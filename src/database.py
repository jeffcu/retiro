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

    # The canonical schema for the 'holdings' table.
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

    # --- Schema Migration for 'holdings' table ---
    # Check for the existence of 'market_value' column and add it if missing.
    # This ensures backward compatibility with older database files.
    cursor.execute("PRAGMA table_info(holdings)")
    columns = [row[1] for row in cursor.fetchall()]

    if 'market_value' not in columns:
        print("--- MIGRATING SCHEMA: Adding 'market_value' column to 'holdings' table. ---")
        cursor.execute("ALTER TABLE holdings ADD COLUMN market_value REAL;")
        print("--- MIGRATION COMPLETE. ---")

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
                 import_run_id, raw_data_hash
             ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);"""
    data_to_insert = [
        (
            t.transaction_id, t.account_id, t.transaction_date.isoformat(), float(t.amount), t.description,
            t.merchant, t.category, t.cashflow_type.value if t.cashflow_type else None,
            1 if t.is_transfer else 0, t.asset_id, t.import_run_id, t.raw_data_hash
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

def save_holdings(holdings: List[Holding]):
    if not holdings:
        return
    conn = get_db_connection()
    cursor = conn.cursor()

    sql = """INSERT OR REPLACE INTO holdings (
                holding_id, account_id, symbol, quantity, cost_basis, market_value
             ) VALUES (?, ?, ?, ?, ?, ?);"""
    data_to_insert = [
        (
            h.holding_id, h.account_id, h.symbol, float(h.quantity), float(h.cost_basis),
            float(h.market_value) if h.market_value is not None else None
        ) for h in holdings
    ]
    try:
        cursor.executemany(sql, data_to_insert)
        conn.commit()
        print(f"Successfully saved/updated {cursor.rowcount} holdings.")
    except sqlite3.Error as e:
        print(f"Database error during holdings save: {e}")
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
