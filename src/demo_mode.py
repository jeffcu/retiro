from typing import List, Dict, Any
from decimal import Decimal

# Portfolio assets are divided by 4 (25% of value shown)
PORTFOLIO_DIVISOR = Decimal('4.0')

# Real Estate assets are divided by 2 (50% of value shown)
REAL_ESTATE_DIVISOR = Decimal('2.0')

def _apply_demo_to_holding(holding: Dict[str, Any]) -> Dict[str, Any]:
    """Applies demo mode transformation to a single holding dictionary (Portfolio)."""
    if not isinstance(holding, dict):
        return holding
    
    demo_holding = holding.copy()
    
    # These fields represent real values that should be scaled by the PORTFOLIO divisor.
    fields_to_scale = ['quantity', 'cost_basis', 'market_value', 'total_market_value', 'value']
    
    for field in fields_to_scale:
        if field in demo_holding and demo_holding[field] is not None:
            try:
                original_value = Decimal(str(demo_holding[field]))
                demo_holding[field] = float(original_value / PORTFOLIO_DIVISOR)
            except (TypeError, ValueError):
                pass
                
    return demo_holding

def _apply_demo_to_property(prop: Dict[str, Any]) -> Dict[str, Any]:
    """Applies demo mode transformation to a single property dictionary (Real Estate)."""
    if not isinstance(prop, dict):
        return prop
    
    demo_prop = prop.copy()

    # These fields represent real estate values to be scaled by the REAL ESTATE divisor.
    fields_to_scale = ['purchase_price', 'mortgage_balance', 'current_value', 'equity']

    for field in fields_to_scale:
        if field in demo_prop and demo_prop[field] is not None:
            try:
                original_value = Decimal(str(demo_prop[field]))
                demo_prop[field] = float(original_value / REAL_ESTATE_DIVISOR)
            except (TypeError, ValueError):
                pass
    
    return demo_prop

def process_for_demo_mode(data: Any) -> Any:
    """
    Recursively processes a data structure to apply demo mode transformations.
    Intelligently detects if data is Real Estate, Portfolio, or Forecast Simulation based on keys.
    """
    if isinstance(data, list):
        if not data:
            return data
        
        # Peek at the first item to determine the type of list
        first_item = data[0]
        if isinstance(first_item, dict):
            if 'mortgage_balance' in first_item or 'purchase_price' in first_item:
                # It's a list of Properties
                return [_apply_demo_to_property(item) for item in data]
            else:
                # Assume it's a list of Holdings
                return [_apply_demo_to_holding(item) for item in data]
        
        return data
    
    if isinstance(data, dict):
        # Handle specific, known data structures
        
        # 1. Forecast Simulation Result (Wrapper)
        if 'simulation_series' in data:
            demo_data = data.copy()
            demo_data['simulation_series'] = [
                process_for_demo_mode(year_data) for year_data in data['simulation_series']
            ]
            if 'settings' in demo_data:
                 # Obscure the starting points summary
                 s = demo_data['settings']
                 if 'starting_nw' in s:
                      s['starting_nw'] = s['starting_nw'] / float(PORTFOLIO_DIVISOR)
                 if 'starting_base_col' in s:
                      s['starting_base_col'] = s['starting_base_col'] / float(PORTFOLIO_DIVISOR)
            return demo_data

        # 2. Forecast Year Data (Simulation Row)
        # We scale assets/expenses/income to obscure magnitude.
        if 'liquid_assets' in data and 'total_net_worth' in data:
            demo_row = data.copy()
            
            # Scale Portfolio-like items
            port_keys = ['liquid_assets', 'bucket_taxable', 'bucket_deferred', 'bucket_roth', 
                         'total_income', 'total_expenses', 'base_col_expense', 'discretionary_expense',
                         'net_cashflow', 'investment_growth', 'rmd_event']
            
            for k in port_keys:
                if k in demo_row:
                     demo_row[k] = demo_row[k] / float(PORTFOLIO_DIVISOR)
            
            # Scale Real Estate Items
            if 'real_estate_equity' in demo_row:
                 demo_row['real_estate_equity'] = demo_row['real_estate_equity'] / float(REAL_ESTATE_DIVISOR)

            # Re-sum Net Worth because components were scaled differently
            # Note: This changes the math slightly, but visual trend remains roughly similar for demo purposes.
            demo_row['total_net_worth'] = demo_row['liquid_assets'] + demo_row['real_estate_equity']
            
            # Scale the detailed breakdown map
            if 'expense_breakdown' in demo_row and isinstance(demo_row['expense_breakdown'], dict):
                 demo_row['expense_breakdown'] = {
                      k: v / float(PORTFOLIO_DIVISOR) for k, v in demo_row['expense_breakdown'].items()
                 }
            
            return demo_row

        # 3. Portfolio Allocation (Pie Chart & Table)
        # This is purely portfolio data, use standard divisor.
        if all(k in data for k in ['chartData', 'tableData']):
            demo_data = data.copy()
            demo_data['chartData'] = [
                {**item, 'value': float(Decimal(str(item['value'])) / PORTFOLIO_DIVISOR)}
                for item in data['chartData']
            ]
            demo_data['tableData'] = [
                {**item, 'value': int(Decimal(str(item['value'])) / PORTFOLIO_DIVISOR)}
                for item in data['tableData']
            ]
            return demo_data

        # 4. Portfolio Summary / Overall Return (Mix of Liquid and Real Estate)
        # This requires applying DIFFERENT divisors to different keys and re-summing.
        if 'total_real_estate_equity' in data or 'total_market_value' in data:
            demo_data = data.copy()
            
            # Scale Liquid Portfolio
            if 'total_market_value' in demo_data:
                val = Decimal(str(demo_data['total_market_value']))
                demo_data['total_market_value'] = float(val / PORTFOLIO_DIVISOR)

            # Scale Cost Basis (Portfolio)
            if 'total_cost_basis' in demo_data:
                val = Decimal(str(demo_data['total_cost_basis']))
                demo_data['total_cost_basis'] = float(val / PORTFOLIO_DIVISOR)

            # Scale Gains (Portfolio)
            if 'total_gain_dollars' in demo_data:
                val = Decimal(str(demo_data['total_gain_dollars']))
                demo_data['total_gain_dollars'] = float(val / PORTFOLIO_DIVISOR)
            
            # Scale Real Estate
            if 'total_real_estate_equity' in demo_data:
                val = Decimal(str(demo_data['total_real_estate_equity']))
                demo_data['total_real_estate_equity'] = float(val / REAL_ESTATE_DIVISOR)
            
            # Recalculate Total Net Worth if present (Sum of scaled parts)
            if 'total_net_worth' in demo_data:
                tmv = Decimal(str(demo_data.get('total_market_value', 0)))
                tre = Decimal(str(demo_data.get('total_real_estate_equity', 0)))
                demo_data['total_net_worth'] = float(tmv + tre)

            demo_data['notes'] = "DEMO MODE: Values reduced (Portfolio 25%, Real Estate 50%)."
            return demo_data

        # Fallback for generic dictionaries
        return {key: process_for_demo_mode(value) for key, value in data.items()}

    return data
