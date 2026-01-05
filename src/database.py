import sqlite3
from pathlib import Path
from typing import List
from src.data_model import Transaction

# Per MDS, the database is a single file in the data/ directory.
# We resolve the path to its absolute form to avoid ambiguity.
DB_FILE = (Path(__file__).parent.parent / "data" / "trust.db").resolve()

def get_db_connection():
    """ Establishes a connection to the SQLite database. """
    # Ensure the data directory exists
    DB_FILE.parent.mkdir(exist_ok=True)
    
    # Use the string representation of the path for sqlite3.connect
    conn = sqlite3.connect(str(DB_FILE))
    conn.row_factory = sqlite3.Row
    return conn

def initialize_database():
    """
    Creates the necessary tables in the database if they don't already exist,
    based on the schema defined in the MDS and src/data_model.py.
    """
    print(f"--- Initializing database at: {DB_FILE} ---")
    conn = get_db_connection()
    cursor = conn.cursor()

    # Per Phase 0 requirements, create the 'transactions' table.
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS transactions (
        transaction_id TEXT PRIMARY KEY,
        account_id TEXT NOT NULL,
        transaction_date TEXT NOT NULL,
        amount REAL NOT NULL,
        description TEXT NOT NULL,
        merchant TEXT,
        category TEXT,
        cashflow_type TEXT,
        is_transfer INTEGER,
        asset_id TEXT,
        import_run_id TEXT,
        raw_data_hash TEXT UNIQUE
    );
    """)

    conn.commit()
    conn.close()
    print("--- Database initialization complete. ---")

def save_transactions(transactions: List[Transaction]):
    """
    Saves a list of Transaction objects to the database.
    Uses a transaction to ensure all or nothing is saved.
    """
    if not transactions:
        return

    conn = get_db_connection()
    cursor = conn.cursor()
    
    # The UNIQUE constraint on raw_data_hash will prevent duplicates on re-import.
    sql = """INSERT OR IGNORE INTO transactions (
                 transaction_id, account_id, transaction_date, amount, description, 
                 merchant, category, cashflow_type, is_transfer, asset_id, 
                 import_run_id, raw_data_hash
             ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);"""
    
    # This data tuple must match the SQL columns exactly (12 items).
    data_to_insert = [
        (
            t.transaction_id, t.account_id, t.transaction_date.isoformat(), t.amount, t.description,
            t.merchant, t.category, t.cashflow_type.value if t.cashflow_type else None,
            1 if t.is_transfer else 0, t.asset_id, t.import_run_id, t.raw_data_hash
        ) for t in transactions
    ]

    try:
        cursor.executemany(sql, data_to_insert)
        conn.commit()
        # The cursor.rowcount tells us how many rows were actually inserted (not ignored).
        print(f"Successfully saved {cursor.rowcount} new transactions to the database.")
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        conn.rollback()
    finally:
        conn.close()
