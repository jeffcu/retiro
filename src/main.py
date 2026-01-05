import uvicorn
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from dotenv import load_dotenv
import os

from src.importers import csv_importer
from src.database import initialize_database, get_db_connection, save_transactions

# Load environment variables from .env file
load_dotenv()

app = FastAPI(
    title="Curie Trust Financial Control Center API",
    version="1.0",
)

@app.on_event("startup")
async def startup_event():
    print("API is starting up...")
    # Initialize the database and create tables if they don't exist
    initialize_database()
    
    api_key = os.getenv("ALPHA_VANTAGE_API_KEY")
    if not api_key or api_key == "YOUR_API_KEY_HERE":
        print("WARNING: ALPHA_VANTAGE_API_KEY is not set. Market data features will fail.")


@app.get("/")
async def root():
    return {"message": "Curie Trust Financial Control Center API is running."}


@app.post("/api/import/csv")
async def import_transactions_csv(account_id: str = Form(...), file: UploadFile = File(...)):
    """
    Accepts a CSV file, parses it, and stores the transactions.
    (PRS Section 5.2)
    """
    # Using the filename extension is more robust than checking the content_type header,
    # which can be inconsistent between different clients (like curl).
    if not file.filename or not file.filename.lower().endswith('.csv'):
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a CSV.")

    contents = await file.read()
    try:
        transactions = csv_importer.parse_standard_csv(contents, account_id)
        
        # Persist the parsed transactions to the database
        save_transactions(transactions)
        
        print(f"Successfully processed {len(transactions)} transactions for account {account_id}.")
        return {
            "message": f"Successfully imported and saved {len(transactions)} transactions.",
            "filename": file.filename,
            "transaction_count": len(transactions)
        }
    except Exception as e:
        # It's good practice to log the actual error for diagnostics
        print(f"ERROR processing file {file.filename}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process CSV file: {e}")


# Placeholder for Phase 0 endpoint
@app.get("/api/sankey/income")
async def get_income_sankey_data(period: str = "YTD"):
    # This will eventually call the analysis module to generate Sankey data
    return {
        "period": period,
        "nodes": [
            {"id": "Income"},
            {"id": "Expenses"},
            {"id": "Savings"}
        ],
        "links": [
            {"source": "Income", "target": "Expenses", "value": 8000},
            {"source": "Income", "target": "Savings", "value": 2000},
        ]
    }

if __name__ == "__main__":
    # Note: The command 'uvicorn src.main:app --reload' should be run from the project root.
    # Running this file directly is not the intended use for a uvicorn server with reload.
    uvicorn.run(app, host="127.0.0.1", port=8000)