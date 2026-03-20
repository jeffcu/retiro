import uvicorn
import sys
import uuid
import asyncio
import shutil
import socket
import threading
import webbrowser
import time
from datetime import datetime, timezone, date
from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Body, Response, Query, Depends, BackgroundTasks, Path
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os
import traceback
from typing import List, Optional, Any, Dict, Union
from pydantic import BaseModel, Field
from decimal import Decimal

from src.importers import csv_importer, holdings_importer
from src.database import initialize_database, save_transactions
from src.data_model import CashflowType, Transaction, FutureIncomeStream, Property
from src import database as db
from src import analysis
from src import forecast
from src import rules_engine
from src.market_data import polling_service, market_scheduler
from src import demo_mode

load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("API is starting up...")
    initialize_database()
    if not os.getenv("MASSIVE_API_KEY") or "YOUR_API_KEY_HERE" in os.getenv("MASSIVE_API_KEY", ""):
        print("WARNING: MASSIVE_API_KEY is not set correctly. Market data features will fail.")
    print("Launching background market data polling scheduler...")
    asyncio.create_task(market_scheduler.background_market_poller())
    yield
    print("API is shutting down...")

app = FastAPI(title="Curie Trust Financial Control Center API", version="1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class RuleCreate(BaseModel):
    category: str
    cashflow_type: str
    tags: Optional[List[str]] = []
    pattern: Optional[str] = None
    case_sensitive: Optional[bool] = False
    account_filter_list: Optional[List[str]] = []
    condition_category: Optional[str] = None
    condition_institution: Optional[str] = None
    condition_cashflow_type: Optional[str] = None
    condition_tags: Optional[str] = None
    priority: Optional[int] = 100
    account_filter_mode: Optional[str] = 'include'

class RuleResponse(RuleCreate):
    rule_id: str

class PurgeRequest(BaseModel):
    target: str

class AccountVisibilitySettings(BaseModel):
    settings: Dict[str, bool]

class TransactionUpdate(BaseModel):
    description: str
    category: Optional[str] = None
    cashflow_type: Optional[str] = None
    tags: List[str] = []

class BulkTagRequest(BaseModel):
    transaction_ids: List[str]
    tags: List[str]

class HoldingUpdate(BaseModel):
    tags: List[str] = []
    asset_type: Optional[str] = None

class AllocationDataItem(BaseModel):
    id: str
    label: str
    value: float
    percentage: float

class AllocationTableItem(BaseModel):
    categoryName: str
    value: int
    percentage: str

class PortfolioAllocationResponse(BaseModel):
    chartData: List[AllocationDataItem]
    tableData: List[AllocationTableItem]

class TaxFactsPayload(BaseModel):
    filing_status: Optional[str] = None
    fed_taxable_income: Optional[float] = None
    fed_total_tax: Optional[float] = None
    state_taxable_income: Optional[float] = None
    state_total_tax: Optional[float] = None

class TaxFactsResponse(TaxFactsPayload):
    tax_year: int

class TaxRateSummary(BaseModel):
    year: int
    federal_rate: str
    state_rate: str
    combined_rate: str
    notes: str

class PortfolioOverallReturnSummary(BaseModel):
    total_market_value: float
    total_cost_basis: float
    total_gain_dollars: float
    total_gain_percent: float
    total_real_estate_equity: float
    total_net_worth: float
    notes: str

class LayeredReturnsMetrics(BaseModel):
    gross_return: float
    total_fees: float
    estimated_taxes: float
    after_tax_return: float

class SankeyNode(BaseModel):
    id: str

class SankeyLink(BaseModel):
    source: str
    target: str
    value: float

class SankeyData(BaseModel):
    nodes: List[SankeyNode]
    links: List[SankeyLink]

class LayeredReturnsResponse(BaseModel):
    metrics: LayeredReturnsMetrics
    sankey_data: SankeyData
    notes: str

class FutureIncomeStreamCreate(BaseModel):
    stream_type: str = Field(..., json_schema_extra={"example": "Pension"})
    description: str = Field(..., json_schema_extra={"example": "Spouse's Pension"})
    start_date: date
    end_date: Optional[date] = None
    amount: float
    frequency: str = Field(..., json_schema_extra={"example": "monthly"})
    annual_increase_rate: float = Field(0.0, ge=0)

class FutureIncomeStreamResponse(FutureIncomeStreamCreate):
    stream_id: str

class PortfolioWaterfallResponse(BaseModel):
    start_of_period_value: Optional[float]
    external_contributions: float
    portfolio_yield: float
    withdrawals_for_spending: float
    fees_and_estimated_taxes: float
    net_cash_flow: float
    market_growth_or_loss: float
    end_of_period_value: Optional[float]
    notes: str

class PortfolioSnapshotCreate(BaseModel):
    snapshot_date: date
    market_value: float

class PortfolioSnapshotResponse(PortfolioSnapshotCreate):
    snapshot_id: str

class PropertyCreate(BaseModel):
    name: str
    purchase_price: float
    mortgage_balance: float
    current_value: float
    appreciation_rate: float
    is_primary: bool
    purchase_year: Optional[int] = None
    sale_year: Optional[int] = None
    annual_maintenance: Optional[float] = 0.0
    fixed_sale_price: Optional[float] = None

class PropertyResponse(PropertyCreate):
    property_id: str
    equity: float

class ForecastConfig(BaseModel):
    birth_year: Optional[int]
    inflation_rate: Optional[float]
    return_rate: Optional[float]
    withdrawal_tax_rate: Optional[float]
    state_tax_rate: Optional[float]
    retirement_age: Optional[int]
    nogo_age: Optional[int]
    base_col_categories: Optional[List[str]]
    base_col_sunset_dates: Optional[Dict[str, Union[float, int, str]]] = None
    phase_multipliers: Optional[Dict[str, Dict[str, Union[float, int, str]]]] 
    residence_sale_enabled: Optional[bool] = False
    residence_sale_year: Optional[int] = None
    residence_lease_enabled: Optional[bool] = False
    residence_lease_year: Optional[int] = None
    residence_lease_monthly_value: Optional[float] = None
    future_properties_enabled: Optional[bool] = True
    base_col_lookback_years: Optional[int] = 1
    withdrawal_strategy: Optional[str] = 'standard'
    tax_filing_status: Optional[str] = 'single'
    roth_conversion_target: Optional[str] = 'none'
    healthcare_amplifier: Optional[float] = 1.5
    worst_case_drop: Optional[float] = 0.02
    best_case_boost: Optional[float] = 0.02
    stress_years: Optional[int] = 10
    daf_transfers: Optional[List[Dict[str, Union[int, float]]]] = None

class DiscretionaryItemCreate(BaseModel):
    item_id: Optional[str] = None
    name: str
    amount: float
    start_year: int
    end_year: Optional[int] = None
    is_recurring: bool = False
    inflation_adjusted: bool = True
    category: Optional[str] = None
    is_enabled: Optional[bool] = True

class AccountMetadataUpdate(BaseModel):
    tax_status: str
    notes: Optional[str] = None

def get_transaction_filters(
    category: Optional[str] = Query(None),
    account_id: Optional[str] = Query(None),
    institution: Optional[str] = Query(None),
    description: Optional[str] = Query(None),
    tags: Optional[str] = Query(None),
    cashflow_type: Optional[str] = Query(None),
    period: Optional[str] = Query(None)
):
    return {k: v for k, v in locals().items() if v is not None}

def get_holding_filters(
    account_id: Optional[str] = Query(None),
    symbol: Optional[str] = Query(None),
    tags: Optional[str] = Query(None),
    asset_type: Optional[str] = Query(None),
    period: Optional[str] = Query(None)
):
    return {k: v for k, v in locals().items() if v is not None}

@app.get("/api")
async def root():
    return {"message": "Curie Trust Financial Control Center API is running."}

@app.post("/api/import/transactions", tags=["Import"])
async def import_transactions_csv(account_id: str = Form(...), file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith('.csv'):
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a CSV.")
    contents = await file.read()
    try:
        transactions, summary = csv_importer.parse_standard_csv(contents, account_id)
        if transactions:
            save_transactions(transactions)
        run_data = {
            "import_run_id": str(uuid.uuid4()),
            "file_name": file.filename,
            "import_type": "transactions",
            "import_timestamp": datetime.now(timezone.utc).isoformat(),
            "record_count": summary.get('record_count'),
            "total_amount": float(summary.get('total_amount', 0.0))
        }
        db.save_import_run(run_data)
        return {"message": f"Successfully imported and saved {len(transactions)} transactions.", "filename": file.filename, "transaction_count": len(transactions)}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to process CSV file: {e}")

@app.post("/api/import/holdings", tags=["Import"])
async def import_holdings_csv(account_id: str = Form(...), file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith('.csv'):
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a CSV.")
    cleaned_account_id = account_id.strip()
    if not cleaned_account_id:
        raise HTTPException(status_code=400, detail="Account ID cannot be empty.")
    contents = await file.read()
    try:
        holdings, summary, skipped, warnings = holdings_importer.parse_holdings_csv(contents, cleaned_account_id)
        deleted, inserted = db.save_holdings_snapshot(holdings, cleaned_account_id)
        run_data = {
            "import_run_id": str(uuid.uuid4()),
            "file_name": file.filename,
            "import_type": "holdings",
            "import_timestamp": datetime.now(timezone.utc).isoformat(),
            "record_count": summary.get('record_count'),
            "total_market_value": float(summary.get('total_market_value', 0.0)),
            "total_cost_basis": float(summary.get('total_cost_basis', 0.0))
        }
        db.save_import_run(run_data)
        return {"message": f"Import complete. Processed {summary.get('record_count', 0)} holdings.", "filename": file.filename, "holdings_count": len(holdings), "deleted_stale_holdings": deleted, "skipped_rows": skipped, "import_warnings": warnings}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to process holdings CSV: {e}")

@app.get("/api/import/runs", tags=["Import"])
async def get_all_import_runs():
    return db.get_all_import_runs()

@app.get("/api/filter-options/income-categories", response_model=List[str], tags=["Filters"])
async def get_income_category_options():
    return db.get_income_categories()

@app.get("/api/filter-options", tags=["Filters"])
async def get_filter_options():
    return db.get_filter_options()

@app.get("/api/accounts", response_model=List[str], tags=["Accounts"])
async def get_all_accounts():
    return db.get_all_account_ids()

@app.get("/api/accounts/visibility", response_model=Dict[str, bool], tags=["Accounts"])
async def get_visibility_settings():
    return db.get_account_visibility()

@app.put("/api/accounts/visibility", status_code=204, tags=["Accounts"])
async def update_visibility_settings(payload: AccountVisibilitySettings):
    db.set_account_visibility(payload.settings)
    return Response(status_code=204)

@app.get("/api/settings/sankey-income-categories", response_model=List[str], tags=["Settings"])
async def get_sankey_income_settings():
    return db.get_setting('sankey_income_categories') or []

@app.put("/api/settings/sankey-income-categories", status_code=204, tags=["Settings"])
async def set_sankey_income_settings(categories: List[str] = Body(...)):
    db.set_setting('sankey_income_categories', categories)
    return Response(status_code=204)

@app.get("/api/accounts/metadata", response_model=Dict[str, Dict[str, Any]], tags=["Accounts"])
async def get_account_metadata():
    return db.get_account_metadata()

@app.put("/api/accounts/{account_id}/metadata", status_code=204, tags=["Accounts"])
async def update_account_metadata(account_id: str, payload: AccountMetadataUpdate):
    db.set_account_metadata(account_id, payload.tax_status, payload.notes)
    return Response(status_code=204)

@app.get("/api/tax-facts/{year}", response_model=TaxFactsResponse, tags=["Tax Data"])
async def get_tax_facts_for_year(year: int = Path(..., ge=2000, le=2100)):
    facts = db.get_tax_facts(year)
    if not facts:
        raise HTTPException(status_code=404, detail=f"Tax facts for year {year} not found.")
    return facts

@app.post("/api/tax-facts/{year}", response_model=TaxFactsResponse, status_code=201, tags=["Tax Data"])
async def create_or_update_tax_facts(payload: TaxFactsPayload, year: int = Path(..., ge=2000, le=2100)):
    try:
        db.save_tax_facts(year, payload.dict())
        facts = db.get_tax_facts(year)
        return facts
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/future-streams", response_model=FutureIncomeStreamResponse, status_code=201, tags=["Forecasting"])
async def create_future_stream(payload: FutureIncomeStreamCreate):
    stream_id = str(uuid.uuid4())
    stream_obj = FutureIncomeStream(
        stream_id=stream_id,
        stream_type=payload.stream_type,
        description=payload.description,
        start_date=payload.start_date,
        end_date=payload.end_date,
        amount=Decimal(str(payload.amount)),
        frequency=payload.frequency,
        annual_increase_rate=Decimal(str(payload.annual_increase_rate))
    )
    try:
        db.create_future_income_stream(stream_obj)
        return FutureIncomeStreamResponse(**stream_obj.__dict__)
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to create income stream: {e}")

@app.get("/api/future-streams", response_model=List[FutureIncomeStreamResponse], tags=["Forecasting"])
async def get_all_future_streams():
    return db.get_all_future_income_streams()

@app.delete("/api/future-streams/{stream_id}", status_code=204, tags=["Forecasting"])
async def delete_future_stream(stream_id: str):
    if not db.delete_future_income_stream(stream_id):
        raise HTTPException(status_code=404, detail="Future income stream not found.")
    return Response(status_code=204)

@app.get("/api/properties", response_model=List[PropertyResponse], tags=["Real Estate"])
async def get_all_properties(mode: str = Query("actuals")):
    properties = db.get_all_properties()
    results = []
    for p in properties:
        p['equity'] = p['current_value'] - p['mortgage_balance']
        results.append(p)
    
    if mode == 'demo':
        return demo_mode.process_for_demo_mode(results)
    return results

@app.post("/api/properties", response_model=PropertyResponse, status_code=201, tags=["Real Estate"])
async def create_property(payload: PropertyCreate):
    existing = db.get_all_properties()
    if len(existing) >= 12:
        raise HTTPException(status_code=400, detail="Maximum property limit reached.")
    
    prop_id = str(uuid.uuid4())
    prop_obj = Property(
        property_id=prop_id,
        name=payload.name,
        purchase_price=Decimal(str(payload.purchase_price)),
        mortgage_balance=Decimal(str(payload.mortgage_balance)),
        current_value=Decimal(str(payload.current_value)),
        appreciation_rate=Decimal(str(payload.appreciation_rate)),
        is_primary=payload.is_primary,
        purchase_year=payload.purchase_year,
        sale_year=payload.sale_year,
        annual_maintenance=Decimal(str(payload.annual_maintenance or 0.0)),
        fixed_sale_price=Decimal(str(payload.fixed_sale_price)) if payload.fixed_sale_price is not None else None
    )
    try:
        db.create_property(prop_obj)
        response_dict = prop_obj.__dict__.copy()
        response_dict['equity'] = float(prop_obj.current_value - prop_obj.mortgage_balance)
        return response_dict
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/properties/{property_id}", status_code=204, tags=["Real Estate"])
async def update_property(property_id: str, payload: PropertyCreate):
    try:
        db.update_property(property_id, payload.dict())
        return Response(status_code=204)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/properties/{property_id}", status_code=204, tags=["Real Estate"])
async def delete_property(property_id: str):
    if not db.delete_property(property_id):
        raise HTTPException(status_code=404, detail="Property not found.")
    return Response(status_code=204)

@app.get("/api/settings/portfolio-inception-date", response_model=Optional[date], tags=["Settings"])
async def get_portfolio_inception_date():
    date_str = db.get_setting('portfolio_inception_date')
    return date.fromisoformat(date_str) if date_str else None

@app.put("/api/settings/portfolio-inception-date", status_code=204, tags=["Settings"])
async def set_portfolio_inception_date(inception_date: date = Body(..., embed=True)):
    db.set_setting('portfolio_inception_date', inception_date.isoformat())
    return Response(status_code=204)

@app.get("/api/portfolio/snapshots", response_model=List[PortfolioSnapshotResponse], tags=["Portfolio Data"])
async def get_all_snapshots():
    return db.get_all_portfolio_snapshots()

@app.post("/api/portfolio/snapshots", response_model=PortfolioSnapshotResponse, status_code=201, tags=["Portfolio Data"])
async def create_snapshot(payload: PortfolioSnapshotCreate):
    try:
        new_snapshot = db.create_portfolio_snapshot(
            snapshot_date=payload.snapshot_date.isoformat(),
            market_value=payload.market_value
        )
        return new_snapshot
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/portfolio/snapshots/{snapshot_id}", status_code=204, tags=["Portfolio Data"])
async def delete_snapshot(snapshot_id: str):
    if not db.delete_portfolio_snapshot(snapshot_id):
        raise HTTPException(status_code=404, detail="Snapshot not found.")
    return Response(status_code=204)

@app.get("/api/forecast/config", tags=["Forecast"])
async def get_forecast_config():
    future_props_setting = db.get_setting('forecast_future_properties_enabled')
    return {
        "birth_year": db.get_setting('forecast_birth_year'),
        "inflation_rate": db.get_setting('forecast_inflation_rate') or 0.03,
        "return_rate": db.get_setting('forecast_return_rate') or 0.05,
        "withdrawal_tax_rate": db.get_setting('forecast_withdrawal_tax_rate') or 0.15,
        "state_tax_rate": db.get_setting('forecast_state_tax_rate') or 0.0,
        "retirement_age": db.get_setting('forecast_retirement_age') or 65,
        "nogo_age": db.get_setting('forecast_nogo_age') or 80,
        "base_col_categories": db.get_setting('forecast_base_col_categories') or [],
        "base_col_sunset_dates": db.get_setting('forecast_base_col_sunset_dates') or {},
        "phase_multipliers": db.get_setting('forecast_phase_multipliers') or {},
        "residence_sale_enabled": db.get_setting('forecast_residence_sale_enabled') or False,
        "residence_sale_year": db.get_setting('forecast_residence_sale_year'),
        "residence_lease_enabled": db.get_setting('forecast_residence_lease_enabled') or False,
        "residence_lease_year": db.get_setting('forecast_residence_lease_year'),
        "residence_lease_monthly_value": db.get_setting('forecast_residence_lease_monthly_value'),
        "future_properties_enabled": bool(future_props_setting) if future_props_setting is not None else True,
        "base_col_lookback_years": db.get_setting('forecast_base_col_lookback_years') or 1,
        "withdrawal_strategy": db.get_setting('forecast_withdrawal_strategy') or 'standard',
        "tax_filing_status": db.get_setting('forecast_tax_filing_status') or 'single',
        "roth_conversion_target": db.get_setting('forecast_roth_conversion_target') or 'none',
        "healthcare_amplifier": db.get_setting('forecast_healthcare_amplifier') or 1.5,
        "worst_case_drop": db.get_setting('forecast_worst_case_drop') or 0.02,
        "best_case_boost": db.get_setting('forecast_best_case_boost') or 0.02,
        "stress_years": db.get_setting('forecast_stress_years') or 10,
        "daf_transfers": db.get_setting('forecast_daf_transfers') or []
    }

@app.put("/api/forecast/config", status_code=204, tags=["Forecast"])
async def update_forecast_config(config: ForecastConfig):
    fields_set = config.__fields_set__
    print(f"DEBUG: Received forecast config update. Fields: {fields_set}")

    if 'birth_year' in fields_set: 
        db.set_setting('forecast_birth_year', config.birth_year)
    if 'inflation_rate' in fields_set: 
        db.set_setting('forecast_inflation_rate', config.inflation_rate)
    if 'return_rate' in fields_set: 
        db.set_setting('forecast_return_rate', config.return_rate)
    if 'withdrawal_tax_rate' in fields_set: 
        db.set_setting('forecast_withdrawal_tax_rate', config.withdrawal_tax_rate)
    if 'state_tax_rate' in fields_set: 
        db.set_setting('forecast_state_tax_rate', config.state_tax_rate)
    if 'retirement_age' in fields_set: 
        db.set_setting('forecast_retirement_age', config.retirement_age)
    if 'nogo_age' in fields_set: 
        db.set_setting('forecast_nogo_age', config.nogo_age)
    if 'base_col_categories' in fields_set: 
        db.set_setting('forecast_base_col_categories', config.base_col_categories)
    if 'base_col_sunset_dates' in fields_set:
        db.set_setting('forecast_base_col_sunset_dates', config.base_col_sunset_dates)
    if 'phase_multipliers' in fields_set: 
        db.set_setting('forecast_phase_multipliers', config.phase_multipliers)
    if 'residence_sale_enabled' in fields_set: 
        db.set_setting('forecast_residence_sale_enabled', config.residence_sale_enabled)
    if 'residence_sale_year' in fields_set: 
        db.set_setting('forecast_residence_sale_year', config.residence_sale_year)
    if 'residence_lease_enabled' in fields_set:
        db.set_setting('forecast_residence_lease_enabled', config.residence_lease_enabled)
    if 'residence_lease_year' in fields_set:
        db.set_setting('forecast_residence_lease_year', config.residence_lease_year)
    if 'residence_lease_monthly_value' in fields_set:
        db.set_setting('forecast_residence_lease_monthly_value', config.residence_lease_monthly_value)
    if 'future_properties_enabled' in fields_set:
        db.set_setting('forecast_future_properties_enabled', config.future_properties_enabled)
    if 'base_col_lookback_years' in fields_set: 
        db.set_setting('forecast_base_col_lookback_years', config.base_col_lookback_years)
    if 'withdrawal_strategy' in fields_set:
        db.set_setting('forecast_withdrawal_strategy', config.withdrawal_strategy)
    if 'tax_filing_status' in fields_set:
        db.set_setting('forecast_tax_filing_status', config.tax_filing_status)
    if 'roth_conversion_target' in fields_set:
        db.set_setting('forecast_roth_conversion_target', config.roth_conversion_target)
    if 'healthcare_amplifier' in fields_set:
        db.set_setting('forecast_healthcare_amplifier', config.healthcare_amplifier)
    if 'worst_case_drop' in fields_set:
        db.set_setting('forecast_worst_case_drop', config.worst_case_drop)
    if 'best_case_boost' in fields_set:
        db.set_setting('forecast_best_case_boost', config.best_case_boost)
    if 'stress_years' in fields_set:
        db.set_setting('forecast_stress_years', config.stress_years)
    if 'daf_transfers' in fields_set:
        db.set_setting('forecast_daf_transfers', config.daf_transfers)

    return Response(status_code=204)

@app.get("/api/forecast/base-col", tags=["Forecast"])
async def get_calculated_base_col(categories: Optional[List[str]] = Query(None), lookback_years: int = Query(1)):
    cats_to_check = categories or db.get_setting('forecast_base_col_categories') or []
    total = db.get_base_col_from_actuals(cats_to_check, lookback_years)
    return {"base_col": total}

@app.get("/api/forecast/simulation", tags=["Forecast"])
async def run_forecast_simulation(mode: str = Query("actuals")):
    result = forecast.calculate_forecast()
    if mode == 'demo':
        return demo_mode.process_for_demo_mode(result)
    return result

@app.get("/api/forecast/discretionary", tags=["Forecast"])
async def get_discretionary_items():
    return db.get_discretionary_budget_items()

@app.post("/api/forecast/discretionary", status_code=201, tags=["Forecast"])
async def create_discretionary_item(item: DiscretionaryItemCreate):
    db.save_discretionary_budget_item(item.dict())
    return {"message": "Item saved"}

@app.delete("/api/forecast/discretionary/{item_id}", status_code=204, tags=["Forecast"])
async def delete_discretionary_item(item_id: str):
    db.delete_discretionary_budget_item(item_id)
    return Response(status_code=204)

@app.get("/api/tags/summary", tags=["Tags"])
async def get_all_tags_summary():
    return db.get_tag_summary()

@app.get("/api/tags/{tag_name}/records", tags=["Tags"])
async def get_tag_records(tag_name: str):
    return db.get_records_by_tag(tag_name)

@app.post("/api/rules", response_model=RuleResponse, status_code=201, tags=["Rules"])
async def create_new_rule(rule: RuleCreate):
    try:
        new_rule = db.create_rule(rule.dict())
        return new_rule
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/rules", response_model=List[RuleResponse], tags=["Rules"])
async def get_all_rules():
    return db.get_all_rules()

@app.delete("/api/rules/{rule_id}", status_code=204, tags=["Rules"])
async def delete_rule_by_id(rule_id: str):
    if not db.delete_rule(rule_id):
        raise HTTPException(status_code=404, detail="Rule not found.")
    return Response(status_code=204)

@app.post("/api/transactions/recategorize", tags=["Processing"])
async def trigger_recategorization():
    re_categorized_count = rules_engine.recategorize_all_transactions()
    return {"message": f"Successfully re-categorized {re_categorized_count} transactions."}

@app.get("/api/sankey/home", tags=["Analysis"])
async def get_home_sankey_data(period: str = "all"):
    return analysis.generate_capital_flow_sankey(period, exclude_invisible=True)

@app.get("/api/analysis/capital-flow-table", tags=["Analysis"])
async def get_home_capital_flow_table(period: str = "all"):
    return analysis.generate_capital_flow_table_data(period, exclude_invisible=True)

@app.get("/api/analysis/investment-cashflow-summary", tags=["Analysis"])
async def get_investment_cashflow_summary(period: str = "all"):
    return analysis.calculate_investment_cashflow_summary(period)

@app.get("/api/portfolio/summary", tags=["Analysis"])
async def get_portfolio_summary(mode: str = Query("actuals")):
    holdings = db.get_holdings()
    total_market_value = sum(h.get('market_value', 0) for h in holdings if h.get('market_value') is not None)
    total_re_equity = db.get_total_real_estate_equity()
    result = {
        "total_market_value": total_market_value,
        "total_real_estate_equity": total_re_equity,
        "total_net_worth": total_market_value + total_re_equity
    }
    if mode == 'demo':
        return demo_mode.process_for_demo_mode(result)
    return result

@app.get("/api/analysis/cashflow-chart", tags=["Analysis"])
async def get_cashflow_chart(filters: Dict[str, Any] = Depends(get_transaction_filters)):
    return analysis.prepare_cashflow_chart_data(filters)

@app.get("/api/analysis/portfolio-allocation", tags=["Analysis"], response_model=PortfolioAllocationResponse)
async def get_portfolio_allocation_data(mode: str = Query("actuals")):
    result = analysis.prepare_portfolio_allocation_chart_data()
    if mode == 'demo':
        return demo_mode.process_for_demo_mode(result)
    return result

@app.get("/api/analysis/portfolio-chart", tags=["Analysis"])
async def get_portfolio_chart(filters: Dict[str, Any] = Depends(get_holding_filters), mode: str = Query("actuals")):
    result = analysis.prepare_portfolio_chart_data(filters)
    if mode == 'demo':
        return demo_mode.process_for_demo_mode(result)
    return result

@app.get("/api/analysis/effective-tax-rates", response_model=List[TaxRateSummary], tags=["Analysis"])
async def get_effective_tax_rates():
    target_years = [2023, 2024]
    return analysis.calculate_effective_tax_rates_for_years(target_years)

@app.get("/api/portfolio/overall-return", response_model=PortfolioOverallReturnSummary, tags=["Analysis"])
async def get_portfolio_overall_return(mode: str = Query("actuals")):
    result = analysis.calculate_portfolio_summary_metrics()
    if mode == 'demo':
        return demo_mode.process_for_demo_mode(result)
    return result

@app.get("/api/portfolio/layered-returns-summary", response_model=LayeredReturnsResponse, tags=["Analysis"])
async def get_layered_returns_summary(mode: str = Query("actuals")):
    result = analysis.calculate_layered_returns_summary()
    return result

@app.get("/api/analysis/portfolio-waterfall", response_model=PortfolioWaterfallResponse, tags=["Analysis"])
async def get_portfolio_waterfall(period: str = Query("all", description="Time period, e.g., '2023', '6m', 'all'")):
    return analysis.calculate_portfolio_waterfall(period)

@app.get("/api/accounts/performance", tags=["Analysis"])
async def get_account_performance(mode: str = Query("actuals")):
    data = analysis.get_account_performance_summary()
    if mode == 'demo':
        return demo_mode.process_for_demo_mode(data)
    return data

@app.get("/api/transactions", tags=["Data"])
async def get_filtered_transactions(filters: Dict[str, Any] = Depends(get_transaction_filters)):
    return db.get_transactions(filters)

@app.post("/api/transactions/bulk-tag", tags=["Data"])
async def bulk_tag_transactions(payload: BulkTagRequest):
    updated = []
    for tx_id in payload.transaction_ids:
        tx_dict = db.get_transaction(tx_id)
        if tx_dict:
            existing_tags = [t.strip() for t in (tx_dict.get('tags') or '').split(',') if t.strip()]
            new_tags = list(set(existing_tags + payload.tags))
            
            tx_date = datetime.strptime(tx_dict['transaction_date'].split(' ')[0], '%Y-%m-%d').date()
            tx_obj = Transaction(
                transaction_id=tx_dict['transaction_id'],
                account_id=tx_dict['account_id'],
                transaction_date=tx_date,
                amount=Decimal(str(tx_dict['amount'])),
                description=tx_dict['description'],
                category=tx_dict.get('category'),
                cashflow_type=CashflowType.from_string(tx_dict.get('cashflow_type')),
                tags=new_tags,
                merchant=tx_dict.get('merchant'),
                asset_id=tx_dict.get('asset_id'),
                import_run_id=tx_dict.get('import_run_id'),
                raw_data_hash=tx_dict.get('raw_data_hash'),
                institution=tx_dict.get('institution'),
                original_category=tx_dict.get('original_category')
            )
            tx_obj.is_transfer = tx_obj.cashflow_type == CashflowType.TRANSFER
            updated.append(tx_obj)
    
    if updated:
        db.save_transactions(updated)
    return {"message": f"Successfully tagged {len(updated)} transactions."}

@app.put("/api/transactions/{transaction_id}", tags=["Data"])
async def update_transaction(transaction_id: str, payload: TransactionUpdate):
    tx_dict = db.get_transaction(transaction_id)
    if not tx_dict:
        raise HTTPException(status_code=404, detail="Transaction not found.")
    
    tx_date = datetime.strptime(tx_dict['transaction_date'].split(' ')[0], '%Y-%m-%d').date()
    amount = Decimal(str(tx_dict['amount']))
    cashflow_type = CashflowType.from_string(payload.cashflow_type)

    tx_obj = Transaction(
        transaction_id=tx_dict['transaction_id'],
        account_id=tx_dict['account_id'],
        transaction_date=tx_date,
        amount=amount,
        description=payload.description,
        category=payload.category,
        cashflow_type=cashflow_type,
        tags=payload.tags,
        merchant=tx_dict.get('merchant'),
        asset_id=tx_dict.get('asset_id'),
        import_run_id=tx_dict.get('import_run_id'),
        raw_data_hash=tx_dict.get('raw_data_hash'),
        institution=tx_dict.get('institution'),
        original_category=tx_dict.get('original_category')
    )
    tx_obj.is_transfer = tx_obj.cashflow_type == CashflowType.TRANSFER
    db.save_transactions([tx_obj])
    return {"message": "Transaction updated successfully", "transaction": tx_obj}

@app.get("/api/holdings", tags=["Data"])
async def get_filtered_holdings(filters: Dict[str, Any] = Depends(get_holding_filters), mode: str = Query("actuals")):
    result = db.get_holdings(filters)
    if mode == 'demo':
        return demo_mode.process_for_demo_mode(result)
    return result

@app.put("/api/holdings/{holding_id}", tags=["Data"])
async def update_holding(holding_id: str, payload: HoldingUpdate):
    db.update_holding(holding_id, payload.dict())
    updated_holding = db.get_holding(holding_id)
    if not updated_holding:
        raise HTTPException(status_code=404, detail="Holding not found after update.")
    return updated_holding

@app.post("/api/data/purge", tags=["Admin"])
async def purge_data(request: PurgeRequest):
    try:
        purge_details = db.purge_table_data(request.target)
        return {"message": f"Successfully purged table: {request.target}", "details": purge_details}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/admin/factory-reset", tags=["Admin"])
async def factory_reset_db():
    try:
        db.factory_reset()
        return {"message": "System purged. Factory reset complete."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/market-data/refresh", tags=["Market Data"])
async def trigger_market_data_refresh(background_tasks: BackgroundTasks, limit: int = Query(25, description="Number of top holdings to refresh. Use 0 for all.")):
    limit = limit if limit > 0 else 1000
    background_tasks.add_task(polling_service.refresh_market_data, top_n=limit)
    return {"message": f"Live market data refresh initiated in the background for top {limit} holdings."}

@app.post("/api/market-data/refresh-eod", tags=["Market Data"])
async def trigger_eod_market_data_refresh(background_tasks: BackgroundTasks):
    background_tasks.add_task(polling_service.refresh_eod_data)
    return {"message": "Bulk EOD data refresh initiated in the background for ALL holdings."}

@app.get("/api/admin/backup", tags=["Admin"])
async def download_backup():
    db_path = db.DB_FILE
    filename = f"trust_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    return FileResponse(path=db_path, filename=filename, media_type='application/octet-stream')

@app.post("/api/admin/restore", tags=["Admin"])
async def restore_backup(file: UploadFile = File(...)):
    try:
        if not file.filename.endswith('.db') and not file.filename.endswith('.sqlite'):
            raise HTTPException(status_code=400, detail="Invalid file type. Please upload a .db file.")
        
        # Read completely into memory first to avoid blocking the event loop with I/O
        content = await file.read()
        
        # Write the file down to disk
        with open(db.DB_FILE, "wb") as f:
            f.write(content)
            
        # Critical: Purge lingering SQLite WAL and SHM files to prevent disk image malformation
        wal_path = str(db.DB_FILE) + "-wal"
        shm_path = str(db.DB_FILE) + "-shm"
        if os.path.exists(wal_path):
            os.remove(wal_path)
        if os.path.exists(shm_path):
            os.remove(shm_path)
            
        # Tell the database module to re-run schema validation on the next query
        db._schema_ensured = False

        return {"message": "Database restored successfully. Please refresh the application."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to restore backup: {e}")

# --- SPA / STATIC FILE MOUNTING FOR STANDALONE APP ---
def get_base_path():
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

base_path = get_base_path()
dist_dir = os.path.join(base_path, "dist")

if os.path.exists(dist_dir):
    assets_dir = os.path.join(dist_dir, "assets")
    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")
    
    @app.get("/{full_path:path}")
    async def catch_all(full_path: str):
        if full_path.startswith("api/"):
            return {"error": "API route not found"}
            
        index_path = os.path.join(dist_dir, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
        return {"error": "Frontend build index.html not found."}

def get_free_port(start_port=8000, max_port=8100):
    for port in range(start_port, max_port):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(('127.0.0.1', port)) != 0:
                return port
    return 8000

def open_browser_when_ready(port):
    url = f"http://127.0.0.1:{port}"
    print(f"--- Engaging active port sensors for {url} ---")
    
    # Actively poll the port instead of a blind timeout
    for _ in range(40):  # Maximum 20 seconds wait
        try:
            with socket.create_connection(('127.0.0.1', port), timeout=0.5):
                print(f"\n🚀 Warp core stable! Opening browser at {url}\n")
                webbrowser.open(url)
                return
        except OSError:
            time.sleep(0.5)
            
    print(f"⚠️ Warning: Main screen offline. Please manually navigate to {url}")

if __name__ == "__main__":
    port = get_free_port()
    # Spawn a background thread that actively waits for the server to bind
    threading.Thread(target=open_browser_when_ready, args=(port,), daemon=True).start()
    uvicorn.run(app, host="0.0.0.0", port=port)
