import uvicorn
import uuid
import asyncio
import shutil
from datetime import datetime, timezone, date
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Body, Response, Query, Depends, BackgroundTasks, Path
from fastapi.responses import FileResponse
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
from src import forecast # NEW
from src import rules_engine
from src.market_data import polling_service, market_scheduler
from src import demo_mode

load_dotenv()

app = FastAPI(title="Curie Trust Financial Control Center API", version="1.0")

# Scotty: Opening the hailing frequencies to all ships in the sector (Local Network Access)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allow all origins for local dev convenience
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Pydantic Models ---
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

# --- NEW: Pydantic model for Tax Facts ---
class TaxFactsPayload(BaseModel):
    filing_status: Optional[str] = None
    fed_taxable_income: Optional[float] = None
    fed_total_tax: Optional[float] = None
    state_taxable_income: Optional[float] = None
    state_total_tax: Optional[float] = None

class TaxFactsResponse(TaxFactsPayload):
    tax_year: int

# --- NEW: Pydantic model for Tax Rate Summary ---
class TaxRateSummary(BaseModel):
    year: int
    federal_rate: str
    state_rate: str
    combined_rate: str
    notes: str

# --- REVISED: Pydantic model for Portfolio Overall Return ---
class PortfolioOverallReturnSummary(BaseModel):
    total_market_value: float
    total_cost_basis: float
    total_gain_dollars: float
    total_gain_percent: float
    total_real_estate_equity: float # NEW
    total_net_worth: float # NEW
    notes: str

# --- NEW: Pydantic models for Layered Returns --- 
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


# --- NEW: Pydantic models for Future Income Streams ---
class FutureIncomeStreamCreate(BaseModel):
    stream_type: str = Field(..., example="Pension")
    description: str = Field(..., example="Spouse's Pension")
    start_date: date
    end_date: Optional[date] = None
    amount: float
    frequency: str = Field(..., example="monthly") # 'monthly' or 'annually'
    annual_increase_rate: float = Field(0.0, ge=0)

class FutureIncomeStreamResponse(FutureIncomeStreamCreate):
    stream_id: str

# --- REVISED: Pydantic model for Portfolio Waterfall ---
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

# --- NEW: Pydantic models for Snapshots ---
class PortfolioSnapshotCreate(BaseModel):
    snapshot_date: date
    market_value: float

class PortfolioSnapshotResponse(PortfolioSnapshotCreate):
    snapshot_id: str

# --- NEW: Pydantic models for Properties ---
class PropertyCreate(BaseModel):
    name: str
    purchase_price: float
    mortgage_balance: float
    current_value: float
    appreciation_rate: float
    is_primary: bool

class PropertyResponse(PropertyCreate):
    property_id: str
    equity: float

# --- NEW: Pydantic models for Forecast Config (Phase 9) ---
class ForecastConfig(BaseModel):
    birth_year: Optional[int]
    inflation_rate: Optional[float]
    return_rate: Optional[float]
    withdrawal_tax_rate: Optional[float]
    retirement_age: Optional[int]
    nogo_age: Optional[int]
    base_col_categories: Optional[List[str]]
    # Phase Multipliers can be strings from UI (e.g. empty string to clear), so we allow Any/Union
    phase_multipliers: Optional[Dict[str, Dict[str, Union[float, int, str]]]] 
    # --- NEW: Residence Sale Strategy ---
    residence_sale_enabled: Optional[bool] = False
    residence_sale_year: Optional[int] = None
    # --- NEW: CoL Lookback ---
    base_col_lookback_years: Optional[int] = 1

class DiscretionaryItemCreate(BaseModel):
    name: str
    amount: float
    start_year: int
    end_year: Optional[int] = None
    is_recurring: bool = False
    inflation_adjusted: bool = True
    category: Optional[str] = None

# --- NEW: Account Metadata Pydantic ---
class AccountMetadataUpdate(BaseModel):
    tax_status: str
    notes: Optional[str] = None


# --- App Events ---
@app.on_event("startup")
async def startup_event():
    print("API is starting up...")
    initialize_database()
    if not os.getenv("MASSIVE_API_KEY") or "YOUR_API_KEY_HERE" in os.getenv("MASSIVE_API_KEY", ""):
        print("WARNING: MASSIVE_API_KEY is not set correctly. Market data features will fail.")
    print("Launching background market data polling scheduler...")
    asyncio.create_task(market_scheduler.background_market_poller())

# --- Dependency Functions for Filters ---
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

# --- API Endpoints ---

@app.get("/")
async def root():
    return {"message": "Curie Trust Financial Control Center API is running."}

# --- Import Endpoints ---
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

# --- Rules Endpoints ---
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

# --- Analysis Endpoints ---
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
    
    # Calculate Real Estate Equity
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

# --- NEW: Effective Tax Rate Endpoint ---
@app.get("/api/analysis/effective-tax-rates", response_model=List[TaxRateSummary], tags=["Analysis"])
async def get_effective_tax_rates():
    """Calculates and returns the effective tax rates for key years."""
    target_years = [2023, 2024]
    return analysis.calculate_effective_tax_rates_for_years(target_years)

# --- REVISED: Portfolio Overall Return Endpoint ---
@app.get("/api/portfolio/overall-return", response_model=PortfolioOverallReturnSummary, tags=["Analysis"])
async def get_portfolio_overall_return(mode: str = Query("actuals")):
    """
    Calculates key portfolio summary metrics based on "since inception" data.
    """
    result = analysis.calculate_portfolio_summary_metrics()
    if mode == 'demo':
        return demo_mode.process_for_demo_mode(result)
    return result

# --- NEW: Layered Returns Endpoint --- 
@app.get("/api/portfolio/layered-returns-summary", response_model=LayeredReturnsResponse, tags=["Analysis"])
async def get_layered_returns_summary(mode: str = Query("actuals")):
    """ 
    Calculates the full Gross -> Fees -> Taxes -> After-Tax return waterfall.
    """
    result = analysis.calculate_layered_returns_summary()
    # Note: Demo mode is not applied here as the values are relative and less sensitive.
    return result

# --- REVISED: Portfolio Waterfall Endpoint ---
@app.get("/api/analysis/portfolio-waterfall", response_model=PortfolioWaterfallResponse, tags=["Analysis"])
async def get_portfolio_waterfall(period: str = Query("all", description="Time period, e.g., '2023', '6m', 'all'")):
    """
    Provides a full performance attribution waterfall analysis of portfolio value changes.
    Requires historical value snapshots to be entered.
    """
    return analysis.calculate_portfolio_waterfall(period)


# --- Data & Filter Endpoints ---
@app.get("/api/transactions", tags=["Data"])
async def get_filtered_transactions(filters: Dict[str, Any] = Depends(get_transaction_filters)):
    return db.get_transactions(filters)

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

@app.get("/api/filter-options", tags=["Filters"])
async def get_filter_options():
    return db.get_filter_options()

@app.get("/api/filter-options/income-categories", response_model=List[str], tags=["Filters"])
async def get_income_category_options():
    return db.get_income_categories()

# --- Account & Settings Endpoints ---
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

# --- NEW: Account Metadata Endpoints ---
@app.get("/api/accounts/metadata", response_model=Dict[str, Dict[str, Any]], tags=["Accounts"])
async def get_account_metadata():
    return db.get_account_metadata()

@app.put("/api/accounts/{account_id}/metadata", status_code=204, tags=["Accounts"])
async def update_account_metadata(account_id: str, payload: AccountMetadataUpdate):
    db.set_account_metadata(account_id, payload.tax_status, payload.notes)
    return Response(status_code=204)

# --- NEW: Tax Facts Endpoints --- 
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

# --- NEW: Future Income Stream Endpoints ---
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

# --- NEW: Properties (Real Estate) Endpoints ---
@app.get("/api/properties", response_model=List[PropertyResponse], tags=["Real Estate"])
async def get_all_properties(mode: str = Query("actuals")):
    properties = db.get_all_properties()
    # Calculate equity on the fly for display
    results = []
    for p in properties:
        p['equity'] = p['current_value'] - p['mortgage_balance']
        results.append(p)
    
    if mode == 'demo':
        return demo_mode.process_for_demo_mode(results)
    return results

@app.post("/api/properties", response_model=PropertyResponse, status_code=201, tags=["Real Estate"])
async def create_property(payload: PropertyCreate):
    # Check limit: "Principal Residence first, with up to five additional properties"
    existing = db.get_all_properties()
    if len(existing) >= 6:
        raise HTTPException(status_code=400, detail="Maximum property limit (6) reached.")
    
    # Enforce Principal Residence logic? Or just allow user to manage via flags.
    # Requirement says "Principal Residence should be first". We'll rely on frontend/sorting.
    
    prop_id = str(uuid.uuid4())
    prop_obj = Property(
        property_id=prop_id,
        name=payload.name,
        purchase_price=Decimal(str(payload.purchase_price)),
        mortgage_balance=Decimal(str(payload.mortgage_balance)),
        current_value=Decimal(str(payload.current_value)),
        appreciation_rate=Decimal(str(payload.appreciation_rate)),
        is_primary=payload.is_primary
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


# --- NEW: Portfolio Settings & Snapshots Endpoints ---
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

# --- NEW: Phase 9 Forecast Endpoints ---
@app.get("/api/forecast/config", tags=["Forecast"])
async def get_forecast_config():
    return {
        "birth_year": db.get_setting('forecast_birth_year'),
        "inflation_rate": db.get_setting('forecast_inflation_rate') or 0.03,
        "return_rate": db.get_setting('forecast_return_rate') or 0.05,
        "withdrawal_tax_rate": db.get_setting('forecast_withdrawal_tax_rate') or 0.15,
        "retirement_age": db.get_setting('forecast_retirement_age') or 65,
        "nogo_age": db.get_setting('forecast_nogo_age') or 80,
        "base_col_categories": db.get_setting('forecast_base_col_categories') or [],
        "phase_multipliers": db.get_setting('forecast_phase_multipliers') or {},
        "residence_sale_enabled": db.get_setting('forecast_residence_sale_enabled') or False,
        "residence_sale_year": db.get_setting('forecast_residence_sale_year'),
        "base_col_lookback_years": db.get_setting('forecast_base_col_lookback_years') or 1
    }

@app.put("/api/forecast/config", status_code=204, tags=["Forecast"])
async def update_forecast_config(config: ForecastConfig):
    # We use __fields_set__ to know which fields were actually sent in the request.
    # This allows us to handle explicit nulls (clearing a value) vs missing fields (no update).
    
    fields_set = config.__fields_set__

    if 'birth_year' in fields_set: 
        db.set_setting('forecast_birth_year', config.birth_year)
    
    if 'inflation_rate' in fields_set: 
        db.set_setting('forecast_inflation_rate', config.inflation_rate)
    
    if 'return_rate' in fields_set: 
        db.set_setting('forecast_return_rate', config.return_rate)
    
    if 'withdrawal_tax_rate' in fields_set: 
        db.set_setting('forecast_withdrawal_tax_rate', config.withdrawal_tax_rate)
    
    if 'retirement_age' in fields_set: 
        db.set_setting('forecast_retirement_age', config.retirement_age)
    
    if 'nogo_age' in fields_set: 
        db.set_setting('forecast_nogo_age', config.nogo_age)
    
    if 'base_col_categories' in fields_set: 
        db.set_setting('forecast_base_col_categories', config.base_col_categories)
    
    if 'phase_multipliers' in fields_set: 
        db.set_setting('forecast_phase_multipliers', config.phase_multipliers)
    
    # --- NEW: Residence Sale Settings ---
    if 'residence_sale_enabled' in fields_set: 
        db.set_setting('forecast_residence_sale_enabled', config.residence_sale_enabled)
    
    if 'residence_sale_year' in fields_set: 
        db.set_setting('forecast_residence_sale_year', config.residence_sale_year)
    
    if 'base_col_lookback_years' in fields_set:
        db.set_setting('forecast_base_col_lookback_years', config.base_col_lookback_years)

    return Response(status_code=204)

@app.get("/api/forecast/base-col", tags=["Forecast"])
async def get_calculated_base_col(categories: Optional[List[str]] = Query(None), lookback_years: int = Query(1)):
    cats_to_check = categories or db.get_setting('forecast_base_col_categories') or []
    total = db.get_base_col_from_actuals(cats_to_check, lookback_years)
    return {"base_col": total}

@app.get("/api/forecast/simulation", tags=["Forecast"])
async def run_forecast_simulation():
    return forecast.calculate_forecast()

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


# --- Admin & Market Data Endpoints ---
@app.post("/api/data/purge", tags=["Admin"])
async def purge_data(request: PurgeRequest):
    try:
        purge_details = db.purge_table_data(request.target)
        return {"message": f"Successfully purged table: {request.target}", "details": purge_details}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/market-data/refresh", tags=["Market Data"])
async def trigger_market_data_refresh(background_tasks: BackgroundTasks, limit: int = Query(25, description="Number of top holdings to refresh. Use 0 for all.")):
    limit = limit if limit > 0 else 1000
    background_tasks.add_task(polling_service.refresh_market_data, top_n=limit)
    return {"message": f"Live market data refresh initiated in the background for top {limit} holdings."}

@app.post("/api/market-data/refresh-eod", tags=["Market Data"])
async def trigger_eod_market_data_refresh(background_tasks: BackgroundTasks):
    background_tasks.add_task(polling_service.refresh_eod_data)
    return {"message": "Bulk EOD data refresh initiated in the background for ALL holdings."}

# --- NEW: Backup & Restore Endpoints ---
@app.get("/api/admin/backup", tags=["Admin"])
async def download_backup():
    """Downloads the current SQLite database file."""
    db_path = db.DB_FILE
    filename = f"trust_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    return FileResponse(path=db_path, filename=filename, media_type='application/octet-stream')

@app.post("/api/admin/restore", tags=["Admin"])
async def restore_backup(file: UploadFile = File(...)):
    """Overwrites the current database with the uploaded file."""
    try:
        # Verify file extension (simple check)
        if not file.filename.endswith('.db') and not file.filename.endswith('.sqlite'):
            raise HTTPException(status_code=400, detail="Invalid file type. Please upload a .db file.")
        
        # Overwrite the database file
        with open(db.DB_FILE, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        return {"message": "Database restored successfully. Please refresh the application."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to restore backup: {e}")

if __name__ == "__main__":
    # Scotty: Binding to 0.0.0.0 is crucial for the iPad (remote access) to work!
    uvicorn.run(app, host="0.0.0.0", port=8000)
