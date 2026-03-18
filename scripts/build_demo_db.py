import sys
import os
import uuid
import random
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Hijack the Database Path BEFORE importing models that use it
import src.database as db
demo_dir = Path(project_root) / "demo_data"
demo_dir.mkdir(exist_ok=True)
demo_db_path = demo_dir / "trust_demo.db"

# Remove old demo db if it exists to ensure a clean slate
if demo_db_path.exists():
    os.remove(demo_db_path)

# Override the engine's target file
db.DB_FILE = demo_db_path

from src.data_model import Transaction, Holding, Property, CashflowType, FutureIncomeStream

def build_demo_dataset():
    print(f"--- Initializing Calibration Matrix at {demo_db_path} ---")
    db.initialize_database()
    
    current_year = date.today().year
    
    # 1. Base Settings (Subject is 65 years old for retirement demographic)
    print("Injecting Temporal Settings...")
    settings = {
        'forecast_birth_year': current_year - 65,
        'forecast_inflation_rate': 0.03,
        'forecast_return_rate': 0.06,
        'forecast_withdrawal_tax_rate': 0.15,
        'forecast_state_tax_rate': 0.04,
        'forecast_retirement_age': 65,
        'forecast_nogo_age': 80,
        'forecast_tax_filing_status': 'joint',
        'forecast_withdrawal_strategy': 'standard',
        'forecast_base_col_lookback_years': 1,
        'forecast_base_col_categories': ['Groceries', 'Utilities', 'Property Tax', 'Insurance', 'Dining & Entertainment', 'Healthcare', 'Hobbies', 'Travel'],
        'portfolio_inception_date': f"{current_year-2}-01-01",
        'sankey_income_categories': ['Pension', 'Social Security']
    }
    for k, v in settings.items():
        db.set_setting(k, v)

    # 2. Account Metadata
    print("Obfuscating Institutions...")
    db.set_account_metadata("Horizon Bank", "Taxable", "Primary Checking")
    db.set_account_metadata("Apex Wealth", "Taxable", "Standard Brokerage")
    db.set_account_metadata("Starlight 401k", "Deferred", "Pre-tax Retirement")
    db.set_account_metadata("Starlight Roth", "Roth", "Post-tax Retirement")

    # 3. Real Estate (Primary Residence: $1.2M Value, $200k Debt = $1M Equity)
    print("Constructing Real Estate Assets...")
    prop = Property(
        property_id=str(uuid.uuid4()),
        name="Primary Residence (Demo)",
        purchase_price=Decimal('500000'),
        mortgage_balance=Decimal('200000'),
        current_value=Decimal('1200000'),
        appreciation_rate=Decimal('0.03'),
        is_primary=True,
        annual_maintenance=Decimal('12000')
    )
    db.create_property(prop)

    # 4. Holdings ($1.5M Liquid Net Worth + Highly Appreciated Tech)
    print("Injecting Diversified Portfolio Data & Legacy Assets...")
    apex_holdings = [
        Holding(holding_id=str(uuid.uuid4()), account_id="Apex Wealth", symbol="VTI", quantity=Decimal('1500'), cost_basis=Decimal('200000'), market_value=Decimal('350000'), asset_type="Equities", tags=["Core"]),
        Holding(holding_id=str(uuid.uuid4()), account_id="Apex Wealth", symbol="VGIT", quantity=Decimal('2000'), cost_basis=Decimal('120000'), market_value=Decimal('115000'), asset_type="Government Bonds", tags=["Yield"]),
        Holding(holding_id=str(uuid.uuid4()), account_id="Apex Wealth", symbol="SGOV", quantity=Decimal('5000'), cost_basis=Decimal('500000'), market_value=Decimal('501000'), asset_type="Cash Equivalent", tags=["Liquidity"]),
        Holding(holding_id=str(uuid.uuid4()), account_id="Apex Wealth", symbol="AAPL", quantity=Decimal('2500'), cost_basis=Decimal('4500'), market_value=Decimal('450000'), asset_type="Equities", tags=["Highly Appreciated", "Tech"]),
        Holding(holding_id=str(uuid.uuid4()), account_id="Apex Wealth", symbol="AMZN", quantity=Decimal('2000'), cost_basis=Decimal('3000'), market_value=Decimal('340000'), asset_type="Equities", tags=["Highly Appreciated", "Tech"]),
        Holding(holding_id=str(uuid.uuid4()), account_id="Apex Wealth", symbol="GOOGL", quantity=Decimal('1500'), cost_basis=Decimal('5000'), market_value=Decimal('210000'), asset_type="Equities", tags=["Highly Appreciated", "Tech"])
    ]
    
    starlight_401k_holdings = [
        Holding(holding_id=str(uuid.uuid4()), account_id="Starlight 401k", symbol="FXAIX", quantity=Decimal('4000'), cost_basis=Decimal('300000'), market_value=Decimal('600000'), asset_type="Equities", tags=["Retirement"]),
        Holding(holding_id=str(uuid.uuid4()), account_id="Starlight 401k", symbol="BND", quantity=Decimal('3000'), cost_basis=Decimal('220000'), market_value=Decimal('215000'), asset_type="Fixed Income", tags=["Safety"])
    ]
    
    starlight_roth_holdings = [
        Holding(holding_id=str(uuid.uuid4()), account_id="Starlight Roth", symbol="QQQ", quantity=Decimal('400'), cost_basis=Decimal('100000'), market_value=Decimal('200000'), asset_type="Equities", tags=["Growth"])
    ]

    db.save_holdings_snapshot(apex_holdings, "Apex Wealth")
    db.save_holdings_snapshot(starlight_401k_holdings, "Starlight 401k")
    db.save_holdings_snapshot(starlight_roth_holdings, "Starlight Roth")

    # 5. Deterministic Transactions with Organic Variance
    print("Synthesizing 12 Months of Organic Cashflow...")
    transactions = []
    
    random.seed(42) # Ensure the generated data is perfectly deterministic across runs
    
    for month_offset in range(12):
        tx_date = date.today() - timedelta(days=30 * month_offset)
        
        # Income
        transactions.append(Transaction(transaction_id=str(uuid.uuid4()), account_id="Horizon Bank", transaction_date=tx_date, amount=Decimal('9000'), description="Tech Corp Pension", category="Pension", cashflow_type=CashflowType.INCOME))
        transactions.append(Transaction(transaction_id=str(uuid.uuid4()), account_id="Horizon Bank", transaction_date=tx_date, amount=Decimal('3200'), description="SSA TREAS 310 XXSOC SEC", category="Social Security", cashflow_type=CashflowType.INCOME))
        
        # Helper to generate varied amounts for organic simulation
        def var_amt(base, low=0.8, high=1.2):
            multiplier = Decimal(str(round(random.uniform(low, high), 2)))
            return (Decimal(str(base)) * multiplier).quantize(Decimal('0.01'))

        # Expenses (Varied month to month)
        transactions.append(Transaction(transaction_id=str(uuid.uuid4()), account_id="Horizon Bank", transaction_date=tx_date, amount=var_amt('-1200'), description="MegaMart", category="Groceries", cashflow_type=CashflowType.EXPENSE))
        transactions.append(Transaction(transaction_id=str(uuid.uuid4()), account_id="Horizon Bank", transaction_date=tx_date, amount=var_amt('-400', 0.9, 1.1), description="City Power & Light", category="Utilities", cashflow_type=CashflowType.EXPENSE))
        transactions.append(Transaction(transaction_id=str(uuid.uuid4()), account_id="Horizon Bank", transaction_date=tx_date, amount=var_amt('-350', 0.95, 1.05), description="Medicare Part B Premium", category="Healthcare", cashflow_type=CashflowType.EXPENSE))
        transactions.append(Transaction(transaction_id=str(uuid.uuid4()), account_id="Horizon Bank", transaction_date=tx_date, amount=var_amt('-1000', 0.9, 1.0), description="State Farm Auto/Home", category="Insurance", cashflow_type=CashflowType.EXPENSE))
        transactions.append(Transaction(transaction_id=str(uuid.uuid4()), account_id="Horizon Bank", transaction_date=tx_date, amount=var_amt('-1500', 0.6, 1.5), description="Local Restaurants & Theaters", category="Dining & Entertainment", cashflow_type=CashflowType.EXPENSE))
        transactions.append(Transaction(transaction_id=str(uuid.uuid4()), account_id="Horizon Bank", transaction_date=tx_date, amount=var_amt('-600', 0.5, 1.8), description="Pine Valley Golf Club", category="Hobbies", cashflow_type=CashflowType.EXPENSE))
        
        # Sporadic Events
        if month_offset % 4 == 0:
            transactions.append(Transaction(transaction_id=str(uuid.uuid4()), account_id="Horizon Bank", transaction_date=tx_date, amount=var_amt('-2500', 0.8, 1.5), description="Delta Airlines / Marriott", category="Travel", cashflow_type=CashflowType.EXPENSE))
            
        if month_offset == 5:
            transactions.append(Transaction(transaction_id=str(uuid.uuid4()), account_id="Horizon Bank", transaction_date=tx_date, amount=var_amt('-4500', 0.9, 1.1), description="Home Depot / Lowe's", category="Home Improvement", cashflow_type=CashflowType.CAPEX))

        if month_offset == 1:
            transactions.append(Transaction(transaction_id=str(uuid.uuid4()), account_id="Horizon Bank", transaction_date=tx_date, amount=Decimal('-12000'), description="County Tax Collector", category="Property Tax", cashflow_type=CashflowType.EXPENSE))

        # Transfers/Investments
        transactions.append(Transaction(transaction_id=str(uuid.uuid4()), account_id="Horizon Bank", transaction_date=tx_date, amount=Decimal('-2000'), description="Transfer to Apex Wealth", category="Transfer", cashflow_type=CashflowType.TRANSFER, is_transfer=True))

    db.save_transactions(transactions)

    # 6. Future Income & Discretionary Budget
    print("Configuring Runway Events...")
    db.create_future_income_stream(FutureIncomeStream(
        stream_id=str(uuid.uuid4()), stream_type="Pension", description="Spouse Pension (Age 67)", 
        start_date=date(current_year + 2, 1, 1), end_date=None, amount=Decimal('1500'), frequency="monthly", annual_increase_rate=Decimal('0.02')
    ))
    
    db.save_discretionary_budget_item({
        'name': 'Daughter\'s Wedding',
        'amount': 40000,
        'start_year': current_year + 3,
        'is_recurring': False,
        'inflation_adjusted': True,
        'category': 'Family',
        'is_enabled': True
    })
    
    db.save_discretionary_budget_item({
        'name': 'European Vacation',
        'amount': 15000,
        'start_year': current_year + 1,
        'is_recurring': False,
        'inflation_adjusted': True,
        'category': 'Travel',
        'is_enabled': True
    })

    print("\n--- Calibration Matrix Complete! ---")
    print(f"Dataset successfully forged at: {demo_db_path}")
    print("To use: Navigate to 'Data & Settings' in the UI and 'Restore' this file.")

if __name__ == "__main__":
    build_demo_dataset()
