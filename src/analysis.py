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
    investment_income = 0.0
    expense_by_category = defaultdict(float)

    for row in aggregates:
        source_type, category, total = row['source_type'], row['category'], row['total']
        if total is None: continue

        if source_type == 'Income':
            # Only include income if it's in the user-selected list
            if category in selected_income_categories:
                income_by_category[category] += total
        elif source_type == 'Investment Income':
            investment_income += total
        elif source_type == 'Expense':
            expense_by_category[category or 'Uncategorized'] += abs(total)
    
    total_op_income = sum(income_by_category.values())
    total_inflows = total_op_income + investment_income
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
        "investment_income": investment_income,
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
        "Investment Income",
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
    if details['investment_income'] > 0:
        nodes.append({"id": "Investment Income"})
        links.append({"source": "Investment Income", "target": "Total Inflows", "value": round(details['investment_income'], 2)})

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

def calculate_investment_cashflow_summary(period: str) -> Dict[str, Any]:
    """
    Calculates a summary of cashflows from portfolio activities.
    """
    # Step 1: Get cash inflows from investments
    investment_income = db.get_investment_income_for_period(period)

    # Step 2: Get cash outflows for fees
    fees = db.get_total_investment_fees_for_period(period)

    # Step 3: Calculate estimated taxes on the income with intelligent fallback
    notes = [f"Using data for period '{period}'."]
    taxes = 0
    tax_facts = None

    # Determine the primary year to check based on the period
    primary_year_to_check = None
    if period.isdigit() and len(period) == 4:
        primary_year_to_check = int(period)
    else:
        primary_year_to_check = db.get_latest_transaction_year() # e.g., for 'all' or '6m'

    if primary_year_to_check:
        # Attempt to get tax facts for the primary year
        tax_facts = db.get_tax_facts(primary_year_to_check)
        
        # Check if primary year's facts are usable for calculation
        if tax_facts and tax_facts.get('fed_taxable_income') and tax_facts.get('fed_total_tax'):
            notes.append(f"Taxes estimated based on {primary_year_to_check} tax data.")
        else:
            # If not usable, find the latest complete historical data as a fallback
            historical_tax_facts = db.get_latest_complete_tax_facts()
            if historical_tax_facts:
                tax_facts = historical_tax_facts
                tax_year_used = tax_facts['tax_year']
                notes.append(f"Tax facts for {primary_year_to_check} are incomplete; using data from {tax_year_used} as an estimate.")
            else:
                notes.append("No complete tax data available in the system; taxes cannot be calculated.")
                tax_facts = None # Ensure it's None for the next step
    else:
        notes.append("Could not determine a tax year; taxes cannot be calculated.")

    # Calculate taxes if we found any usable tax_facts (either primary or fallback)
    if tax_facts:
        total_income = (tax_facts.get('fed_taxable_income', 0) or 0) + (tax_facts.get('state_taxable_income', 0) or 0)
        total_tax = (tax_facts.get('fed_total_tax', 0) or 0) + (tax_facts.get('state_total_tax', 0) or 0)
        if total_income > 0:
            effective_tax_rate = total_tax / total_income
            taxes = investment_income * effective_tax_rate if investment_income > 0 else 0
            notes.append(f"Effective rate used: {effective_tax_rate:.2%}.")
        else:
            notes.append("Taxable income for the selected year is zero; could not calculate rate.")

    # Step 4: Calculate what's left to spend
    spendable_cash = investment_income - fees - taxes

    return {
        "investment_income": investment_income,
        "advisory_fees": fees,
        "estimated_taxes": taxes,
        "spendable_cash": spendable_cash,
        "notes": ' '.join(notes)
    }

# --- NEW: Tax Rate Calculation ---
def calculate_effective_tax_rates_for_years(years: List[int]) -> List[Dict[str, Any]]:
    """
    Calculates effective tax rates for a given list of years based on stored TaxYearFacts.
    """
    results = []
    for year in years:
        tax_facts = db.get_tax_facts(year)
        year_data = {"year": year}

        if not tax_facts:
            year_data.update({
                "federal_rate": "N/A",
                "state_rate": "N/A",
                "combined_rate": "N/A",
                "notes": "No tax data entered for this year."
            })
            results.append(year_data)
            continue

        fed_income = tax_facts.get('fed_taxable_income') or 0
        fed_tax = tax_facts.get('fed_total_tax') or 0
        state_income = tax_facts.get('state_taxable_income') or 0
        state_tax = tax_facts.get('state_total_tax') or 0
        total_income = fed_income + state_income
        total_tax = fed_tax + state_tax

        year_data["federal_rate"] = f"{(fed_tax / fed_income * 100):.2f}%" if fed_income > 0 else "N/A"
        year_data["state_rate"] = f"{(state_tax / state_income * 100):.2f}%" if state_income > 0 else "N/A"
        year_data["combined_rate"] = f"{(total_tax / total_income * 100):.2f}%" if total_income > 0 else "N/A"
        year_data["notes"] = "Calculated from entered tax facts."
        
        results.append(year_data)
        
    return results

# --- NEW: Layered Portfolio Return Calculation ---
def calculate_layered_portfolio_returns(period: str) -> Dict[str, Any]:
    """
    Calculates layered portfolio returns.

    NOTE: This is a highly simplified, "since inception" calculation due to the lack
    of historical portfolio value snapshots. It should be labeled as an approximation.
    - Gross Return is based on total market value vs. total cost basis.
    - Fees are correctly calculated for the given period.
    - Taxes are estimated based on the effective tax rate applied to investment *yield* for
      the period, as capital gains data is not available.
    """
    total_market_value = db.get_total_portfolio_market_value()
    total_cost_basis = db.get_total_portfolio_cost_basis()

    if total_cost_basis == 0:
        return { # Return a zeroed-out state if there's no portfolio
            "gross_return_dollars": 0,
            "gross_return_percent": 0,
            "fees_dollars": 0,
            "after_fees_return_dollars": 0,
            "after_fees_return_percent": 0,
            "taxes_dollars": 0,
            "after_taxes_return_dollars": 0,
            "after_taxes_return_percent": 0,
            "notes": "No portfolio cost basis found. Cannot calculate returns."
        }

    # 1. Gross Return (Since Inception)
    gross_return_dollars = total_market_value - total_cost_basis
    gross_return_percent = (gross_return_dollars / total_cost_basis) * 100

    # 2. Fees (For the Period)
    fees_dollars = db.get_total_investment_fees_for_period(period)

    # 3. After Fees Return
    after_fees_return_dollars = gross_return_dollars - fees_dollars
    after_fees_return_percent = (after_fees_return_dollars / total_cost_basis) * 100

    # 4. Estimated Taxes (For the Period, on YIELD only)
    year_to_use = None
    if period.isdigit() and len(period) == 4:
        year_to_use = int(period)
    else:
        # For 'all', '6m', etc., use the latest year with transaction data as a proxy
        year_to_use = db.get_latest_transaction_year()

    notes = [f"Return calculated since inception (Total Market Value vs Total Cost Basis). Fees and Taxes are for the selected period '{period}'."]
    taxes_dollars = 0

    if year_to_use:
        investment_income_for_period = db.get_investment_income_for_period(period)
        tax_facts = db.get_tax_facts(year_to_use)
        
        if tax_facts and tax_facts.get('fed_taxable_income') and tax_facts.get('fed_total_tax'):
            total_income = (tax_facts.get('fed_taxable_income', 0) or 0) + (tax_facts.get('state_taxable_income', 0) or 0)
            total_tax = (tax_facts.get('fed_total_tax', 0) or 0) + (tax_facts.get('state_total_tax', 0) or 0)
            
            if total_income > 0:
                effective_tax_rate = total_tax / total_income
                taxes_dollars = investment_income_for_period * effective_tax_rate
                notes.append(f"Taxes estimated using {effective_tax_rate:.2%} effective rate from {year_to_use} tax data, applied to period investment yield of ${investment_income_for_period:,.0f}.")
            else:
                notes.append(f"Taxable income for {year_to_use} is zero; cannot calculate tax rate.")
        else:
            notes.append(f"Tax facts for {year_to_use} are incomplete; taxes could not be estimated.")
    else:
        notes.append("Could not determine a tax year; taxes could not be estimated.")

    # 5. After Taxes Return
    after_taxes_return_dollars = after_fees_return_dollars - taxes_dollars
    after_taxes_return_percent = (after_taxes_return_dollars / total_cost_basis) * 100

    return {
        "gross_return_dollars": round(gross_return_dollars, 2),
        "gross_return_percent": round(gross_return_percent, 2),
        "fees_dollars": round(fees_dollars, 2),
        "after_fees_return_dollars": round(after_fees_return_dollars, 2),
        "after_fees_return_percent": round(after_fees_return_percent, 2),
        "taxes_dollars": round(taxes_dollars, 2),
        "after_taxes_return_dollars": round(after_taxes_return_dollars, 2),
        "after_taxes_return_percent": round(after_taxes_return_percent, 2),
        "notes": " ".join(notes)
    }