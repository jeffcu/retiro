import uvicorn
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os
import traceback
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field
from decimal import Decimal

from src.importers import csv_importer, holdings_importer
from src.database import initialize_database, save_transactions, save_holdings
from src.data_model import CashflowType
from src import database as db
from src import analysis
from src import rules_engine

# Load environment variables from .env file
load_dotenv()

app = FastAPI(
    title="Curie Trust Financial Control Center API",
    version="1.0",
)

# --- CORS Middleware ---
origins = [
    "http://localhost:5173",  # Vite dev server
    "http://127.0.0.1:5173", # Also common
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Pydantic Models for API data validation ---
class RuleCreate(BaseModel):
    pattern: str
    category: str
    cashflow_type: CashflowType
    tags: Optional[List[str]] = []
    priority: Optional[int] = 100

class RuleResponse(RuleCreate):
    rule_id: str

# --- Event Handlers ---
@app.on_event("startup")
async def startup_event():
    print("API is starting up...")
    initialize_database()
    
    api_key = os.getenv("ALPHA_VANTAGE_API_KEY")
    if not api_key or api_key == "YOUR_API_KEY_HERE":
        print("WARNING: ALPHA_VANTAGE_API_KEY is not set. Market data features will fail.")

# --- API Endpoints ---

@app.get("/")
async def root():
    return {"message": "Curie Trust Financial Control Center API is running."}


@app.post("/api/import/transactions", tags=["Import"])
async def import_transactions_csv(account_id: str = Form(...), file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith('.csv'):
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a CSV.")

    contents = await file.read()
    try:
        transactions = csv_importer.parse_standard_csv(contents, account_id)
        save_transactions(transactions)
        print(f"Successfully processed {len(transactions)} transactions for account {account_id}.")
        return {
            "message": f"Successfully imported and saved {len(transactions)} transactions.",
            "filename": file.filename,
            "transaction_count": len(transactions)
        }
    except Exception as e:
        print(f"ERROR processing file {file.filename}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process CSV file: {e}")

@app.post("/api/import/holdings", tags=["Import"])
async def import_holdings_csv(account_id: str = Form(...), file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith('.csv'):
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a CSV.")
    
    contents = await file.read()
    try:
        holdings = holdings_importer.parse_holdings_csv(contents, account_id)
        save_holdings(holdings)
        return {
            "message": f"Successfully imported and saved {len(holdings)} holdings.",
            "filename": file.filename,
            "holdings_count": len(holdings)
        }
    except Exception as e:
        print(f"ERROR processing holdings file {file.filename}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process holdings CSV file: {e}")

# --- Rules API --- 
@app.post("/api/rules", response_model=RuleResponse, status_code=201, tags=["Rules"])
async def create_new_rule(rule: RuleCreate):
    rule_dict = rule.dict()
    rule_dict['cashflow_type'] = rule_dict['cashflow_type'].value
    created_rule = db.create_rule(rule_dict)
    return created_rule

@app.get("/api/rules", response_model=List[RuleResponse], tags=["Rules"])
async def get_all_rules():
    rules = db.get_all_rules()
    return rules

# --- Data & Analysis API ---
@app.get("/api/sankey/income", tags=["Analysis"])
async def get_income_sankey_data(period: str = "all") -> Dict[str, List[Dict[str, Any]]]:
    try:
        data = analysis.generate_income_sankey(period)
        return data
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"An internal error occurred in the analysis engine: {e}")

@app.get("/api/transactions", tags=["Data"])
async def get_all_transactions_for_display():
    try:
        return db.get_all_transactions()
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"An internal error occurred while fetching transactions: {e}")

@app.post("/api/transactions/recategorize", tags=["Processing"])
async def trigger_recategorization():
    try:
        count = rules_engine.recategorize_all_transactions()
        return {"message": f"Successfully re-categorized {count} transactions."}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"An internal error occurred during re-categorization: {e}")

@app.get("/api/holdings", tags=["Data"])
async def get_all_holdings():
    try:
        return db.get_all_holdings()
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Failed to retrieve holdings.")

@app.get("/api/portfolio/summary", tags=["Analysis"])
async def get_portfolio_summary():
    """Calculates the total market value of all holdings."""
    try:
        holdings = db.get_all_holdings()
        total_market_value = sum(h.get('market_value', 0) for h in holdings if h.get('market_value'))
        return {"total_market_value": total_market_value}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Failed to calculate portfolio summary.")

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
