from datetime import date
from decimal import Decimal
from typing import List, Dict, Any, Optional
from . import database as db

def calculate_forecast() -> Dict[str, Any]:
    """
    The Time Machine Simulation Engine.
    Projects Net Worth year-over-year from the current year until Age 95.
    """
    
    # 1. Gather Simulation Inputs
    birth_year = db.get_setting('forecast_birth_year')
    inflation_rate = float(db.get_setting('forecast_inflation_rate') or 0.03)
    return_rate = float(db.get_setting('forecast_return_rate') or 0.05)
    
    # Selected categories for Base CoL (e.g., ["Groceries", "Utilities"])
    base_col_categories = db.get_setting('forecast_base_col_categories') or []
    
    # 2. Establish Starting State
    current_year = date.today().year
    
    # Current Net Worth Components
    liquid_assets = db.get_total_portfolio_market_value()
    properties = db.get_all_properties()
    real_estate_equity = db.get_total_real_estate_equity()
    
    # Calculate Base Cost of Living from Actuals (Last 12 Months)
    base_col_annual = db.get_base_col_from_actuals(base_col_categories)
    
    discretionary_items = db.get_discretionary_budget_items()
    future_income_streams = db.get_all_future_income_streams()
    
    if not birth_year:
        return {"error": "Birth Year not set. Please configure settings."}
    
    end_year = birth_year + 95
    
    # 3. The Simulation Loop
    simulation_data = []
    
    # Working variables for the loop
    current_liquid = liquid_assets
    
    # We track property values individually to apply specific appreciation rates
    # Structure: { property_id: current_value }
    # Mortgage balance is assumed constant for now (conservative) or we could amortize.
    # For v1.7, let's keep debt constant (interest only assumption) or just track equity growth via asset growth.
    working_properties = [
        {
            "id": p['property_id'], 
            "value": p['current_value'], 
            "debt": p['mortgage_balance'],
            "rate": p['appreciation_rate']
        } 
        for p in properties
    ]

    for year in range(current_year, end_year + 1):
        age = year - birth_year
        
        # A. Calculate Income for this Year
        year_income = 0.0
        for stream in future_income_streams:
            start = date.fromisoformat(stream['start_date'])
            end = date.fromisoformat(stream['end_date']) if stream['end_date'] else None
            
            # Check if active this year
            if start.year <= year and (end is None or end.year >= year):
                amount = stream['amount']
                # Adjust for frequency
                annual_amount = amount * 12 if stream['frequency'] == 'monthly' else amount
                
                # Apply COLA / Increase Rate
                # Formula: Base * (1 + rate) ^ (year - start_year)
                years_active = year - start.year
                increase_rate = stream['annual_increase_rate']
                adjusted_amount = annual_amount * ((1 + increase_rate) ** years_active)
                
                year_income += adjusted_amount

        # B. Calculate Expenses for this Year
        
        # Base CoL (Inflated)
        # Formula: Base * (1 + inflation) ^ (year - current_year)
        years_from_start = year - current_year
        year_base_col = base_col_annual * ((1 + inflation_rate) ** years_from_start)
        
        # Discretionary Items
        year_discretionary = 0.0
        for item in discretionary_items:
            # Check if active
            item_start = item['start_year']
            item_end = item['end_year'] if item['end_year'] else (9999 if item['is_recurring'] else item_start)
            
            if item_start <= year <= item_end:
                item_amount = item['amount']
                if item['inflation_adjusted']:
                    # Inflate from the Item's Start Year, not current year, or just generic inflation?
                    # Usually budgeting implies "In Today's Dollars". Let's inflate from current_year.
                    item_amount = item_amount * ((1 + inflation_rate) ** years_from_start)
                year_discretionary += item_amount

        total_expenses = year_base_col + year_discretionary

        # C. Calculate Net Portfolio Growth/Drawdown
        # 1. Grow the liquid pile (Pre-drawdown or Post? Usually start of year balance grows, then cashflow happens)
        # Let's do: (Balance * Growth) + Income - Expenses
        investment_growth = current_liquid * return_rate
        
        net_cashflow = year_income - total_expenses
        
        # Update Liquid Assets
        # If net_cashflow is negative, we burn principal. If positive, we save.
        current_liquid += (investment_growth + net_cashflow)

        # D. Grow Real Estate
        year_re_value = 0.0
        year_re_debt = 0.0
        for prop in working_properties:
            # Appreciate value
            prop['value'] = prop['value'] * (1 + prop['rate'])
            year_re_value += prop['value']
            year_re_debt += prop['debt']

        total_net_worth = current_liquid + (year_re_value - year_re_debt)

        # E. Record Simulation Step
        simulation_data.append({
            "year": year,
            "age": age,
            "liquid_assets": round(current_liquid, 2),
            "real_estate_equity": round(year_re_value - year_re_debt, 2),
            "total_net_worth": round(total_net_worth, 2),
            "total_income": round(year_income, 2),
            "total_expenses": round(total_expenses, 2),
            "base_col_expense": round(year_base_col, 2),
            "discretionary_expense": round(year_discretionary, 2),
            "net_cashflow": round(net_cashflow, 2),
            "investment_growth": round(investment_growth, 2)
        })
        
    return {
        "simulation_series": simulation_data,
        "settings": {
            "birth_year": birth_year,
            "inflation_rate": inflation_rate,
            "return_rate": return_rate,
            "starting_nw": liquid_assets + real_estate_equity,
            "starting_base_col": base_col_annual
        }
    }
