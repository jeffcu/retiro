import sqlite3
from pathlib import Path

# Per MDS, the database is a single file in the data/ directory.
DB_FILE = Path(__file__).parent.parent / "data" / "trust.db"

def get_db_connection():
    """ Establishes a connection to the SQLite database. """
    # Ensure the data directory exists
    DB_FILE.parent.mkdir(exist_ok=True)
    
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def initialize_database():
    """
    Creates the necessary tables in the database if they don't already exist,
    based on the schema defined in the MDS and src/data_model.py.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # This is a placeholder for the full schema creation logic.
    # We will build this out as we implement each feature.
    # Starting with the 'transactions' table for Phase 0.
    
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
        raw_data_hash TEXT
    );
    """)

    # We will add more tables here as we progress through the phases:
    # accounts, assets, holdings, price_history, rules, import_profiles, etc.

    print("Database initialized.")
    conn.commit()
    conn.close()

if __name__ == '__main__':
    print(f"Initializing database at: {DB_FILE}")
    initialize_database()
