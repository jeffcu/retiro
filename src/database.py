import sqlite3
import uuid
from pathlib import Path
from typing import List, Dict, Any, Tuple
from src.data_model import Transaction, Holding, PriceQuote # Added PriceQuote

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

    # --- NEW: Table for Price History ---
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS price_history (
        quote_id TEXT PRIMARY KEY,
        symbol TEXT NOT NULL,
        price REAL NOT NULL,
        quote_timestamp TEXT NOT NULL,
        source TEXT
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
    if 'tags' not in holdings_cols:
        print("--- MIGRATING SCHEMA: Adding 'tags' to 'holdings'. ---")
        cursor.execute("ALTER TABLE holdings ADD COLUMN tags TEXT;")
    if 'asset_type' not in holdings_cols:
        print("--- MIGRATING SCHEMA: Adding 'asset_type' to 'holdings'. ---")
        cursor.execute("ALTER TABLE holdings ADD COLUMN asset_type TEXT;")
    if 'last_price_update_failed' not in holdings_cols:
        print("--- MIGRATING SCHEMA: Adding 'last_price_update_failed' to 'holdings'. ---")
        cursor.execute("ALTER TABLE holdings ADD COLUMN last_price_update_failed INTEGER DEFAULT 0;")

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

    cursor.execute("PRAGMA foreign_keys=off;")
    cursor.execute("BEGIN TRANSACTION;")
    try:
        cursor.execute("PRAGMA table_info(rules)")
        rules_info_rows = cursor.fetchall()
        rules_cols = {row['name'] for row in rules_info_rows}
        if 'pattern' in rules_cols and any(row['name'] == 'pattern' and row['notnull'] for row in rules_info_rows):
            print("--- MIGRATING SCHEMA: Making 'pattern' column in 'rules' table nullable. ---")
            cursor.execute("ALTER TABLE rules RENAME TO _rules_old;")
            cursor.execute("""
            CREATE TABLE rules (
                rule_id TEXT PRIMARY KEY,
                pattern TEXT,
                category TEXT NOT NULL,
                cashflow_type TEXT NOT NULL,
                tags TEXT,
                priority INTEGER DEFAULT 100
            );
            """)
            cursor.execute("INSERT INTO rules (rule_id, pattern, category, cashflow_type, tags, priority) SELECT rule_id, pattern, category, cashflow_type, tags, priority FROM _rules_old;")
            cursor.execute("DROP TABLE _rules_old;")

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
    except Exception as e:
        print(f"ERROR during 'rules' table migration: {e}. Rolling back.")
        conn.rollback()
        raise e
    finally:
        cursor.execute("PRAGMA foreign_keys=on;")

    print("--- Database schema is OK. ---")
    _schema_ensured = True

def get_db_connection():
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
    cleaned_account_id = account_id.strip()
    if not cleaned_account_id:
        print("ERROR: Cannot save holdings snapshot without an account_id.")
        return 0, 0
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Fetch existing metadata for this account
    cursor.execute("SELECT symbol, tags, asset_type FROM holdings WHERE trim(lower(account_id)) = trim(lower(?))", (cleaned_account_id,))
    existing_metadata = {}
    for row in cursor.fetchall():
        existing_metadata[row['symbol']] = {
            'tags': [t.strip() for t in row['tags'].split(',')] if row['tags'] else [],
            'asset_type': row['asset_type']
        }
    
    print(f"Found existing metadata for {len(existing_metadata)} symbols in account '{cleaned_account_id}'.")

    # 2. Merge existing metadata into the new holdings list
    for h in holdings:
        if h.symbol in existing_metadata:
            meta = existing_metadata[h.symbol]
            # If the new holding from the CSV has no tags, but the old one did, preserve them.
            if not h.tags and meta['tags']:
                h.tags = meta['tags']
                print(f"Preserving tags for {h.symbol}: {h.tags}")
            # If the new holding from the CSV has no asset_type, but the old one did, preserve it.
            if not h.asset_type and meta['asset_type']:
                h.asset_type = meta['asset_type']
                print(f"Preserving asset_type for {h.symbol}: {h.asset_type}")

    deleted_count = 0
    inserted_count = 0
    try:
        # 3. Delete old records for the account
        cursor.execute("DELETE FROM holdings WHERE trim(lower(account_id)) = trim(lower(?))", (cleaned_account_id,))
        deleted_count = cursor.rowcount
        print(f"Deleted {deleted_count} stale holdings for account '{cleaned_account_id}'.")
        
        # 4. Insert the merged holdings
        if holdings:
            sql = """INSERT INTO holdings (
                        holding_id, account_id, symbol, quantity, cost_basis, market_value, tags, asset_type
                     ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);"""
            data_to_insert = [
                (
                    h.holding_id, h.account_id, h.symbol, float(h.quantity), float(h.cost_basis),
                    float(h.market_value) if h.market_value is not None else None,
                    ','.join(h.tags) if h.tags else None,
                    h.asset_type
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
        run_data['import_run_id'], run_data['file_name'], run_data['import_type'],
        run_data['import_timestamp'], run_data.get('record_count'), run_data.get('total_amount'),
        run_data.get('total_market_value'), run_data.get('total_cost_basis')
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


def _build_where_clause(filters: Dict, allowed_fields: List[str]) -> Tuple[List[str], List[Any]]:
    clauses, params = [], []
    if not filters:
        return [], []
    for key, value in filters.items():
        if key not in allowed_fields or not value:
            continue

        # --- NEW: Special handling for 'Uncategorized' filter ---
        # This aligns filtering with the display logic where NULLs are shown as "Uncategorized".
        if key == 'category' and value == 'Uncategorized':
            clauses.append("(category IS NULL OR category = '' OR category = ?)")
            params.append('Uncategorized')
        elif key in ['description', 'tags']:
            clauses.append(f"{key} LIKE ?")
            params.append(f"%{value}%")
        else:
            clauses.append(f"{key} = ?")
            params.append(value)
            
    return clauses, params

def get_transaction(transaction_id: str) -> Dict[str, Any] | None:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM transactions WHERE transaction_id = ?", (transaction_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def _apply_period_filter_to_query(where_clauses: List[str], params: List[Any], period: str | None, date_column: str, table_prefix: str = ""):
    if not period or period == 'all':
        return
    column_ref = f"{table_prefix}{date_column}" if table_prefix else date_column
    if period.isdigit() and len(period) == 4:
        where_clauses.append(f"strftime('%Y', {column_ref}) = ?")
        params.append(period)
    elif period.endswith('m'):
        months = period[:-1]
        where_clauses.append(f"{column_ref} >= date('now', '-%s months')" % months)

def get_transactions(filters: Dict[str, Any] = None, exclude_invisible: bool = False) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    filters = filters or {}
    where_clauses, params = [], []
    if exclude_invisible:
        where_clauses.append("account_id NOT IN (SELECT account_id FROM account_visibility WHERE is_visible = 0)")
    period = filters.pop('period', None)
    allowed = ['category', 'account_id', 'institution', 'description', 'tags', 'cashflow_type']
    field_clauses, field_params = _build_where_clause(filters, allowed)
    where_clauses.extend(field_clauses)
    params.extend(field_params)
    _apply_period_filter_to_query(where_clauses, params, period, date_column='transaction_date')
    query_where = " WHERE " + " AND ".join(where_clauses) if where_clauses else ""
    query = f"SELECT * FROM transactions{query_where} ORDER BY transaction_date DESC"
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_holdings(filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    filters = filters or {}
    allowed_fields, period = ['account_id', 'symbol', 'tags', 'asset_type'], filters.pop('period', None)
    clauses, params = _build_where_clause(filters, allowed_fields)
    _apply_period_filter_to_query(clauses, params, period, date_column='last_price_timestamp')
    where_str = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    query = f"SELECT * FROM holdings {where_str} ORDER BY symbol ASC"
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    results = []
    for row in rows:
        row_dict = dict(row)
        row_dict['tags'] = [tag.strip() for tag in row_dict['tags'].split(',')] if row_dict.get('tags') else []
        results.append(row_dict)
    return results

def get_holding(holding_id: str) -> Dict[str, Any] | None:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM holdings WHERE holding_id = ?", (holding_id,))
    row = cursor.fetchone()
    conn.close()
    if not row: return None
    row_dict = dict(row)
    row_dict['tags'] = [tag.strip() for tag in row_dict['tags'].split(',')] if row_dict.get('tags') else []
    return row_dict

def update_holding(holding_id: str, updates: Dict[str, Any]):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    allowed_fields = ['tags', 'asset_type']
    set_clauses = []
    params = []

    for field, value in updates.items():
        if field not in allowed_fields:
            continue

        if field == 'tags' and isinstance(value, list):
            set_clauses.append("tags = ?")
            params.append(','.join(value) if value else None)
        elif field == 'asset_type':
            set_clauses.append("asset_type = ?")
            # Ensure empty strings are saved as NULL
            params.append(value if value and str(value).strip() else None)
    
    if not set_clauses:
        print(f"Warning: No valid fields to update for holding {holding_id}.")
        return

    sql = f"UPDATE holdings SET {', '.join(set_clauses)} WHERE holding_id = ?"
    params.append(holding_id)

    try:
        cursor.execute(sql, tuple(params))
        conn.commit()
        if cursor.rowcount == 0:
            print(f"Warning: Attempted to update holding {holding_id}, but no record was found.")
    except sqlite3.Error as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def get_all_import_runs() -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM import_runs ORDER BY import_timestamp DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_filter_options() -> Dict[str, List[str]]:
    conn, options = get_db_connection(), {}
    cursor = conn.cursor()
    # Get all distinct categories, excluding 'Uncategorized' from the initial list to handle it as a special case.
    cursor.execute("SELECT DISTINCT category FROM transactions WHERE category IS NOT NULL AND category != '' AND category != 'Uncategorized' ORDER BY category")
    options['categories'] = [row['category'] for row in cursor.fetchall()]

    # --- NEW: Conditionally add 'Uncategorized' if relevant transactions exist ---
    cursor.execute("SELECT 1 FROM transactions WHERE category IS NULL OR category = '' OR category = 'Uncategorized' LIMIT 1")
    if cursor.fetchone():
        options['categories'].append('Uncategorized')
        # Re-sort to maintain alphabetical order
        options['categories'].sort()

    cursor.execute("""
        SELECT account_id FROM transactions WHERE account_id IS NOT NULL
        UNION
        SELECT account_id FROM holdings WHERE account_id IS NOT NULL
        ORDER BY account_id ASC
    """)
    options['accounts'] = [row['account_id'] for row in cursor.fetchall()]

    cursor.execute("SELECT DISTINCT institution FROM transactions WHERE institution IS NOT NULL ORDER BY institution")
    options['institutions'] = [row['institution'] for row in cursor.fetchall()]

    cursor.execute("SELECT DISTINCT asset_type FROM holdings WHERE asset_type IS NOT NULL AND asset_type != '' ORDER BY asset_type")
    options['assetTypes'] = [row['asset_type'] for row in cursor.fetchall()]

    options['cashflowTypes'] = ["Income", "Expense", "Transfer", "Capital Expenditure", "Investment"]
    conn.close()
    return options

def get_sankey_aggregates(period: str, exclude_invisible: bool = False) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    where_clauses = ["t.cashflow_type IN ('Income', 'Expense', 'Capital Expenditure')"]
    params = []
    if exclude_invisible:
        where_clauses.append("t.account_id NOT IN (SELECT account_id FROM account_visibility WHERE is_visible = 0)")
    _apply_period_filter_to_query(where_clauses, params, period, date_column='transaction_date', table_prefix='t.')
    where_sql = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""
    query = f"""SELECT cashflow_type, category, SUM(amount) as total FROM transactions t {where_sql} GROUP BY cashflow_type, category"""
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_latest_transaction_year() -> int | None:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT MAX(strftime('%Y', transaction_date)) as latest_year FROM transactions")
    result = cursor.fetchone()
    conn.close()
    return int(result['latest_year']) if result and result['latest_year'] else None

def get_cashflow_aggregation_by_month(filters: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Aggregates income and expense by month based on a flexible filter dictionary.
    This function is driven by the 'period' in the filters, not a separate year.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # Use a copy to avoid mutating the original filters dict
    local_filters = filters.copy()
    period = local_filters.pop('period', None)

    allowed_fields = ['category', 'account_id', 'institution', 'description', 'tags', 'cashflow_type']
    clauses, params = _build_where_clause(local_filters, allowed_fields)

    # The helper function correctly handles various period formats (e.g., 'all', '2024', '6m')
    _apply_period_filter_to_query(clauses, params, period, date_column='transaction_date')

    where_str = f"WHERE {' AND '.join(clauses)}" if clauses else ""

    query = f"""
        SELECT 
            strftime('%Y-%m', transaction_date) as month, 
            SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END) as income, 
            SUM(CASE WHEN amount < 0 AND cashflow_type = 'Expense' THEN amount ELSE 0 END) as expense 
        FROM transactions 
        {where_str} 
        GROUP BY month 
        ORDER BY month ASC
    """

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_holdings_aggregation_by_symbol(filters: Dict[str, Any]) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    filters = filters or {}
    allowed_fields, period = ['account_id', 'symbol', 'tags', 'asset_type'], filters.pop('period', None)
    clauses, params = _build_where_clause(filters, allowed_fields)
    _apply_period_filter_to_query(clauses, params, period, date_column='last_price_timestamp')
    where_str = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    query = f"""SELECT symbol, SUM(market_value) as total_market_value FROM holdings {where_str} GROUP BY symbol HAVING total_market_value > 0 ORDER BY total_market_value DESC LIMIT 20"""
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_holdings_aggregation_by_asset_type() -> List[Dict[str, Any]]:
    """
    Groups holdings by their asset_type and sums their market_value.
    Filters out holdings with no market value or asset type.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    query = """
        SELECT 
            asset_type, 
            SUM(market_value) as total_market_value
        FROM holdings
        WHERE 
            market_value IS NOT NULL AND market_value > 0 AND
            asset_type IS NOT NULL AND asset_type != ''
        GROUP BY asset_type
        ORDER BY total_market_value DESC;
    """
    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_total_portfolio_market_value() -> float:
    """Calculates the sum of market_value for all holdings."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT SUM(market_value) as total FROM holdings WHERE market_value IS NOT NULL AND market_value > 0")
    result = cursor.fetchone()
    conn.close()
    return result['total'] if result and result['total'] else 0.0

def _transform_rule_record(rule_row: sqlite3.Row) -> Dict[str, Any]:
    if not rule_row: return None
    rule_dict = dict(rule_row)
    rule_dict['tags'] = [t.strip() for t in rule_dict['tags'].split(',') if t.strip()] if rule_dict.get('tags') and isinstance(rule_dict['tags'], str) else []
    rule_dict['account_filter_list'] = [a.strip() for a in rule_dict['account_filter_list'].split(',') if a.strip()] if rule_dict.get('account_filter_list') and isinstance(rule_dict['account_filter_list'], str) else []
    rule_dict['case_sensitive'] = bool(rule_dict.get('case_sensitive', 0))
    return rule_dict

def create_rule(rule_data: Dict[str, Any]) -> Dict[str, Any]:
    conn = get_db_connection()
    cursor, rule_id = conn.cursor(), str(uuid.uuid4())
    sql = """INSERT INTO rules (rule_id, pattern, category, cashflow_type, tags, priority, case_sensitive, account_filter_mode, account_filter_list, condition_category, condition_institution, condition_cashflow_type, condition_tags) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);"""
    tags_str, account_list_str = ','.join(rule_data.get('tags', [])), ','.join(rule_data.get('account_filter_list', []))
    cursor.execute(sql, (rule_id, rule_data.get('pattern'), rule_data['category'], rule_data['cashflow_type'], tags_str, rule_data.get('priority', 100), 1 if rule_data.get('case_sensitive') else 0, rule_data.get('account_filter_mode', 'include'), account_list_str, rule_data.get('condition_category'), rule_data.get('condition_institution'), rule_data.get('condition_cashflow_type'), rule_data.get('condition_tags')))
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

def get_all_account_ids() -> List[str]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO account_visibility (account_id, is_visible) SELECT DISTINCT account_id, 1 FROM transactions WHERE account_id IS NOT NULL;")
    conn.commit()
    cursor.execute("SELECT account_id FROM account_visibility ORDER BY account_id ASC")
    rows = cursor.fetchall()
    conn.close()
    return [row['account_id'] for row in rows]

def get_account_visibility() -> Dict[str, bool]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT account_id, is_visible FROM account_visibility")
    rows = cursor.fetchall()
    conn.close()
    return {row['account_id']: bool(row['is_visible']) for row in rows}

def set_account_visibility(settings: Dict[str, bool]):
    conn = get_db_connection()
    cursor = conn.cursor()
    data_to_upsert = [(acc, 1 if is_visible else 0) for acc, is_visible in settings.items()]
    try:
        cursor.executemany("INSERT INTO account_visibility (account_id, is_visible) VALUES (?, ?) ON CONFLICT(account_id) DO UPDATE SET is_visible = excluded.is_visible;", data_to_upsert)
        conn.commit()
        print(f"Updated visibility for {len(data_to_upsert)} accounts.")
    except sqlite3.Error as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

SAFE_TO_PURGE = ["transactions", "holdings"]

def purge_table_data(target_table: str) -> dict:
    if target_table not in SAFE_TO_PURGE:
        raise ValueError(f"'{target_table}' is not a table that can be purged.")
    conn = get_db_connection()
    cursor, deleted_count = conn.cursor(), 0
    try:
        cursor.execute(f"SELECT COUNT(*) FROM {target_table}")
        initial_count = cursor.fetchone()[0]
        cursor.execute(f"DELETE FROM {target_table};")
        deleted_count = cursor.rowcount
        conn.commit()
        print(f"Successfully purged {deleted_count} records from '{target_table}'.")
        return {"table": target_table, "purged_records": deleted_count, "initial_records": initial_count, "status": "success"}
    except sqlite3.Error as e:
        print(f"Database error during purge of '{target_table}': {e}")
        conn.rollback()
        raise e
    finally:
        conn.close()

# --- NEW: Functions for Market Data ---

def save_price_quotes(quotes: Dict[str, Dict[str, Any]]):
    """Saves a batch of price quotes to the price_history table."""
    if not quotes:
        return
    conn = get_db_connection()
    cursor = conn.cursor()
    sql = """INSERT INTO price_history (quote_id, symbol, price, quote_timestamp, source) 
             VALUES (?, ?, ?, ?, ?);"""
    data_to_insert = [
        (
            str(uuid.uuid4()),
            symbol,
            float(data['price']),
            data['timestamp'],
            data['source']
        ) for symbol, data in quotes.items()
    ]
    try:
        cursor.executemany(sql, data_to_insert)
        conn.commit()
        print(f"Saved {cursor.rowcount} price quotes to history.")
    except (sqlite3.Error, KeyError) as e:
        print(f"Database error saving price quotes: {e}")
        conn.rollback()
        raise e
    finally:
        conn.close()

def update_holdings_with_new_prices(quotes: Dict[str, Dict[str, Any]]):
    """Updates the holdings table with the latest prices and recalculates market value."""
    if not quotes:
        return
    conn = get_db_connection()
    cursor = conn.cursor()
    updated_count = 0
    try:
        for symbol, data in quotes.items():
            price = float(data['price'])
            timestamp = data['timestamp']
            # This single query updates all holdings for a given symbol across all accounts
            cursor.execute("""
                UPDATE holdings 
                SET 
                    last_price = ?,
                    last_price_timestamp = ?,
                    market_value = quantity * ?,
                    last_price_update_failed = 0
                WHERE symbol = ?;
            """, (price, timestamp, price, symbol))
            updated_count += cursor.rowcount
        conn.commit()
        print(f"Updated {updated_count} holding records with new prices.")
    except (sqlite3.Error, KeyError) as e:
        print(f"Database error updating holdings with new prices: {e}")
        conn.rollback()
        raise e
    finally:
        conn.close()

def mark_holdings_as_failed(symbols: List[str]):
    """Sets the failure flag for a list of holding symbols."""
    if not symbols:
        return
    conn = get_db_connection()
    cursor = conn.cursor()
    # Use parameter substitution to safely handle the list of symbols
    placeholders = ', '.join('?' for _ in symbols)
    sql = f"UPDATE holdings SET last_price_update_failed = 1 WHERE symbol IN ({placeholders})"
    try:
        cursor.execute(sql, symbols)
        conn.commit()
        print(f"Marked {cursor.rowcount} holdings as failed for symbols: {symbols}")
    except sqlite3.Error as e:
        print(f"Database error marking holdings as failed: {e}")
        conn.rollback()
        raise e
    finally:
        conn.close()
