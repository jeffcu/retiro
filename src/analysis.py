"""
This module contains functions for financial calculations, generating data
for visualizations like Sankey diagrams, and running forecasts.
(PRS Sections 2, 4, 7)
"""
from typing import Dict, Any, List
from collections import defaultdict
from datetime import datetime
from .database import get_transactions, get_holdings_aggregation_by_symbol, get_cashflow_aggregation_by_month, get_latest_transaction_year

def generate_income_sankey(period: str, exclude_invisible: bool = False) -> Dict[str, Any]:
    """
    Analyzes transactions to generate data for a simple Sankey diagram.
    This version creates a flat structure: Income -> [Expense Categories].
    (PRS Section 2.1.A)

    Args:
        period: The time period to analyze (NOTE: Not yet implemented).
        exclude_invisible: If True, filters out transactions from accounts
                           marked as not visible.

    Returns:
        A dictionary formatted for the Nivo Sankey component.
    """
    # UPDATED: Call the new filterable get_transactions function with no filters.
    transactions = get_transactions(exclude_invisible=exclude_invisible)
    
    total_income = 0.0
    expense_by_category = defaultdict(float)
    total_capex = 0.0
    
    for tx in transactions:
        try:
            amount = float(tx['amount'])
            cashflow_type = tx.get('cashflow_type')

            if cashflow_type == 'Income' and amount > 0:
                total_income += amount
            elif cashflow_type == 'Expense' and amount < 0:
                # Use the assigned category, or 'Uncategorized' if none exists
                category = tx.get('category') or 'Uncategorized'
                expense_by_category[category] += abs(amount)
            elif cashflow_type == 'Capital Expenditure' and amount < 0:
                total_capex += abs(amount)

        except (ValueError, TypeError) as e:
            tx_id = tx.get('transaction_id', 'N/A')
            # In a real application, this should be structured logging.
            print(f"WARNING: Skipping transaction {tx_id} due to invalid amount: {tx.get('amount')}. Error: {e}")
            continue

    total_expenses = sum(expense_by_category.values())
    net_surplus = total_income - total_expenses - total_capex

    nodes = [{"id": "Income"}]
    links = []

    # Add expense categories as nodes and create links from Income
    for category, amount in expense_by_category.items():
        if amount > 0:
            nodes.append({"id": category})
            links.append({"source": "Income", "target": category, "value": round(amount, 2)})

    # Handle Capital Expenditure
    if total_capex > 0:
        nodes.append({"id": "Capital Expenditure"})
        links.append({"source": "Income", "target": "Capital Expenditure", "value": round(total_capex, 2)})
    
    # Handle Net Surplus
    if net_surplus > 0:
        nodes.append({"id": "Net Surplus"})
        links.append({"source": "Income", "target": "Net Surplus", "value": round(net_surplus, 2)})

    # Deduplicate nodes just in case, though the build-up logic should prevent it.
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

