"""
This module contains functions for financial calculations, generating data
for visualizations like Sankey diagrams, and running forecasts.
(PRS Sections 2, 4, 7)
"""
from typing import Dict, Any, List
from collections import defaultdict
from . import database as db

MAX_PRIMARY_EXPENSE_CATEGORIES = 7

def _calculate_capital_flow_details(period: str, exclude_invisible: bool = False) -> Dict[str, Any]:
    """Core logic to calculate all components of the capital flow.
    Returns a structured dictionary suitable for both tables and Sankey diagrams.
    """
    aggregates = db.get_capital_flow_aggregates(period=period, exclude_invisible=exclude_invisible)
    
    # Get user settings for which income categories to show
    selected_income_categories = db.get_setting('sankey_income_categories') or []

    income_by_category = defaultdict(float)
    portfolio_yield = 0.0
    expense_by_category = defaultdict(float)

    for row in aggregates:
        source_type, category, total = row['source_type'], row['category'], row['total']
        if total is None: continue

        if source_type == 'Income':
            # Only include income if it's in the user-selected list
            if category in selected_income_categories:
                income_by_category[category] += total
        elif source_type == 'Portfolio Yield':
            portfolio_yield += total
        elif source_type == 'Expense':
            expense_by_category[category or 'Uncategorized'] += abs(total)
    
    total_op_income = sum(income_by_category.values())
    total_inflows = total_op_income + portfolio_yield
    total_consumption = sum(expense_by_category.values())
    net_savings = total_inflows - total_consumption

    # Expense breakdown logic
    sorted_expenses = sorted(expense_by_category.items(), key=lambda item: item[1], reverse=True)
    top_expenses = dict(sorted_expenses[:MAX_PRIMARY_EXPENSE_CATEGORIES])
    other_expenses_list = sorted_expenses[MAX_PRIMARY_EXPENSE_CATEGORIES:]
    other_expenses_total = sum(amount for _, amount in other_expenses_list)
    other_expenses_breakdown = dict(other_expenses_list) # All remaining expenses are included.

    return {
        "inflows_by_category": dict(income_by_category),
        "portfolio_yield": portfolio_yield,
        "total_inflows": total_inflows,
        "total_consumption": total_consumption,
        "net_savings": net_savings,
        "consumption_breakdown": {
            "top_categories": top_expenses,
            "other_total": other_expenses_total,
            "other_breakdown": other_expenses_breakdown
        }
    }

def generate_capital_flow_table_data(period: str, exclude_invisible: bool = False) -> Dict[str, Any]:
    """Generates the capital flow data specifically for the new tabular view."""
    return _calculate_capital_flow_details(period, exclude_invisible)

def generate_capital_flow_sankey(period: str, exclude_invisible: bool = False) -> Dict[str, Any]:
    """
    Uses the detailed capital flow data to generate the Sankey diagram structure.
    (PRS Section 2.1.A - REVISED v1.4)
    """
    details = _calculate_capital_flow_details(period, exclude_invisible)
    nodes, links = [], []

    if details['total_inflows'] <= 0:
        return {"nodes": [], "links": []}

    # --- FIX: Create a master set of all reserved node names up front. ---
    # This includes all structural nodes and all data-driven income sources.
    # Any data-driven expense node will be checked against this master set.
    RESERVED_NODE_IDS = {
        "Total Inflows", 
        "Consumption", 
        "Net Savings", 
        "Portfolio Yield",
        "Other Expenses" # This structural node is now explicitly reserved.
    }
    RESERVED_NODE_IDS.update(details['inflows_by_category'].keys())

    def disambiguate_expense_node(name: str) -> str:
        """If an expense category name conflicts with any reserved name, append '(Expense)'."""
        return f"{name} (Expense)" if name in RESERVED_NODE_IDS else name

    # Tier 1 & 2: Sources -> Total Inflows
    nodes.append({"id": "Total Inflows"})
    for category, amount in details['inflows_by_category'].items():
        if amount > 0:
            nodes.append({"id": category})
            links.append({"source": category, "target": "Total Inflows", "value": round(amount, 2)})
    if details['portfolio_yield'] > 0:
        nodes.append({"id": "Portfolio Yield"})
        links.append({"source": "Portfolio Yield", "target": "Total Inflows", "value": round(details['portfolio_yield'], 2)})

    # Tier 3: Primary Allocation
    nodes.extend([{"id": "Consumption"}, {"id": "Net Savings"}])
    if details['total_consumption'] > 0:
        links.append({"source": "Total Inflows", "target": "Consumption", "value": round(details['total_consumption'], 2)})
    if details['net_savings'] > 0:
        links.append({"source": "Total Inflows", "target": "Net Savings", "value": round(details['net_savings'], 2)})

    # Tier 4: Expense Breakdown
    consumption_breakdown = details['consumption_breakdown']
    for category, amount in consumption_breakdown['top_categories'].items():
        if amount > 0:
            node_id = disambiguate_expense_node(category)
            nodes.append({"id": node_id})
            links.append({"source": "Consumption", "target": node_id, "value": round(amount, 2)})
    
    if consumption_breakdown['other_total'] > 0:
        # The name for this structural node is fixed and pre-reserved.
        other_expenses_node_id = "Other Expenses"
        nodes.append({"id": other_expenses_node_id})
        links.append({"source": "Consumption", "target": other_expenses_node_id, "value": round(consumption_breakdown['other_total'], 2)})

        # Tier 5: 'Other Expenses' Sub-Breakdown
        for category, amount in consumption_breakdown['other_breakdown'].items():
            if amount > 0:
                node_id = disambiguate_expense_node(category)
                nodes.append({"id": node_id})
                links.append({"source": other_expenses_node_id, "target": node_id, "value": round(amount, 2)})

    # Finalize node list by finding all unique node IDs used.
    unique_node_ids = {node['id'] for node in nodes}
    final_nodes = [{ "id": node_id } for node_id in sorted(list(unique_node_ids))]

    return {"nodes": final_nodes, "links": links}

def prepare_cashflow_chart_data(filters: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Prepares monthly cashflow summary data for the frontend bar chart."""
    data = db.get_cashflow_aggregation_by_month(filters=filters)
    return [{"month": row['month'], "Income": row['income'], "Expense": abs(row['expense'])} for row in data]

def prepare_portfolio_chart_data(filters: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Prepares portfolio summary data for the frontend bar chart."""
    data = db.get_holdings_aggregation_by_symbol(filters=filters)
    return [{"id": row['symbol'], "value": row['total_market_value']} for row in data]

def prepare_portfolio_allocation_chart_data() -> Dict[str, Any]:
    """Creates a data structure for the portfolio allocation pie chart and table."""
    grand_total_market_value = db.get_total_portfolio_market_value()
    aggregated_by_type = db.get_holdings_aggregation_by_asset_type()

    if not aggregated_by_type or grand_total_market_value == 0:
        return {"tableData": [], "chartData": []}

    table_data, chart_data = [], []
    for row in aggregated_by_type:
        category_name, value = row['asset_type'], row['total_market_value']
        percentage = (value / grand_total_market_value) * 100
        table_data.append({"categoryName": category_name, "value": int(round(value)), "percentage": f"{percentage:.1f}%"})
        chart_data.append({"id": category_name, "label": category_name, "value": round(value, 2), "percentage": round(percentage, 1)})

    return {"tableData": table_data, "chartData": chart_data}



