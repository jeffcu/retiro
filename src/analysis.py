"""
This module contains functions for financial calculations, generating data
for visualizations like Sankey diagrams, and running forecasts.
(PRS Sections 2, 4, 7)
"""
from typing import Dict, Any, List
from collections import defaultdict
from .database import get_all_transactions

def generate_income_sankey(period: str) -> Dict[str, Any]:
    """
    Analyzes all transactions and generates the data structure
    required for the "Income -> Uses of Money" Sankey diagram, formatted for Nivo.
    This function is designed to be robust against incomplete or corrupt data.
    (PRS Section 2.1.A)

    Args:
        period: The time period to analyze (e.g., "YTD", "month"). 
                (NOTE: Filtering by period is not yet implemented).

    Returns:
        A dictionary containing nodes and links for the Nivo Sankey component.
    """
    transactions = get_all_transactions()
    
    total_income = 0
    expense_by_category = defaultdict(float)
    
    for tx in transactions:
        try:
            # Defensively convert amount to float, handling potential data corruption.
            amount = float(tx['amount'])
            cashflow_type = tx.get('cashflow_type')

            if cashflow_type == 'Income' and amount > 0:
                total_income += amount
            elif cashflow_type == 'Expense' and amount < 0:
                # CRITICAL FIX: Ensure category is never None. If tx['category'] is None or an empty string,
                # default to 'Uncategorized'. This prevents a 'None' node in the Sankey data.
                category = tx.get('category') or 'Uncategorized'
                expense_by_category[category] += abs(amount)
        except (ValueError, TypeError) as e:
            # If a transaction has a non-numeric amount, skip it and warn.
            # This prevents the entire API endpoint from crashing.
            tx_id = tx.get('transaction_id', 'N/A')
            print(f"WARNING: Skipping transaction {tx_id} due to invalid amount: {tx.get('amount')}. Error: {e}")
            continue

    total_expenses = sum(expense_by_category.values())
    net_surplus = total_income - total_expenses

    # Step 1: Build the links conditionally based on non-zero values.
    links = []

    if total_income > 0:
        links.append({
            "source": "Income", 
            "target": "Uses of Money", 
            "value": round(total_income, 2)
        })

    if total_expenses > 0:
        links.append({
            "source": "Uses of Money", 
            "target": "Expenses", 
            "value": round(total_expenses, 2)
        })
        for category, amount in expense_by_category.items():
            if amount > 0:
                links.append({
                    "source": "Expenses",
                    "target": category,
                    "value": round(amount, 2)
                })
    
    if net_surplus > 0:
        links.append({
            "source": "Uses of Money", 
            "target": "Net Surplus", 
            "value": round(net_surplus, 2)
        })

    # If there are no links, there is no chart to draw.
    if not links:
        return {"nodes": [], "links": []}

    # Step 2: Derive the complete, unique set of nodes directly from the links.
    # This guarantees that every source and target in a link has a corresponding node.
    node_ids = set()
    for link in links:
        node_ids.add(link["source"])
        node_ids.add(link["target"])

    # Step 3: Create the node list for the API response.
    nodes = [{"id": node_id} for node_id in sorted(list(node_ids))]

    return {
        "nodes": nodes,
        "links": links
    }
