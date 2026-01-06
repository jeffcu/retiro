import sqlite3
import uuid
from pathlib import Path
from typing import List, Dict, Any
from src.data_model import Transaction, Holding

# Per MDS, the database is a single file in the data/ directory.
# We resolve the path to its absolute form to avoid ambiguity.
DB_FILE = (Path(__file__).parent.parent / "data" / "trust.db").resolve()
_schema_ensured = False

def _ensure_schema(conn: sqlite3.Connection):
    """
    Ensures the necessary tables exist in the database and performs migrations.
    This is designed to be idempotent and safe to call.
    """
    global _schema_ensured
    if _schema_ensured:
        return

    print("--- Verifying database schema... ---")
    cursor = conn.cursor()

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

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS rules (
        rule_id TEXT PRIMARY KEY,
        pattern TEXT NOT NULL,
        category TEXT NOT NULL,
        cashflow_type TEXT NOT NULL,
        tags TEXT, -- Comma-separated list
        priority INTEGER DEFAULT 100
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS holdings (
        holding_id TEXT PRIMARY KEY,
        account_id TEXT NOT NULL,
        symbol TEXT NOT NULL,
        quantity REAL NOT NULL,
        cost_basis REAL NOT NULL,
        market_value REAL, 
        last_price REAL,
        last_price_timestamp TEXT,
        UNIQUE(account_id, symbol)
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS import_runs (
        import_run_id TEXT PRIMARY KEY,
        file_name TEXT NOT NULL,
        import_type TEXT NOT NULL,
        import_timestamp TEXT NOT NULL,
        record_count INTEGER,
        total_amount REAL,
        total_market_value REAL,
        total_cost_basis REAL
    );
    """)

    # --- Schema Migrations ---
    cursor.execute("PRAGMA table_info(holdings)")
    holdings_cols = {row[1] for row in cursor.fetchall()}
    if 'market_value' not in holdings_cols:
        print("--- MIGRATING SCHEMA: Adding 'market_value' to 'holdings'. ---")
        cursor.execute("ALTER TABLE holdings ADD COLUMN market_value REAL;")

    cursor.execute("PRAGMA table_info(transactions)")
    trans_cols = {row[1] for row in cursor.fetchall()}
    if 'institution' not in trans_cols:
        print("--- MIGRATING SCHEMA: Adding 'institution' to 'transactions'. ---")
        cursor.execute("ALTER TABLE transactions ADD COLUMN institution TEXT;")
    if 'original_category' not in trans_cols:
        print("--- MIGRATING SCHEMA: Adding 'original_category' to 'transactions'. ---")
        cursor.execute("ALTER TABLE transactions ADD COLUMN original_category TEXT;")
    if 'tags' not in trans_cols:
        print("--- MIGRATING SCHEMA: Adding 'tags' to 'transactions'. ---")
        cursor.execute("ALTER TABLE transactions ADD COLUMN tags TEXT;")

    conn.commit()
    print("--- Database schema is OK. ---")
    _schema_ensured = True

def get_db_connection():
    """ Establishes a connection to the SQLite database and ensures the schema is present. """
    DB_FILE.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(str(DB_FILE))
    conn.row_factory = sqlite3.Row
    _ensure_schema(conn)
    return conn

def initialize_database():
    print(f"--- Initializing database at: {DB_FILE} ---")
    conn = get_db_connection()
    conn.close()
    print("--- Database initialization complete. ---")

def save_transactions(transactions: List[Transaction]):
    if not transactions:
        return
    conn = get_db_connection()
    cursor = conn.cursor()
    sql = """INSERT OR REPLACE INTO transactions (
                 transaction_id, account_id, transaction_date, amount, description, 
                 merchant, category, cashflow_type, is_transfer, asset_id, 
                 import_run_id, raw_data_hash, institution, original_category, tags
             ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);"""
    data_to_insert = [
        (
            t.transaction_id, t.account_id, t.transaction_date.isoformat(), float(t.amount), t.description,
            t.merchant, t.category, t.cashflow_type.value if t.cashflow_type else None,
            1 if t.is_transfer else 0, t.asset_id, t.import_run_id, t.raw_data_hash,
            t.institution, t.original_category, ','.join(t.tags) if t.tags else None
        ) for t in transactions
    ]
    try:
        cursor.executemany(sql, data_to_insert)
        conn.commit()
        print(f"Successfully saved/updated {cursor.rowcount} transactions to the database.")
    except sqlite3.Error as e:
        print(f"Database error during transaction save: {e}")
        conn.rollback()
        raise e
    finally:
        conn.close()

def save_holdings_snapshot(holdings: List[Holding], account_id: str):
    """
    Saves a complete snapshot of holdings for a specific account.
    This is a transactional operation that first deletes all existing holdings
    for the account and then inserts the new ones.
    (PRS Section 11: Idempotent Import)
    """
    cleaned_account_id = account_id.strip() # Defensively sanitize input
    if not cleaned_account_id:
        print("ERROR: Cannot save holdings snapshot without an account_id.")
        return 0, 0

    conn = get_db_connection()
    cursor = conn.cursor()
    deleted_count = 0
    inserted_count = 0

    try:
        # Step 1: Delete existing holdings (CASE-INSENSITIVE & WHITESPACE-INSENSITIVE)
        # CORRECTED: Use trim() and lower() to handle existing dirty data.
        cursor.execute("DELETE FROM holdings WHERE trim(lower(account_id)) = trim(lower(?))", (cleaned_account_id,))
        deleted_count = cursor.rowcount
        print(f"Deleted {deleted_count} stale holdings for account '{cleaned_account_id}'.")

        # Step 2: Insert the new holdings
        if holdings:
            sql = """INSERT INTO holdings (
                        holding_id, account_id, symbol, quantity, cost_basis, market_value
                     ) VALUES (?, ?, ?, ?, ?, ?);"""
            # Note: The `h.account_id` in the holdings list is assumed to be cleaned
            # at the API layer before this function is called.
            data_to_insert = [
                (
                    h.holding_id, h.account_id, h.symbol, float(h.quantity), float(h.cost_basis),
                    float(h.market_value) if h.market_value is not None else None
                ) for h in holdings
            ]
            cursor.executemany(sql, data_to_insert)
            inserted_count = cursor.rowcount
            print(f"Inserted {inserted_count} new holdings for account '{cleaned_account_id}'.")

        conn.commit()
    except sqlite3.Error as e:
        print(f"Database error during holdings snapshot save: {e}")
        conn.rollback()
        raise e
    finally:
        conn.close()
    
    return deleted_count, inserted_count

def save_import_run(run_data: Dict[str, Any]):
    conn = get_db_connection()
    cursor = conn.cursor()
    sql = """INSERT INTO import_runs (
                 import_run_id, file_name, import_type, import_timestamp,
                 record_count, total_amount, total_market_value, total_cost_basis
             ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);"""
    
    data_tuple = (
        run_data['import_run_id'],
        run_data['file_name'],
        run_data['import_type'],
        run_data['import_timestamp'],
        run_data.get('record_count'),
        run_data.get('total_amount'),
        run_data.get('total_market_value'),
        run_data.get('total_cost_basis')
    )
    
    try:
        cursor.execute(sql, data_tuple)
        conn.commit()
        print(f"Successfully saved import run {run_data['import_run_id']}.")
    except sqlite3.Error as e:
        print(f"Database error during import run save: {e}")
        conn.rollback()
        raise e
    finally:
        conn.close()

# --- Data Retrieval --- #

def get_all_transactions() -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM transactions ORDER BY transaction_date DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_all_holdings() -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM holdings ORDER BY symbol ASC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_all_import_runs() -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM import_runs ORDER BY import_timestamp DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

# --- Rules CRUD --- #

def _transform_rule_record(rule_row: sqlite3.Row) -> Dict[str, Any]:
    if not rule_row:
        return None
    rule_dict = dict(rule_row)
    if rule_dict.get('tags') and isinstance(rule_dict['tags'], str):
        rule_dict['tags'] = [tag.strip() for tag in rule_dict['tags'].split(',') if tag.strip()]
    else:
        rule_dict['tags'] = []
    return rule_dict

def create_rule(rule_data: Dict[str, Any]) -> Dict[str, Any]:
    conn = get_db_connection()
    cursor = conn.cursor()
    rule_id = str(uuid.uuid4())
    sql = """INSERT INTO rules (rule_id, pattern, category, cashflow_type, tags, priority)
             VALUES (?, ?, ?, ?, ?, ?);"""
    cursor.execute(sql, (
        rule_id,
        rule_data['pattern'],
        rule_data['category'],
        rule_data['cashflow_type'],
        ','.join(rule_data.get('tags', [])),
        rule_data.get('priority', 100)
    ))
    conn.commit()
    new_rule_cursor = conn.cursor()
    new_rule_cursor.execute("SELECT * FROM rules WHERE rule_id = ?", (rule_id,))
    new_rule = new_rule_cursor.fetchone()
    conn.close()
    return _transform_rule_record(new_rule)

def get_rule(rule_id: str) -> Dict[str, Any] | None:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM rules WHERE rule_id = ?", (rule_id,))
    rule_row = cursor.fetchone()
    conn.close()
    return _transform_rule_record(rule_row)

def get_all_rules() -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM rules ORDER BY priority ASC, category ASC")
    rule_rows = cursor.fetchall()
    conn.close()
    return [_transform_rule_record(row) for row in rule_rows]

def delete_rule(rule_id: str) -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM rules WHERE rule_id = ?", (rule_id,))
    deleted_count = cursor.rowcount
    conn.commit()
    conn.close()
    return deleted_count > 0

# --- Admin Utilities --- #

SAFE_TO_PURGE = ["transactions", "holdings"]

def purge_table_data(target_table: str) -> dict:
    """
    Deletes all data from a specified table if it's in the SAFE_TO_PURGE list.
    This is a destructive operation.
    """
    if target_table not in SAFE_TO_PURGE:
        raise ValueError(f"'{target_table}' is not a table that can be purged.")

    conn = get_db_connection()
    cursor = conn.cursor()
    deleted_count = 0
    
    try:
        cursor.execute(f"SELECT COUNT(*) FROM {target_table}")
        initial_count = cursor.fetchone()[0]

        cursor.execute(f"DELETE FROM {target_table};")
        deleted_count = cursor.rowcount
        conn.commit()

        print(f"Successfully purged {deleted_count} records from '{target_table}'.")
        return {
            "table": target_table,
            "purged_records": deleted_count,
            "initial_records": initial_count,
            "status": "success"
        }
    except sqlite3.Error as e:
        print(f"Database error during purge of '{target_table}': {e}")
        conn.rollback()
        raise e
    finally:
        conn.close()
