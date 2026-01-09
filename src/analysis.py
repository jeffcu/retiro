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
    This version ensures the diagram is always balanced by using an intermediate
    node and explicitly showing deficits.
    (PRS Section 2.1.A, 3.1)

    Args:
        period: The time period to analyze (e.g., 'all', '2024', '6m').
        exclude_invisible: If True, filters out transactions from accounts
                           marked as not visible.

    Returns:
        A dictionary formatted for the Nivo Sankey component.
    """
    aggregates = get_sankey_aggregates(period=period, exclude_invisible=exclude_invisible)
    
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

    nodes = []
    links = []

    # --- NEW: Balanced and Sorted Sankey Architecture --- #

    # 0. Define reserved names to prevent topological loops.
    RESERVED_NODE_NAMES = {
        "Income", "Available Funds", "Net Surplus", 
        "Net Deficit", "Capital Expenditure", "Other Expenses"
    }

    # 1. Define core source and intermediate distribution nodes.
    if total_income > 0:
        nodes.append({"id": "Income"})
    
    nodes.append({"id": "Available Funds"})

    # 2. Handle deficit vs. surplus to establish balanced inflows.
    if net_surplus >= 0:
        if total_income > 0:
            links.append({"source": "Income", "target": "Available Funds", "value": round(total_income, 2)})
    else:
        net_deficit = abs(net_surplus)
        nodes.append({"id": "Net Deficit"})
        if total_income > 0:
            links.append({"source": "Income", "target": "Available Funds", "value": round(total_income, 2)})
        links.append({"source": "Net Deficit", "target": "Available Funds", "value": round(net_deficit, 2)})

    # 3. Sanitize expense category names to prevent collisions.
    sanitized_expenses = defaultdict(float)
    for category, amount in expense_by_category.items():
        safe_name = f"{category} (Expense)" if category in RESERVED_NODE_NAMES else category
        sanitized_expenses[safe_name] += amount

    # 4. Assemble and sort all outflows from "Available Funds".
    outflows = []
    if net_surplus > 0:
        outflows.append(("Net Surplus", net_surplus))
    if total_capex > 0:
        outflows.append(("Capital Expenditure", total_capex))

    # Use top N expense categories and group the rest into "Other Expenses".
    MAX_EXPENSE_CATEGORIES = 6 
    sorted_expenses = sorted(sanitized_expenses.items(), key=lambda item: item[1], reverse=True)
    
    top_expenses_list = sorted_expenses[:MAX_EXPENSE_CATEGORIES]
    other_expenses_list = sorted_expenses[MAX_EXPENSE_CATEGORIES:]
    other_expenses_total = sum(amount for _, amount in other_expenses_list)

    outflows.extend(top_expenses_list)

    if other_expenses_total > 0:
        outflows.append(("Other Expenses", other_expenses_total))

    # Sort the master list of outflows by value, descending.
    outflows.sort(key=lambda item: item[1], reverse=True)

    # 5. Create nodes and links from the sorted outflows.
    for target_node, amount in outflows:
        if amount > 0:
            nodes.append({"id": target_node})
            links.append({"source": "Available Funds", "target": target_node, "value": round(amount, 2)})

    # 6. Handle the sub-tier breakout for "Other Expenses", also sorted.
    if other_expenses_total > 0:
        other_expenses_list.sort(key=lambda item: item[1], reverse=True)
        for category, amount in other_expenses_list:
            if amount > 0:
                nodes.append({"id": category})
                links.append({"source": "Other Expenses", "target": category, "value": round(amount, 2)})

    # 7. Finalize node list, ensuring no duplicates.
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


