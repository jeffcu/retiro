"""
This module contains functions for financial calculations, generating data
for visualizations like Sankey diagrams, and running forecasts.
(PRS Sections 2, 4, 7)
"""
from typing import Dict, Any, List
from collections import defaultdict
from datetime import datetime
from .database import get_sankey_aggregates, get_holdings_aggregation_by_symbol, get_cashflow_aggregation_by_month, get_latest_transaction_year

def generate_income_sankey(period: str, exclude_invisible: bool = False) -> Dict[str, Any]:
    """
    Analyzes transaction aggregates to generate data for the income Sankey diagram.
    This version uses a direct database aggregation for efficiency and accuracy,
    ensuring only operational cashflow is included.
    (PRS Section 2.1.A, 3.1)

    Args:
        period: The time period to analyze (NOTE: Not yet implemented).
        exclude_invisible: If True, filters out transactions from accounts
                           marked as not visible.

    Returns:
        A dictionary formatted for the Nivo Sankey component.
    """
    aggregates = get_sankey_aggregates(exclude_invisible=exclude_invisible)
    
    total_income = 0.0
    expense_by_category = defaultdict(float)
    total_capex = 0.0
    
    for row in aggregates:
        cashflow_type = row.get('cashflow_type')
        total = row.get('total', 0.0)

        if cashflow_type == 'Income' and total > 0:
            total_income += total
        elif cashflow_type == 'Expense' and total < 0:
            category = row.get('category') or 'Uncategorized'
            expense_by_category[category] += abs(total)
        elif cashflow_type == 'Capital Expenditure' and total < 0:
            total_capex += abs(total)

    total_expenses = sum(expense_by_category.values())
    net_surplus = total_income - total_expenses - total_capex

    nodes = [{"id": "Income"}]
    links = []

    # --- NEW: Aggregation Logic (PRS 2.1.A, 2.2) ---
    # Sort expenses and group smaller ones into "Other Expenses"
    MAX_EXPENSE_CATEGORIES = 7 # Keep top 7 expense categories + "Other"
    sorted_expenses = sorted(expense_by_category.items(), key=lambda item: item[1], reverse=True)
    
    top_expenses = dict(sorted_expenses[:MAX_EXPENSE_CATEGORIES])
    other_expenses = dict(sorted_expenses[MAX_EXPENSE_CATEGORIES:])
    other_expenses_total = sum(other_expenses.values())

    # Add top expense categories as nodes and create links
    for category, amount in top_expenses.items():
        if amount > 0:
            nodes.append({"id": category})
            links.append({"source": "Income", "target": category, "value": round(amount, 2)})

    # Add the aggregated "Other Expenses" node if it has value
    if other_expenses_total > 0:
        nodes.append({"id": "Other Expenses"})
        links.append({"source": "Income", "target": "Other Expenses", "value": round(other_expenses_total, 2)})

    # Handle Capital Expenditure
    if total_capex > 0:
        nodes.append({"id": "Capital Expenditure"})
        links.append({"source": "Income", "target": "Capital Expenditure", "value": round(total_capex, 2)})
    
    # Handle Net Surplus
    if net_surplus > 0:
        nodes.append({"id": "Net Surplus"})
        links.append({"source": "Income", "target": "Net Surplus", "value": round(net_surplus, 2)})

    # Deduplicate nodes just in case.
    unique_node_ids = {node['id'] for node in nodes}
    final_nodes = [{"id": node_id} for node_id in sorted(list(unique_node_ids))]

    if not links:
        return {"nodes": [], "links": []}

    return {
        "nodes": final_nodes,
        "links": links
    }


def prepare_cashflow_chart_data(filters: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Prepares monthly cashflow summary data for the frontend bar chart.
    """
    # Dynamically determine the year to display.
    year_to_use = get_latest_transaction_year()
    if not year_to_use:
        year_to_use = datetime.now().year

    data = get_cashflow_aggregation_by_month(year=year_to_use, filters=filters)

    # The data comes in as a list of {'month', 'income', 'expense'}.
    # We'll format it for Nivo.
    return [
        {
            "month": f"{year_to_use}-{row['month']:02d}",
            "Income": row['income'],
            "Expense": abs(row['expense']) # Make expense positive for bar chart
        }
        for row in data
    ]

def prepare_portfolio_chart_data(filters: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Prepares portfolio summary data for the frontend bar chart.
    """
    # Aggregate market value by symbol based on filters.
    data = get_holdings_aggregation_by_symbol(filters=filters)

    # Format for Nivo bar chart: [{id: 'symbol', value: 12345}, ...]
    return [
        {
            "id": row['symbol'],
            "value": row['total_market_value']
        }
        for row in data
    ]
