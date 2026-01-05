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
        amount = float(tx['amount'])
        cashflow_type = tx.get('cashflow_type')

        if cashflow_type == 'Income' and amount > 0:
            total_income += amount
        elif cashflow_type == 'Expense' and amount < 0:
            category = tx.get('category', 'Uncategorized')
            expense_by_category[category] += abs(amount)

    total_expenses = sum(expense_by_category.values())
    net_surplus = total_income - total_expenses

    nodes = []
    links = []

    # Add nodes if they have value
    if total_income > 0:
        nodes.append({"id": "Income"})
        nodes.append({"id": "Uses of Money"})
        links.append({
            "source": "Income", 
            "target": "Uses of Money", 
            "value": round(total_income, 2)
        })

    if total_expenses > 0:
        nodes.append({"id": "Expenses"})
        links.append({
            "source": "Uses of Money", 
            "target": "Expenses", 
            "value": round(total_expenses, 2)
        })
        for category, amount in expense_by_category.items():
            if amount > 0:
                nodes.append({"id": category})
                links.append({
                    "source": "Expenses",
                    "target": category,
                    "value": round(amount, 2)
                })
    
    if net_surplus > 0:
        nodes.append({"id": "Net Surplus"})
        links.append({
            "source": "Uses of Money", 
            "target": "Net Surplus", 
            "value": round(net_surplus, 2)
        })

    # Deduplicate nodes
    unique_nodes = list({v['id']:v for v in nodes}.values())

    return {
        "nodes": unique_nodes,
        "links": links
    }
