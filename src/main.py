import uvicorn
import uuid
import asyncio
from datetime import datetime, timezone, date
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Body, Response, Query, Depends, BackgroundTasks, Path
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os
import traceback
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field
from decimal import Decimal

from src.importers import csv_importer, holdings_importer
from src.database import initialize_database, save_transactions
from src.data_model import CashflowType, Transaction, FutureIncomeStream
from src import database as db
from src import analysis
from src import rules_engine
from src.market_data import polling_service, market_scheduler
from src import demo_mode

load_dotenv()

app = FastAPI(title="Curie Trust Financial Control Center API", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
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
    result = {"total_market_value": total_market_value}
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

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
