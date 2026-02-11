import sqlite3
import uuid
import json
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
from src.data_model import Transaction, Holding, PriceQuote, FutureIncomeStream, Property
from datetime import date
from decimal import Decimal

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

    # --- NEW: Properties Table for Real Estate ---
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS properties (
        property_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        purchase_price REAL NOT NULL,
        mortgage_balance REAL NOT NULL,
        current_value REAL NOT NULL,
        appreciation_rate REAL NOT NULL,
        is_primary INTEGER DEFAULT 0
    );
    """)

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

    # --- NEW: Generic table for application settings ---
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS app_settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    );
    """)

    # --- NEW: Table for storing annual tax return data (PRS Section 7.1) ---
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tax_year_facts (
        tax_year INTEGER PRIMARY KEY,
        filing_status TEXT,
        fed_taxable_income REAL,
        fed_total_tax REAL,
        state_taxable_income REAL,
        state_total_tax REAL
    );
    """)

    # --- NEW: Table for storing future income streams for forecasting (PRS Section 7) ---
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS future_income_streams (
        stream_id TEXT PRIMARY KEY,
        stream_type TEXT NOT NULL,
        description TEXT NOT NULL,
        start_date TEXT NOT NULL,
        end_date TEXT,
        amount REAL NOT NULL,
        frequency TEXT NOT NULL, -- 'monthly' or 'annually'
        annual_increase_rate REAL DEFAULT 0.0
    );
    """)

    # --- NEW: Table for storing historical portfolio values ("Operation Snapshot") ---
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS portfolio_value_snapshots (
        snapshot_id TEXT PRIMARY KEY,
        snapshot_date TEXT NOT NULL UNIQUE,
        market_value REAL NOT NULL
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

# --- NEW: Generic settings functions ---
def get_setting(key: str) -> Any | None:
    """Fetches a setting value by key and decodes its JSON content."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM app_settings WHERE key = ?", (key,))
    row = cursor.fetchone()
    conn.close()
    if row and row['value']:
        try:
            return json.loads(row['value'])
        except json.JSONDecodeError:
            return row['value'] # Fallback for non-JSON data
    return None

def set_setting(key: str, value: Any):
    """Saves a setting value by key, encoding the value as a JSON string."""
    conn = get_db_connection()
    cursor = conn.cursor()
    json_value = json.dumps(value)
    cursor.execute("INSERT OR REPLACE INTO app_settings (key, value) VALUES (?, ?)", (key, json_value))
    conn.commit()
    conn.close()

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
    
    # --- NEW: Non-destructive import logic --- #
    # 1. Fetch existing metadata for the account before deleting.
    cursor.execute("SELECT symbol, tags, asset_type FROM holdings WHERE trim(lower(account_id)) = trim(lower(?))", (cleaned_account_id,))
    existing_metadata = {row['symbol']: {'tags': [t.strip() for t in row['tags'].split(',')] if row['tags'] else [], 'asset_type': row['asset_type']} for row in cursor.fetchall()}
    print(f"Found existing metadata for {len(existing_metadata)} symbols in account '{cleaned_account_id}'.")

    # 2. Enrich the new holdings with the existing metadata if the new data is missing it.
    for h in holdings:
        if h.symbol in existing_metadata:
            meta = existing_metadata[h.symbol]
            if not h.tags and meta['tags']:
                h.tags = meta['tags'] # Preserve old tags if new file has none
            if not h.asset_type and meta['asset_type']:
                h.asset_type = meta['asset_type'] # Preserve old asset_type

    deleted_count, inserted_count = 0, 0
    try:
        # 3. Proceed with the atomic delete-and-insert operation.
        cursor.execute("DELETE FROM holdings WHERE trim(lower(account_id)) = trim(lower(?))", (cleaned_account_id,))
        deleted_count = cursor.rowcount
        print(f"Deleted {deleted_count} stale holdings for account '{cleaned_account_id}'.")
        
        if holdings:
            sql = """INSERT INTO holdings (
                         holding_id, account_id, symbol, quantity, cost_basis, 
                         market_value, tags, asset_type
                     ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);"""
            data_to_insert = [
                (h.holding_id, h.account_id, h.symbol, float(h.quantity), float(h.cost_basis),
                 float(h.market_value) if h.market_value is not None else None, ','.join(h.tags) if h.tags else None, h.asset_type) 
                for h in holdings
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
    data_tuple = (run_data['import_run_id'], run_data['file_name'], run_data['import_type'], run_data['import_timestamp'], run_data.get('record_count'), run_data.get('total_amount'), run_data.get('total_market_value'), run_data.get('total_cost_basis'))
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
    set_clauses, params = [], []
    for field, value in updates.items():
        if field not in allowed_fields:
            continue
        if field == 'tags' and isinstance(value, list):
            set_clauses.append("tags = ?")
            params.append(','.join(value) if value else None)
        elif field == 'asset_type':
            set_clauses.append("asset_type = ?")
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

def get_income_categories() -> List[str]:
    """Gets a distinct list of all non-empty categories assigned to Income transactions."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT category FROM transactions WHERE cashflow_type = 'Income' AND category IS NOT NULL AND category != '' ORDER BY category")
    return [row['category'] for row in cursor.fetchall()]

def get_filter_options() -> Dict[str, List[str]]:
    conn, options = get_db_connection(), {}
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT category FROM transactions WHERE category IS NOT NULL AND category != '' AND category != 'Uncategorized' ORDER BY category")
    options['categories'] = [row['category'] for row in cursor.fetchall()]
    cursor.execute("SELECT 1 FROM transactions WHERE category IS NULL OR category = '' OR category = 'Uncategorized' LIMIT 1")
    if cursor.fetchone():
        options['categories'].append('Uncategorized')
        options['categories'].sort()
    cursor.execute("SELECT account_id FROM transactions WHERE account_id IS NOT NULL UNION SELECT account_id FROM holdings WHERE account_id IS NOT NULL ORDER BY account_id ASC")
    options['accounts'] = [row['account_id'] for row in cursor.fetchall()]
    cursor.execute("SELECT DISTINCT institution FROM transactions WHERE institution IS NOT NULL ORDER BY institution")
    options['institutions'] = [row['institution'] for row in cursor.fetchall()]
    cursor.execute("SELECT DISTINCT asset_type FROM holdings WHERE asset_type IS NOT NULL AND asset_type != '' ORDER BY asset_type")
    options['assetTypes'] = [row['asset_type'] for row in cursor.fetchall()]
    options['cashflowTypes'] = ["Income", "Expense", "Transfer", "Capital Expenditure", "Investment"]
    conn.close()
    return options

def get_capital_flow_aggregates(period: str, exclude_invisible: bool = False) -> List[Dict[str, Any]]:
    """ 
    Fetches all data needed for the Capital Flow Sankey in a single query.
    (PRS Section 2.1.A)
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    where_clauses, params = [], []

    if exclude_invisible:
        where_clauses.append("t.account_id NOT IN (SELECT account_id FROM account_visibility WHERE is_visible = 0)")
    
    _apply_period_filter_to_query(where_clauses, params, period, date_column='transaction_date', table_prefix='t.')
    
    where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

    # CORRECTED QUERY: Separates 'Investment Income' from other 'Income' types to prevent double-counting.
    query = f""" 
    -- Income by Category (excluding 'Investment Income', handled separately)
    SELECT 'Income' as source_type, category, SUM(amount) as total
    FROM transactions t
    WHERE {where_sql} AND t.cashflow_type = 'Income' AND (t.category IS NULL OR t.category != 'Investment Income')
    GROUP BY category

    UNION ALL

    -- Investment Income (a special type of Income, but visualized separately)
    SELECT 'Investment Income' as source_type, 'Investment Income' as category, SUM(amount) as total
    FROM transactions t
    WHERE {where_sql} AND t.cashflow_type = 'Income' AND t.category = 'Investment Income'

    UNION ALL

    -- Consumption Expenses
    SELECT 'Expense' as source_type, category, SUM(amount) as total
    FROM transactions t
    WHERE {where_sql} AND t.cashflow_type = 'Expense'
    GROUP BY category
    """
    
    # Each part of the UNION query uses the same set of WHERE clause parameters.
    # We must provide the parameter list repeated for each part.
    final_params = params * 3 
    cursor.execute(query, final_params)
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

def get_total_investment_fees_for_period(period: str) -> float:
    """
    Calculates the total advisory fees for a given period from transactions.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    where_clauses, params = [], []

    # Define the specific filters for advisory fees
    where_clauses.append("cashflow_type = 'Investment'")
    where_clauses.append("category = 'Service Charges/Fees'")

    _apply_period_filter_to_query(where_clauses, params, period, date_column='transaction_date')

    where_sql = " AND ".join(where_clauses)

    query = f"SELECT SUM(amount) as total_fees FROM transactions WHERE {where_sql}"
    
    cursor.execute(query, params)
    result = cursor.fetchone()
    conn.close()

    # Fees are typically negative amounts, so we return the absolute value.
    if result and result['total_fees'] is not None:
        return abs(float(result['total_fees']))
    return 0.0

def get_investment_income_for_period(period: str) -> float:
    """
    Calculates the total investment income (yield) for a given period.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    where_clauses, params = [], []

    # Per PRS 2.1.A, yield is income categorized as such.
    where_clauses.append("cashflow_type = 'Income'")
    where_clauses.append("category = 'Investment Income'")

    _apply_period_filter_to_query(where_clauses, params, period, date_column='transaction_date')

    where_sql = " AND ".join(where_clauses)

    query = f"SELECT SUM(amount) as total_income FROM transactions WHERE {where_sql}"
    
    cursor.execute(query, params)
    result = cursor.fetchone()
    conn.close()

    if result and result['total_income'] is not None:
        return float(result['total_income'])
    return 0.0

# --- NEW: Functions for Portfolio Waterfall ---
def get_external_contributions(period: str) -> float:
    """
    Calculates external contributions to the portfolio for a given period.
    Defined as 'Investment' type transactions that are not fees (i.e., purchases).
    These are typically negative amounts, so we return the absolute value.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    where_clauses, params = [], []
    where_clauses.append("cashflow_type = 'Investment'")
    # Exclude fees, which are also 'Investment' type but are outflows.
    where_clauses.append("category != 'Service Charges/Fees'")
    # Contributions are negative amounts (debits) in transaction logs
    where_clauses.append("amount < 0")
    _apply_period_filter_to_query(where_clauses, params, period, date_column='transaction_date')
    where_sql = " AND ".join(where_clauses)
    query = f"SELECT SUM(amount) as total_contributions FROM transactions WHERE {where_sql}"
    cursor.execute(query, params)
    result = cursor.fetchone()
    conn.close()
    return abs(float(result['total_contributions'])) if result and result['total_contributions'] is not None else 0.0

def get_withdrawals_for_spending(period: str) -> float:
    """
    Calculates withdrawals for spending, identified by the user-defined category 'Deposits'.
    These are assumed to be transfers from investment accounts to checking accounts.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    where_clauses, params = [], []
    # User specified this is their workflow for taking money out to spend.
    where_clauses.append("category = 'Deposits'")
    _apply_period_filter_to_query(where_clauses, params, period, date_column='transaction_date')
    where_sql = " AND ".join(where_clauses)
    query = f"SELECT SUM(amount) as total_withdrawals FROM transactions WHERE {where_sql}"
    cursor.execute(query, params)
    result = cursor.fetchone()
    conn.close()
    # These might be positive or negative depending on which side of the transfer is logged.
    # We take the absolute value to always represent it as an outflow.
    return abs(float(result['total_withdrawals'])) if result and result['total_withdrawals'] is not None else 0.0


def get_cashflow_aggregation_by_month(filters: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Aggregates income and expense by month based on a flexible filter dictionary."""
    conn = get_db_connection()
    cursor = conn.cursor()
    local_filters = filters.copy()
    period = local_filters.pop('period', None)
    allowed_fields = ['category', 'account_id', 'institution', 'description', 'tags', 'cashflow_type']
    clauses, params = _build_where_clause(local_filters, allowed_fields)
    _apply_period_filter_to_query(clauses, params, period, date_column='transaction_date')
    where_str = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    query = f"""SELECT 
                    strftime('%Y-%m', transaction_date) as month, 
                    SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END) as income, 
                    SUM(CASE WHEN amount < 0 AND cashflow_type = 'Expense' THEN amount ELSE 0 END) as expense 
                FROM transactions 
                {where_str} 
                GROUP BY month 
                ORDER BY month ASC"""
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
    query = f"""SELECT 
                    symbol, 
                    SUM(market_value) as total_market_value 
                FROM holdings 
                {where_str} 
                GROUP BY symbol 
                HAVING total_market_value > 0 
                ORDER BY total_market_value DESC 
                LIMIT 20"""
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_holdings_aggregation_by_asset_type() -> List[Dict[str, Any]]:
    """Groups holdings by asset_type and sums their market_value."""
    conn = get_db_connection()
    cursor = conn.cursor()
    query = """SELECT 
                    asset_type, 
                    SUM(market_value) as total_market_value 
                FROM holdings 
                WHERE market_value IS NOT NULL 
                  AND market_value > 0 
                  AND asset_type IS NOT NULL 
                  AND asset_type != '' 
                GROUP BY asset_type 
                ORDER BY total_market_value DESC;"""
    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_total_portfolio_market_value() -> float:
    """Calculates the sum of market_value for all holdings."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT SUM(market_value) as total FROM holdings WHERE market_value IS NOT NULL")
    result = cursor.fetchone()
    conn.close()
    return result['total'] if result and result['total'] else 0.0

def get_total_portfolio_cost_basis() -> float:
    """Calculates the sum of cost_basis for all holdings."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT SUM(cost_basis) as total FROM holdings WHERE cost_basis IS NOT NULL")
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
    sql = """INSERT INTO rules (
                 rule_id, pattern, category, cashflow_type, tags, priority, 
                 case_sensitive, account_filter_mode, account_filter_list, 
                 condition_category, condition_institution, condition_cashflow_type, 
                 condition_tags
             ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);"""
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

SAFE_TO_PURGE = ["transactions", "holdings", "properties"]

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

def save_price_quotes(quotes: Dict[str, Dict[str, Any]]):
    if not quotes: return
    conn = get_db_connection()
    cursor = conn.cursor()
    sql = """INSERT INTO price_history (
                 quote_id, symbol, price, quote_timestamp, source
             ) VALUES (?, ?, ?, ?, ?);"""
    data_to_insert = [(str(uuid.uuid4()), symbol, float(data['price']), data['timestamp'], data['source']) for symbol, data in quotes.items()]
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
    if not quotes: return
    conn = get_db_connection()
    cursor = conn.cursor()
    updated_count = 0
    try:
        for symbol, data in quotes.items():
            price, timestamp = float(data['price']), data['timestamp']
            cursor.execute("UPDATE holdings SET last_price = ?, last_price_timestamp = ?, market_value = quantity * ?, last_price_update_failed = 0 WHERE symbol = ?;", (price, timestamp, price, symbol))
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
    if not symbols: return
    conn = get_db_connection()
    cursor = conn.cursor()
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

# --- NEW: Functions for Tax Facts --- 
def get_tax_facts(year: int) -> Dict[str, Any] | None:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tax_year_facts WHERE tax_year = ?", (year,))
    row = cursor.fetchone()
    conn.close()
    # FIX: Use an explicit dictionary comprehension to be safer than dict(row)
    if not row:
        return None
    return {k: row[k] for k in row.keys()}

def get_latest_complete_tax_facts() -> Dict[str, Any] | None:
    """Fetches the tax facts for the most recent year that has usable data for rate calculation."""
    conn = get_db_connection()
    cursor = conn.cursor()
    # --- FIX: The query now ensures that the data is valid for calculation. ---
    cursor.execute("""SELECT * FROM tax_year_facts 
                     WHERE fed_taxable_income > 0 AND fed_total_tax > 0
                     ORDER BY tax_year DESC LIMIT 1""")
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    return {k: row[k] for k in row.keys()}

def save_tax_facts(year: int, data: Dict[str, Any]):
    conn = get_db_connection()
    cursor = conn.cursor()
    sql = """INSERT OR REPLACE INTO tax_year_facts (
                 tax_year, filing_status, fed_taxable_income, fed_total_tax, 
                 state_taxable_income, state_total_tax
             ) VALUES (?, ?, ?, ?, ?, ?);"""
    params = (
        year,
        data.get('filing_status'),
        data.get('fed_taxable_income'),
        data.get('fed_total_tax'),
        data.get('state_taxable_income'),
        data.get('state_total_tax')
    )
    try:
        cursor.execute(sql, params)
        conn.commit()
        # Note: Using print for consistency with existing codebase. Should be logging.
        print(f"Successfully saved/replaced tax facts for year {year}.")
    except sqlite3.Error as e:
        print(f"Database error saving tax facts for {year}: {e}")
        conn.rollback()
        raise e
    finally:
        conn.close()

# --- NEW: CRUD functions for Future Income Streams ---
def create_future_income_stream(stream: FutureIncomeStream) -> FutureIncomeStream:
    conn = get_db_connection()
    cursor = conn.cursor()
    sql = """INSERT INTO future_income_streams (
                 stream_id, stream_type, description, start_date, end_date, 
                 amount, frequency, annual_increase_rate
             ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);"""
    params = (
        stream.stream_id,
        stream.stream_type,
        stream.description,
        stream.start_date.isoformat(),
        stream.end_date.isoformat() if stream.end_date else None,
        float(stream.amount),
        stream.frequency,
        float(stream.annual_increase_rate)
    )
    try:
        cursor.execute(sql, params)
        conn.commit()
        print(f"Successfully created future income stream {stream.stream_id}.")
    except sqlite3.Error as e:
        print(f"Database error creating income stream: {e}")
        conn.rollback()
        raise e
    finally:
        conn.close()
    return stream

def get_all_future_income_streams() -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM future_income_streams ORDER BY start_date ASC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def delete_future_income_stream(stream_id: str) -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM future_income_streams WHERE stream_id = ?", (stream_id,))
        conn.commit()
        print(f"Deleted income stream {stream_id}. Rows affected: {cursor.rowcount}")
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Database error deleting income stream {stream_id}: {e}")
        conn.rollback()
        raise e
    finally:
        conn.close()

# --- NEW: Functions for Portfolio Value Snapshots ("Operation Snapshot") ---
def get_closest_snapshot_value_before_date(target_date: str) -> Optional[Dict[str, Any]]:
    """
    Finds the latest portfolio value snapshot on or before a given date.
    Returns the snapshot dictionary or None if no suitable snapshot is found.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    query = """
        SELECT snapshot_date, market_value 
        FROM portfolio_value_snapshots 
        WHERE snapshot_date <= ? 
        ORDER BY snapshot_date DESC 
        LIMIT 1
    """
    cursor.execute(query, (target_date,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_all_portfolio_snapshots() -> List[Dict[str, Any]]:
    """Retrieves all snapshots, ordered by date descending."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM portfolio_value_snapshots ORDER BY snapshot_date DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def create_portfolio_snapshot(snapshot_date: str, market_value: float) -> Dict[str, Any]:
    """Creates or updates a snapshot for a specific date."""
    conn = get_db_connection()
    cursor = conn.cursor()
    snapshot_id = str(uuid.uuid4())
    # Use INSERT OR REPLACE to handle unique constraint on snapshot_date
    sql = """
        INSERT INTO portfolio_value_snapshots (snapshot_id, snapshot_date, market_value)
        VALUES (?, ?, ?)
        ON CONFLICT(snapshot_date) DO UPDATE SET
            market_value = excluded.market_value;
    """
    try:
        # Find if a snapshot already exists to get its ID, otherwise use new one
        cursor.execute("SELECT snapshot_id FROM portfolio_value_snapshots WHERE snapshot_date = ?", (snapshot_date,))
        existing = cursor.fetchone()
        if existing:
            snapshot_id = existing['snapshot_id']
        
        cursor.execute(sql, (snapshot_id, snapshot_date, market_value))
        conn.commit()
    except sqlite3.Error as e:
        conn.rollback()
        raise e
    finally:
        conn.close()
    return {"snapshot_id": snapshot_id, "snapshot_date": snapshot_date, "market_value": market_value}

def delete_portfolio_snapshot(snapshot_id: str) -> bool:
    """Deletes a snapshot by its ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM portfolio_value_snapshots WHERE snapshot_id = ?", (snapshot_id,))
    deleted_count = cursor.rowcount
    conn.commit()
    conn.close()
    return deleted_count > 0

# --- NEW: CRUD Functions for Real Estate Properties ---
def get_all_properties() -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    # Sort by primary first, then by name
    cursor.execute("SELECT * FROM properties ORDER BY is_primary DESC, name ASC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def create_property(prop: Property) -> Property:
    conn = get_db_connection()
    cursor = conn.cursor()
    sql = """INSERT INTO properties (
                 property_id, name, purchase_price, mortgage_balance, 
                 current_value, appreciation_rate, is_primary
             ) VALUES (?, ?, ?, ?, ?, ?, ?);"""
    params = (
        prop.property_id,
        prop.name,
        float(prop.purchase_price),
        float(prop.mortgage_balance),
        float(prop.current_value),
        float(prop.appreciation_rate),
        1 if prop.is_primary else 0
    )
    try:
        cursor.execute(sql, params)
        conn.commit()
    except sqlite3.Error as e:
        conn.rollback()
        raise e
    finally:
        conn.close()
    return prop

def update_property(property_id: str, updates: Dict[str, Any]):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    allowed_fields = ['name', 'purchase_price', 'mortgage_balance', 'current_value', 'appreciation_rate', 'is_primary']
    set_clauses, params = [], []
    for field, value in updates.items():
        if field not in allowed_fields:
            continue
        set_clauses.append(f"{field} = ?")
        params.append(value)
    
    if not set_clauses:
        return

    sql = f"UPDATE properties SET {', '.join(set_clauses)} WHERE property_id = ?"
    params.append(property_id)
    try:
        cursor.execute(sql, tuple(params))
        conn.commit()
    except sqlite3.Error as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def delete_property(property_id: str) -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM properties WHERE property_id = ?", (property_id,))
    deleted_count = cursor.rowcount
    conn.commit()
    conn.close()
    return deleted_count > 0

def get_total_real_estate_equity() -> float:
    """Calculates sum(current_value) - sum(mortgage_balance) for all properties."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT SUM(current_value) as total_val, SUM(mortgage_balance) as total_debt FROM properties")
    row = cursor.fetchone()
    conn.close()
    if row:
        val = row['total_val'] or 0.0
        debt = row['total_debt'] or 0.0
        return val - debt
    return 0.0
