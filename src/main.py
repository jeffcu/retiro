import uvicorn
import uuid
from datetime import datetime, timezone
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Body, Response, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os
import traceback
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field
from decimal import Decimal

from src.importers import csv_importer, holdings_importer
from src.database import initialize_database, save_transactions
from src.data_model import CashflowType
from src import database as db
from src import analysis
from src import rules_engine

load_dotenv()

app = FastAPI(
    title="Curie Trust Financial Control Center API",
    version="1.0",
)

origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class RuleCreate(BaseModel):
    # Action fields
    category: str
    cashflow_type: str # From frontend, will be string value of CashflowType enum
    tags: Optional[List[str]] = []
    
    # Condition fields
    pattern: Optional[str] = None # from description filter
    case_sensitive: Optional[bool] = False
    account_filter_list: Optional[List[str]] = []
    condition_category: Optional[str] = None
    condition_institution: Optional[str] = None
    condition_cashflow_type: Optional[str] = None
    condition_tags: Optional[str] = None

    # Meta
    priority: Optional[int] = 100
    account_filter_mode: Optional[str] = 'include'

class RuleResponse(RuleCreate):
    rule_id: str

class PurgeRequest(BaseModel):
    target: str = Field(..., description="The database table to purge, e.g., 'transactions' or 'holdings'.")

class AccountVisibilitySettings(BaseModel):
    settings: Dict[str, bool]


@app.on_event("startup")
async def startup_event():
    print("API is starting up...")
    initialize_database()
    
    api_key = os.getenv("ALPHA_VANTAGE_API_KEY")
    if not api_key or api_key == "YOUR_API_KEY_HERE":
        print("WARNING: ALPHA_VANTAGE_API_KEY is not set. Market data features will fail.")

@app.get("/")
async def root():
    return {"message": "Curie Trust Financial Control Center API is running."}

@app.post("/api/import/transactions", tags=["Import"])
async def import_transactions_csv(account_id: str = Form(...), file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith('.csv'):
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a CSV.")

    contents = await file.read()
    try:
        # The account_id from the form is now a fallback if not provided in the CSV
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
        
        print(f"Successfully processed {len(transactions)} transactions.")
        return {
            "message": f"Successfully imported and saved {len(transactions)} transactions.",
            "filename": file.filename,
            "transaction_count": len(transactions)
        }
    except Exception as e:
        print(f"ERROR processing file {file.filename}: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to process CSV file: {e}")

@app.post("/api/import/holdings", tags=["Import"])
async def import_holdings_csv(account_id: str = Form(...), file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith('.csv'):
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a CSV.")
    
    # CORRECTED: Sanitize the account_id at the API boundary to remove whitespace.
    cleaned_account_id = account_id.strip()
    if not cleaned_account_id:
        raise HTTPException(status_code=400, detail="Account ID cannot be empty or just whitespace.")

    contents = await file.read()
    try:
        # Pass the cleaned_account_id to the parser so Holding objects are created cleanly.
        holdings, summary, skipped, warnings = holdings_importer.parse_holdings_csv(contents, cleaned_account_id)
        
        # Pass the cleaned_account_id to the database function for the DELETE operation.
        deleted, inserted = db.save_holdings_snapshot(holdings, cleaned_account_id)
        print(f"Holdings snapshot saved for account '{cleaned_account_id}': {deleted} deleted, {inserted} inserted.")

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

        return {
            "message": f"Import complete. Processed {summary.get('record_count', 0)} holdings.",
            "filename": file.filename,
            "holdings_count": len(holdings),
            "deleted_stale_holdings": deleted,
            "skipped_rows": skipped,
            "import_warnings": warnings
        }
    except Exception as e:
        print(f"ERROR processing holdings file {file.filename}: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to process holdings CSV file: {e}")

@app.get("/api/import/runs", tags=["Import"])
async def get_all_import_runs():
    try:
        return db.get_all_import_runs()
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Failed to retrieve import runs.")

@app.post("/api/rules", response_model=RuleResponse, status_code=201, tags=["Rules"])
async def create_new_rule(rule: RuleCreate):
    try:
        rule_dict = rule.dict()
        created_rule = db.create_rule(rule_dict)
        return created_rule
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=500, 
            detail=f"An internal error occurred while creating the rule: {str(e)}"
        )

@app.get("/api/rules", response_model=List[RuleResponse], tags=["Rules"])
async def get_all_rules():
    rules = db.get_all_rules()
    return rules

@app.delete("/api/rules/{rule_id}", status_code=204, tags=["Rules"])
async def delete_rule_by_id(rule_id: str):
    success = db.delete_rule(rule_id)
    if not success:
        raise HTTPException(status_code=404, detail="Rule not found.")
    return Response(status_code=204) # Return empty response for success

@app.get("/api/sankey/income", tags=["Analysis"])
async def get_income_sankey_data(period: str = "all") -> Dict[str, List[Dict[str, Any]]]:
    try:
        # This now implicitly uses the visibility settings stored in the DB
        data = analysis.generate_income_sankey(period, exclude_invisible=True)
        return data
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"An internal error occurred in the analysis engine: {e}")

# --- Filter Dependencies --- #
# These functions gather filter parameters from the query string

def get_transaction_filters(
    category: Optional[str] = Query(None),
    account_id: Optional[str] = Query(None),
    institution: Optional[str] = Query(None),
    description: Optional[str] = Query(None),
    tags: Optional[str] = Query(None),
    cashflow_type: Optional[str] = Query(None),
) -> Dict[str, Any]:
    filters = {
        "category": category,
        "account_id": account_id,
        "institution": institution,
        "description": description,
        "tags": tags,
        "cashflow_type": cashflow_type,
    }
    return {k: v for k, v in filters.items() if v is not None}

def get_holding_filters(
    account_id: Optional[str] = Query(None),
    symbol: Optional[str] = Query(None),
) -> Dict[str, Any]:
    filters = {
        "account_id": account_id,
        "symbol": symbol
    }
    return {k: v for k, v in filters.items() if v is not None}

@app.get("/api/transactions", tags=["Data"])
async def get_filtered_transactions(filters: Dict[str, Any] = Depends(get_transaction_filters)):
    try:
        return db.get_transactions(filters)
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"An internal error occurred while fetching transactions: {e}")

@app.get("/api/holdings", tags=["Data"])
async def get_filtered_holdings(filters: Dict[str, Any] = Depends(get_holding_filters)):
    try:
        return db.get_holdings(filters)
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Failed to retrieve holdings.")


@app.post("/api/transactions/recategorize", tags=["Processing"])
async def trigger_recategorization():
    try:
        count = rules_engine.recategorize_all_transactions()
        return {"message": f"Successfully re-categorized {count} transactions."}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"An internal error occurred during re-categorization: {e}")

@app.get("/api/portfolio/summary", tags=["Analysis"])
async def get_portfolio_summary():
    """Calculates the total market value of all holdings."""
    try:
        holdings = db.get_holdings()
        # Robustly sum market value, ignoring any holdings where it is not set.
        total_market_value = sum(h.get('market_value', 0) for h in holdings if h.get('market_value') is not None)
        return {"total_market_value": total_market_value}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Failed to calculate portfolio summary.")


# --- NEW Endpoints for Filtering and Charts --- #

@app.get("/api/filter-options", tags=["Filters"])
async def get_filter_options():
    try:
        options = db.get_filter_options()
        return options
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Failed to retrieve filter options.")

@app.get("/api/analysis/cashflow-chart", tags=["Analysis"])
async def get_cashflow_chart(filters: Dict[str, Any] = Depends(get_transaction_filters)):
    try:
        chart_data = analysis.prepare_cashflow_chart_data(filters)
        return chart_data
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Failed to generate cashflow chart data.")

@app.get("/api/analysis/portfolio-chart", tags=["Analysis"])
async def get_portfolio_chart(filters: Dict[str, Any] = Depends(get_holding_filters)):
    try:
        chart_data = analysis.prepare_portfolio_chart_data(filters)
        return chart_data
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Failed to generate portfolio chart data.")


# --- Account Management --- #

@app.get("/api/accounts", response_model=List[str], tags=["Accounts"])
async def get_all_accounts():
    """Returns a list of all unique account IDs known to the system."""
    return db.get_all_account_ids()

@app.get("/api/accounts/visibility", response_model=Dict[str, bool], tags=["Accounts"])
async def get_visibility_settings():
    """Returns the current visibility settings for all accounts."""
    return db.get_account_visibility()

@app.put("/api/accounts/visibility", status_code=204, tags=["Accounts"])
async def update_visibility_settings(payload: AccountVisibilitySettings):
    """Updates the visibility settings for one or more accounts."""
    try:
        db.set_account_visibility(payload.settings)
        return Response(status_code=204)
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to update settings: {e}")

@app.post("/api/data/purge", tags=["Admin"])
async def purge_data(request: PurgeRequest):
    """
    [DANGEROUS] Purges all data from a specified table.
    Currently supports 'transactions' and 'holdings'.
    This is a permanent and irreversible action.
    """
    try:
        result = db.purge_table_data(request.target)
        return {"message": f"Successfully purged table: {request.target}", "details": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"An internal error occurred during data purge: {e}")

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
