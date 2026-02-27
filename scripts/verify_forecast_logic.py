import sys
import os
from datetime import date

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock the database module to isolate the engine logic
class MockDB:
    def __init__(self):
        self.settings = {
            'forecast_birth_year': 1960,  # Age 66 in 2026
            'forecast_inflation_rate': 0.03,
            'forecast_return_rate': 0.05,
            'forecast_withdrawal_strategy': 'deferred_first', # TEST TARGET
            'forecast_withdrawal_tax_rate': 0.15,
            'forecast_base_col_lookback_years': 1,
            'forecast_base_col_categories': []
        }
    
    def get_setting(self, key):
        return self.settings.get(key)

    def get_discretionary_budget_items(self):
        return []

    def get_all_future_income_streams(self):
        return []

    def get_account_metadata(self):
        return {}

    def get_holdings(self):
        # SCENARIO: We have money in both buckets
        return [
            {'account_id': 'brokerage', 'market_value': 100000, 'symbol': 'VTSAX'},
            {'account_id': 'ira', 'market_value': 100000, 'symbol': 'VTIAX'}
        ]

    def get_all_properties(self):
        return []
    
    def get_base_col_breakdown(self, cats, lookback):
        return {'Groceries': 50000.0} # $50k annual expense

# Monkey patch the database module in src.forecast
import src.forecast
src.forecast.db = MockDB()

def run_verification():
    print("--- Running Forecast Logic Verification ---")
    print(f"Test Settings: Birth Year={src.forecast.db.settings['forecast_birth_year']}")
    print(f"Test Settings: Strategy={src.forecast.db.settings['forecast_withdrawal_strategy']}")
    
    # Run Simulation
    result = src.forecast.calculate_forecast()
    series = result['simulation_series']
    
    # Check Year 1 (2026, Age 66)
    year_1 = series[0]
    print(f"\n[Year {year_1['year']} | Age {year_1['age']}]")
    print(f"Income: ${year_1['total_income']}")
    print(f"Expenses: ${year_1['total_expenses']}")
    print(f"Net Cashflow: ${year_1['net_cashflow']}")
    print(f"Strategy Executed: {year_1['strategy_executed']}")
    
    # Verification Logic
    if year_1['strategy_executed'] == "Deferred First":
        print("\n✅ SUCCESS: Engine correctly applied 'Deferred First' strategy.")
    else:
        print(f"\n❌ FAILURE: Engine applied '{year_1['strategy_executed']}' instead of 'Deferred First'.")

if __name__ == "__main__":
    run_verification()