import uvicorn
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os
import traceback
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field

from src.importers import csv_importer
from src.database import initialize_database, save_transactions
from src.data_model import CashflowType
from src import database as db
from src import analysis

# Load environment variables from .env file
load_dotenv()

app = FastAPI(
    title="Curie Trust Financial Control Center API",
    version="1.0",
)

# --- CORS Middleware ---
# This is necessary to allow the frontend (running on a different port)
# to communicate with the backend, especially for non-simple requests like POST with JSON.
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
    # Initialize the database and create tables if they don't exist
    initialize_database()
    
    api_key = os.getenv("ALPHA_VANTAGE_API_KEY")
    if not api_key or api_key == "YOUR_API_KEY_HERE":
        print("WARNING: ALPHA_VANTAGE_API_KEY is not set. Market data features will fail.")

# --- API Endpoints ---

@app.get("/")
async def root():
    return {"message": "Curie Trust Financial Control Center API is running."}


@app.post("/api/import/csv", tags=["Import"])
async def import_transactions_csv(account_id: str = Form(...), file: UploadFile = File(...)):
    """
    Accepts a CSV file, parses it, applies categorization rules, and stores the transactions.
    (PRS Section 5.2, 5.3)
    """
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


# --- Rules API --- (Phase 1)
@app.post("/api/rules", response_model=RuleResponse, status_code=201, tags=["Rules"])
async def create_new_rule(rule: RuleCreate):
    """ Creates a new categorization rule. """
    rule_dict = rule.dict()
    # Convert enum to its string value for DB storage
    rule_dict['cashflow_type'] = rule_dict['cashflow_type'].value
    created_rule = db.create_rule(rule_dict)
    return created_rule

@app.get("/api/rules", response_model=List[RuleResponse], tags=["Rules"])
async def get_all_rules():
    """ Retrieves all categorization rules. """
    rules = db.get_all_rules()
    return rules

@app.get("/api/rules/{rule_id}", response_model=RuleResponse, tags=["Rules"])
async def get_specific_rule(rule_id: str):
    """ Retrieves a single rule by its ID. """
    rule = db.get_rule(rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    return rule

@app.delete("/api/rules/{rule_id}", status_code=204, tags=["Rules"])
async def delete_existing_rule(rule_id: str):
    """ Deletes a rule by its ID. """
    success = db.delete_rule(rule_id)
    if not success:
        raise HTTPException(status_code=404, detail="Rule not found")
    return None # FastAPI will return a 204 No Content response


# --- Data & Analysis API ---
@app.get("/api/sankey/income", tags=["Analysis"])
async def get_income_sankey_data(period: str = "all") -> Dict[str, List[Dict[str, Any]]]:
    """ 
    Generates the data for the main Income->Uses Sankey diagram.
    Now powered by the analysis module.
    """
    try:
        data = analysis.generate_income_sankey(period)
        return data
    except Exception as e:
        # Log the full traceback to the backend console for diagnosis
        print(f"\n---! ERROR IN /api/sankey/income ENDPOINT !---")
        traceback.print_exc()
        print(f"---! END OF ERROR TRACEBACK !---\n")
        # Re-raise as a standard HTTPException to inform the client
        raise HTTPException(status_code=500, detail=f"An internal error occurred in the analysis engine: {e}")

@app.get("/api/transactions", tags=["Data"])
async def get_all_transactions_for_display():
    """ Retrieves all transactions from the database for display or debugging. """
    try:
        transactions = db.get_all_transactions()
        return transactions
    except Exception as e:
        print(f"\n---! ERROR IN /api/transactions ENDPOINT !---")
        traceback.print_exc()
        print(f"---! END OF ERROR TRACEBACK !---\n")
        raise HTTPException(status_code=500, detail=f"An internal error occurred while fetching transactions: {e}")

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
