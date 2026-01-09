import sqlite3
import uuid
from pathlib import Path
from typing import List, Dict, Any, Tuple
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
        pattern TEXT,
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
    
    # --- NEW: Table for Account Visibility Settings --- #
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS account_visibility (
        account_id TEXT PRIMARY KEY,
        is_visible INTEGER NOT NULL DEFAULT 1
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

    # --- Advanced Rules Table Migration ---
    cursor.execute("PRAGMA table_info(rules)")
    rules_info_rows = cursor.fetchall()
    rules_cols_info = {row['name']: row for row in rules_info_rows}

    # MIGRATION: Make 'rules.pattern' nullable if it was previously defined as NOT NULL.
    if 'pattern' in rules_cols_info and rules_cols_info['pattern']['notnull'] == 1:
        print("--- MIGRATING SCHEMA: Making 'pattern' column in 'rules' table nullable. ---")
        try:
            cursor.execute("PRAGMA foreign_keys=off;")
            cursor.execute("BEGIN TRANSACTION;")
            cursor.execute("ALTER TABLE rules RENAME TO _rules_old;")
            
            # Recreate the table with the full, modern schema where 'pattern' is nullable.
            cursor.execute("""
            CREATE TABLE rules (
                rule_id TEXT PRIMARY KEY,
                pattern TEXT, -- This is now correctly nullable
                category TEXT NOT NULL,
                cashflow_type TEXT NOT NULL,
                tags TEXT,
                priority INTEGER DEFAULT 100,
                case_sensitive INTEGER DEFAULT 0,
                account_filter_mode TEXT DEFAULT 'include',
                account_filter_list TEXT,
                condition_category TEXT,
                condition_institution TEXT,
                condition_cashflow_type TEXT,
                condition_tags TEXT
            );
            """)
            
            # Copy data from the old table, matching existing columns.
            old_cols = list(rules_cols_info.keys())
            old_cols_str = ", ".join([f'\"{c}\"' for c in old_cols])
            cursor.execute(f"INSERT INTO rules ({old_cols_str}) SELECT {old_cols_str} FROM _rules_old;")
            
            cursor.execute("DROP TABLE _rules_old;")
            cursor.execute("COMMIT;")
            print("--- 'rules' table migration successful. ---")
        except Exception as e:
            print(f"ERROR during 'rules' table migration: {e}. Rolling back.")
            cursor.execute("ROLLBACK;")
            raise e
        finally:
            cursor.execute("PRAGMA foreign_keys=on;")
            # After migration, we need to refresh the column info.
            cursor.execute("PRAGMA table_info(rules)")
            rules_cols_info = {row['name']: row for row in cursor.fetchall()}

    # Subsequent migrations for adding columns one-by-one.
    rules_cols = set(rules_cols_info.keys())
    if 'case_sensitive' not in rules_cols:
        print("--- MIGRATING SCHEMA: Adding 'case_sensitive' to 'rules'. ---")
        cursor.execute("ALTER TABLE rules ADD COLUMN case_sensitive INTEGER DEFAULT 0;")
    if 'account_filter_mode' not in rules_cols:
        print("--- MIGRATING SCHEMA: Adding 'account_filter_mode' to 'rules'. ---")
        cursor.execute("ALTER TABLE rules ADD COLUMN account_filter_mode TEXT DEFAULT 'include';")
    if 'account_filter_list' not in rules_cols:
        print("--- MIGRATING SCHEMA: Adding 'account_filter_list' to 'rules'. ---")
        cursor.execute("ALTER TABLE rules ADD COLUMN account_filter_list TEXT;")
    if 'condition_category' not in rules_cols:
        print("--- MIGRATING SCHEMA: Adding 'condition_category' to 'rules'. ---")
        cursor.execute("ALTER TABLE rules ADD COLUMN condition_category TEXT;")
    if 'condition_institution' not in rules_cols:
        print("--- MIGRATING SCHEMA: Adding 'condition_institution' to 'rules'. ---")
        cursor.execute("ALTER TABLE rules ADD COLUMN condition_institution TEXT;")
    if 'condition_cashflow_type' not in rules_cols:
        print("--- MIGRATING SCHEMA: Adding 'condition_cashflow_type' to 'rules'. ---")
        cursor.execute("ALTER TABLE rules ADD COLUMN condition_cashflow_type TEXT;")
    if 'condition_tags' not in rules_cols:
        print("--- MIGRATING SCHEMA: Adding 'condition_tags' to 'rules'. ---")
        cursor.execute("ALTER TABLE rules ADD COLUMN condition_tags TEXT;")

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

def _build_where_clause(filters: Dict, allowed_fields: List[str]) -> Tuple[str, List[Any]]:
    """Helper to build a dynamic WHERE clause safely."""
    clauses = []
    params = []

    if not filters:
        return "", []

    for key, value in filters.items():
        if key not in allowed_fields:
            continue
        
        if key in ['description', 'tags']:
            clauses.append(f"{key} LIKE ?")
            params.append(f"%{value}%")
        else:
            clauses.append(f"{key} = ?")
            params.append(value)
    
    if not clauses:
        return "", []

    return f"WHERE {" AND ".join(clauses)}", params

def get_transactions(filters: Dict[str, Any] = None, exclude_invisible: bool = False) -> List[Dict[str, Any]]:
    """ 
    Retrieves transactions, with options for filtering.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    base_query = "SELECT * FROM transactions"
    where_clauses = []
    params = []

    if exclude_invisible:
        where_clauses.append("account_id NOT IN (SELECT account_id FROM account_visibility WHERE is_visible = 0)")

    if filters:
        allowed = ['category', 'account_id', 'institution', 'description', 'tags', 'cashflow_type']
        for key, value in filters.items():
            if key in allowed:
                if key in ['description', 'tags']:
                    where_clauses.append(f"{key} LIKE ?")
                    params.append(f'%{value}%')
                else:
                    where_clauses.append(f"{key} = ?")
                    params.append(value)

    if where_clauses:
        base_query += " WHERE " + " AND ".join(where_clauses)

    base_query += " ORDER BY transaction_date DESC"

    cursor.execute(base_query, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_holdings(filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()

    allowed_fields = ['account_id', 'symbol']
    where_clause, params = _build_where_clause(filters, allowed_fields)

    query = f"SELECT * FROM holdings {where_clause} ORDER BY symbol ASC"
    
    cursor.execute(query, params)
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

# --- Filter Options --- #

def get_filter_options() -> Dict[str, List[str]]:
    """Gets unique values for filter dropdowns."""
    conn = get_db_connection()
    cursor = conn.cursor()

    options = {}

    cursor.execute("SELECT DISTINCT category FROM transactions WHERE category IS NOT NULL AND category != '' AND category != 'Uncategorized' ORDER BY category")
    
    fetched_rows = cursor.fetchall()
    options['categories'] = [row['category'] for row in fetched_rows]

    cursor.execute("SELECT DISTINCT account_id FROM transactions ORDER BY account_id")
    options['accounts'] = [row['account_id'] for row in cursor.fetchall()]

    cursor.execute("SELECT DISTINCT institution FROM transactions WHERE institution IS NOT NULL ORDER BY institution")
    options['institutions'] = [row['institution'] for row in cursor.fetchall()]

    # ADDED: Hardcode cashflow types based on the spec
    options['cashflowTypes'] = [
        "Income", 
        "Expense", 
        "Transfer", 
        "Capital Expenditure", 
        "Investment"
    ]

    conn.close()
    return options


# --- Aggregations for Charts --- #

def get_sankey_aggregates(exclude_invisible: bool = False) -> List[Dict[str, Any]]:
    """
    Performs a direct SQL aggregation to get the data needed for the Income Sankey.
    This is more efficient than fetching all transactions. It correctly filters by
    account visibility and only considers operational cashflow types.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    where_clauses = ["t.cashflow_type IN ('Income', 'Expense', 'Capital Expenditure')"]
    
    if exclude_invisible:
        where_clauses.append("t.account_id NOT IN (SELECT account_id FROM account_visibility WHERE is_visible = 0)")

    where_sql = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""

    query = f"""
        SELECT 
            cashflow_type,
            category,
            SUM(amount) as total
        FROM transactions t
        {where_sql}
        GROUP BY cashflow_type, category
    """
    
    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_latest_transaction_year() -> int | None:
    """Finds the most recent year present in the transaction data."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT MAX(strftime('%Y', transaction_date)) as latest_year FROM transactions")
    result = cursor.fetchone()
    conn.close()
    if result and result['latest_year']:
        return int(result['latest_year'])
    return None

def get_cashflow_aggregation_by_month(year: int, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()

    allowed_fields = ['category', 'account_id', 'institution', 'description', 'tags', 'cashflow_type']
    where_clause, params = _build_where_clause(filters, allowed_fields)
    
    # Prepend year filter to where clause
    if where_clause:
        final_where = f"WHERE strftime('%Y', transaction_date) = ? AND ({where_clause[6:]})"
    else:
        final_where = f"WHERE strftime('%Y', transaction_date) = ?"

    final_params = [str(year)] + params

    query = f"""
        SELECT 
            CAST(strftime('%m', transaction_date) AS INTEGER) as month,
            SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END) as income,
            SUM(CASE WHEN amount < 0 AND cashflow_type = 'Expense' THEN amount ELSE 0 END) as expense
        FROM transactions
        {final_where}
        GROUP BY month
        ORDER BY month ASC
    """

    cursor.execute(query, final_params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_holdings_aggregation_by_symbol(filters: Dict[str, Any]) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()

    allowed_fields = ['account_id', 'symbol']
    where_clause, params = _build_where_clause(filters, allowed_fields)

    query = f"""
        SELECT
            symbol,
            SUM(market_value) as total_market_value
        FROM holdings
        {where_clause}
        GROUP BY symbol
        HAVING total_market_value > 0
        ORDER BY total_market_value DESC
        LIMIT 20
    """
    cursor.execute(query, params)
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

    if rule_dict.get('account_filter_list') and isinstance(rule_dict['account_filter_list'], str):
        rule_dict['account_filter_list'] = [acc.strip() for acc in rule_dict['account_filter_list'].split(',') if acc.strip()]
    else:
        rule_dict['account_filter_list'] = []
        
    rule_dict['case_sensitive'] = bool(rule_dict.get('case_sensitive', 0))

    return rule_dict

def create_rule(rule_data: Dict[str, Any]) -> Dict[str, Any]:
    conn = get_db_connection()
    cursor = conn.cursor()
    rule_id = str(uuid.uuid4())
    sql = """INSERT INTO rules (
                rule_id, pattern, category, cashflow_type, tags, priority, 
                case_sensitive, account_filter_mode, account_filter_list,
                condition_category, condition_institution, condition_cashflow_type, condition_tags
             ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);"""
    
    tags_str = ','.join(rule_data.get('tags', []))
    account_list_str = ','.join(rule_data.get('account_filter_list', []))
    
    cursor.execute(sql, (
        rule_id,
        rule_data.get('pattern'),
        rule_data['category'],
        rule_data['cashflow_type'],
        tags_str,
        rule_data.get('priority', 100),
        1 if rule_data.get('case_sensitive') else 0,
        rule_data.get('account_filter_mode', 'include'),
        account_list_str,
        rule_data.get('condition_category'),
        rule_data.get('condition_institution'),
        rule_data.get('condition_cashflow_type'),
        rule_data.get('condition_tags')
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

# --- Account Management --- #

def get_all_account_ids() -> List[str]:
    """ Gets all unique account IDs, ensuring they exist in the visibility table. """
    conn = get_db_connection()
    cursor = conn.cursor()
    # This query finds all accounts in transactions and inserts any new ones
    # into the visibility table with a default of visible (1).
    cursor.execute("""
        INSERT OR IGNORE INTO account_visibility (account_id, is_visible)
        SELECT DISTINCT account_id, 1 FROM transactions WHERE account_id IS NOT NULL;
    """)
    conn.commit()
    
    cursor.execute("SELECT account_id FROM account_visibility ORDER BY account_id ASC")
    rows = cursor.fetchall()
    conn.close()
    return [row['account_id'] for row in rows]

def get_account_visibility() -> Dict[str, bool]:
    """ Returns a dictionary of all known accounts and their visibility status. """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT account_id, is_visible FROM account_visibility")
    rows = cursor.fetchall()
    conn.close()
    return {row['account_id']: bool(row['is_visible']) for row in rows}

def set_account_visibility(settings: Dict[str, bool]):
    """ Persists visibility settings for multiple accounts. """
    conn = get_db_connection()
    cursor = conn.cursor()
    data_to_upsert = [(acc, 1 if is_visible else 0) for acc, is_visible in settings.items()]
    
    try:
        cursor.executemany("""
            INSERT INTO account_visibility (account_id, is_visible) VALUES (?, ?)
            ON CONFLICT(account_id) DO UPDATE SET is_visible = excluded.is_visible;
        """, data_to_upsert)
        conn.commit()
        print(f"Updated visibility for {len(data_to_upsert)} accounts.")
    except sqlite3.Error as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

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
