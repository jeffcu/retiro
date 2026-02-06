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

    # Step 3: Calculate estimated taxes on the income
    year_to_use = None
    if period.isdigit() and len(period) == 4:
        year_to_use = int(period)
    else:
        year_to_use = db.get_latest_transaction_year()

    notes = f"Using data for period '{period}'."
    taxes = 0

    if year_to_use:
        tax_facts = db.get_tax_facts(year_to_use)
        if tax_facts and tax_facts.get('fed_taxable_income') and tax_facts.get('fed_total_tax'):
            total_income = (tax_facts.get('fed_taxable_income', 0) or 0) + (tax_facts.get('state_taxable_income', 0) or 0)
            total_tax = (tax_facts.get('fed_total_tax', 0) or 0) + (tax_facts.get('state_total_tax', 0) or 0)
            effective_tax_rate = total_tax / total_income if total_income > 0 else 0
            
            # Apply the effective rate to the investment income
            taxes = investment_income * effective_tax_rate if investment_income > 0 else 0
            notes += f" Estimated taxes based on {effective_tax_rate:.2%} effective rate from {year_to_use} tax data."
        else:
            notes += f" Tax facts for {year_to_use} are incomplete; taxes are not calculated."
    else:
        notes += " Could not determine a tax year; taxes are not calculated."

    # Step 4: Calculate what's left to spend
    spendable_cash = investment_income - fees - taxes

    return {
        "investment_income": investment_income,
        "advisory_fees": fees,
        "estimated_taxes": taxes,
        "spendable_cash": spendable_cash,
        "notes": notes
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

# --- Layered Returns Calculation --- 
def calculate_layered_returns(period: str) -> Dict[str, Any]:
    """
    Calculates gross return, fees, taxes, and after-tax return for a period.
    (PRS Section 7.2)
    """
    # STEP 1: Calculate Gross Return as (Market Value - Cost Basis).
    # This is an approximation of total unrealized gain.
    total_market_value = db.get_total_portfolio_market_value()
    total_cost_basis = db.get_total_portfolio_cost_basis()
    gross_return = total_market_value - total_cost_basis
    
    # STEP 2: Calculate fees for the specified period.
    fees = db.get_total_investment_fees_for_period(period)

    # STEP 3: Determine the tax year to use.
    year_to_use = None
    if period.isdigit() and len(period) == 4:
        year_to_use = int(period)
    else:
        # Fallback to the latest year with transaction data as a proxy.
        year_to_use = db.get_latest_transaction_year()

    notes = "Gross return is lifetime unrealized gain (Market Value - Cost Basis). Fees & Taxes are for the selected period."

    if not year_to_use:
        # No tax data available, so we can't calculate taxes.
        return {
            "gross_return": gross_return,
            "fees": fees,
            "taxes": 0,
            "after_tax_return": gross_return - fees,
            "notes": notes
        }

    # STEP 4: Fetch tax facts and calculate effective tax rate.
    tax_facts = db.get_tax_facts(year_to_use)
    if not tax_facts or not tax_facts.get('fed_taxable_income') or not tax_facts.get('fed_total_tax'):
        return {
            "gross_return": gross_return,
            "fees": fees,
            "taxes": 0,
            "after_tax_return": gross_return - fees,
            "notes": f"{notes} Tax facts for {year_to_use} are incomplete."
        }
    
    # Calculate a blended federal and state effective tax rate.
    total_income = (tax_facts.get('fed_taxable_income', 0) or 0) + (tax_facts.get('state_taxable_income', 0) or 0)
    total_tax = (tax_facts.get('fed_total_tax', 0) or 0) + (tax_facts.get('state_total_tax', 0) or 0)

    effective_tax_rate = total_tax / total_income if total_income > 0 else 0
    
    # Apply the tax rate to the investment gains (gross return).
    # This is an estimation, as per PRS.
    taxes = gross_return * effective_tax_rate if gross_return > 0 else 0
    after_tax_return = gross_return - fees - taxes

    return {
        "gross_return": gross_return,
        "fees": fees,
        "taxes": taxes,
        "after_tax_return": after_tax_return,
        "notes": f"{notes} Using effective tax rate of {effective_tax_rate:.2%} from {year_to_use} tax data."
    }

def generate_portfolio_return_sankey(period: str) -> Dict[str, Any]:
    """
    Generates the data for the Portfolio Return Waterfall Sankey diagram.
    (PRS Section 2.1.C)
    """
    returns = calculate_layered_returns(period)

    gross_return = returns['gross_return']
    fees = returns['fees']
    taxes = returns['taxes']
    after_tax_return = returns['after_tax_return']

    # --- NEW: Handle negative gross returns (a loss) --- 
    if gross_return <= 0:
        # If there's a loss, the waterfall is simpler.
        # Gross Loss -> Fees -> Net Loss
        nodes = [
            {"id": "Gross Loss"},
            {"id": "Fees"},
            {"id": "Net Loss"}
        ]
        links = [
            {"source": "Gross Loss", "target": "Net Loss", "value": round(abs(gross_return), 2)},
            {"source": "Fees", "target": "Net Loss", "value": round(fees, 2)}
        ]
        return {"nodes": nodes, "links": links, "notes": returns.get('notes')}

    # --- Logic for positive gross returns --- 
    # Ensure we don't create negative values in the Sankey chart.
    if gross_return < (fees + taxes):
        # In this edge case, just show fees and taxes eating the whole return.
        after_tax_return = 0
        if gross_return < fees:
            fees = gross_return
            taxes = 0
        else:
            taxes = gross_return - fees

    nodes = [
        {"id": "Gross Return"},
        {"id": "Fees"},
        {"id": "Taxes"},
        {"id": "After-Tax Return"}
    ]

    links = []
    if gross_return > 0:
        if fees > 0:
            links.append({"source": "Gross Return", "target": "Fees", "value": round(fees, 2)})
        if taxes > 0:
            links.append({"source": "Gross Return", "target": "Taxes", "value": round(taxes, 2)})
        if after_tax_return > 0:
            links.append({"source": "Gross Return", "target": "After-Tax Return", "value": round(after_tax_return, 2)})

    return {"nodes": nodes, "links": links, "notes": returns.get('notes')}

