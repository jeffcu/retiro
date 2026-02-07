from typing import List, Dict, Any
from decimal import Decimal

DEMO_DIVISOR = Decimal('4.0')

def _apply_demo_to_holding(holding: Dict[str, Any]) -> Dict[str, Any]:
    """Applies demo mode transformation to a single holding dictionary."""
    if not isinstance(holding, dict):
        return holding
    
    demo_holding = holding.copy()
    
    # These fields represent real values that should be scaled.
    fields_to_scale = ['quantity', 'cost_basis', 'market_value', 'total_market_value', 'value']
    
    for field in fields_to_scale:
        if field in demo_holding and demo_holding[field] is not None:
            try:
                original_value = Decimal(str(demo_holding[field]))
                demo_holding[field] = original_value / DEMO_DIVISOR
            except (TypeError, ValueError):
                # Ignore fields that are not numeric
                pass
                
    return demo_holding

def process_for_demo_mode(data: Any) -> Any:
    """
    Recursively processes a data structure to apply demo mode transformations.
    This is designed to handle various response types from the API.
    """
    if isinstance(data, list):
        return [_apply_demo_to_holding(item) for item in data]
    
    if isinstance(data, dict):
        # Handle specific, known data structures first
        
        # Structure from `calculate_portfolio_summary_metrics`
        if all(k in data for k in ['total_market_value', 'total_cost_basis', 'total_gain_dollars']):
            demo_data = data.copy()
            demo_data['total_market_value'] /= float(DEMO_DIVISOR)
            demo_data['total_cost_basis'] /= float(DEMO_DIVISOR)
            demo_data['total_gain_dollars'] /= float(DEMO_DIVISOR)
            # Percentage gain remains the same, as it's a ratio.
            demo_data['notes'] = "DEMO MODE: All values are divided by 4."
            return demo_data
            
        # Structure from `prepare_portfolio_allocation_chart_data`
        if all(k in data for k in ['chartData', 'tableData']):
            demo_data = data.copy()
            demo_data['chartData'] = [
                {**item, 'value': item['value'] / float(DEMO_DIVISOR)}
                for item in data['chartData']
            ]
            demo_data['tableData'] = [
                {**item, 'value': int(item['value'] / float(DEMO_DIVISOR))}
                for item in data['tableData']
            ]
            # Percentages remain the same.
            return demo_data
            
        # Structure from `portfolio/summary`
        if 'total_market_value' in data and len(data.keys()) == 1:
            demo_data = data.copy()
            demo_data['total_market_value'] /= float(DEMO_DIVISOR)
            return demo_data

        # Fallback for generic dictionaries (though less likely to be used)
        return {key: process_for_demo_mode(value) for key, value in data.items()}

    return data
