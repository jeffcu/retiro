from typing import Dict, Any, List
from collections import defaultdict
from . import database as db
from dateutil.relativedelta import relativedelta
from datetime import date, timedelta

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

    # Step 3: Calculate estimated taxes on the income with LTCG 15% standard
    notes = [f"Using data for period '{period}'."]
    taxes = investment_income * 0.15 if investment_income > 0 else 0
    notes.append("Applying standard 15% Long-Term Capital Gains rate to yield.")

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

# --- REVISED: Portfolio Overall Gains Calculation ---
def calculate_portfolio_summary_metrics() -> Dict[str, Any]:
    """
    Calculates key portfolio summary metrics based on "since inception" data.
    This provides a simple, non-period-specific overview of the portfolio's
    current standing against its cost basis, as requested by the Captain.
    """
    total_market_value = db.get_total_portfolio_market_value()
    total_cost_basis = db.get_total_portfolio_cost_basis()

    if total_cost_basis == 0:
        return {
            "total_market_value": round(total_market_value, 2),
            "total_cost_basis": 0,
            "total_gain_dollars": 0,
            "total_gain_percent": 0,
            "notes": "Portfolio cost basis is zero. Cannot calculate gains."
        }

    total_gain_dollars = total_market_value - total_cost_basis
    total_gain_percent = (total_gain_dollars / total_cost_basis) * 100 if total_cost_basis else 0

    return {
        "total_market_value": round(total_market_value, 2),
        "total_cost_basis": round(total_cost_basis, 2),
        "total_gain_dollars": round(total_gain_dollars, 2),
        "total_gain_percent": round(total_gain_percent, 2),
        "notes": "Calculated since inception (Total Market Value vs. Total Cost Basis). This is not a time-weighted return."
    }

# --- NEW: Account Performance Summary (Source of Truth for Forecast) ---
def get_account_performance_summary() -> List[Dict[str, Any]]:
    """
    Aggregates holdings by account (and sub-account/number) to provide a clear view 
    of where assets live and how they are taxed. This data drives the Forecast engine's 
    starting buckets and the Account Summary table on the Home Page.
    """
    # Get all holdings
    holdings = db.get_holdings()
    # Get metadata
    metadata = db.get_account_metadata() # returns dict {account_id: {tax_status, notes, group_name}}

    # Group by (account_id, account_number)
    accounts = {}
    for h in holdings:
        # Group ID is the high-level import batch (e.g. "Fidelity")
        group_id = h['account_id'] 
        # Sub-Account Number (e.g. "123456789")
        acc_num = h.get('account_number')
        
        # Create a unique key for aggregation
        # If no account number, we fall back to just the group ID
        key = (group_id, acc_num) if acc_num else (group_id, None)
        
        if key not in accounts:
            # Determine display name and metadata lookup key
            if acc_num:
                lookup_key = f"{group_id}::{acc_num}"
            else:
                lookup_key = group_id

            # Determine tax status AND group name via hierarchical lookup
            tax_status = "Taxable" # Default
            group_name = None
            
            # 1. Try specific composite key (Group::Number)
            if lookup_key in metadata:
                tax_status = metadata[lookup_key]['tax_status']
                group_name = metadata[lookup_key].get('group_name')
            # 2. Try just the Group ID (wildcard for all accounts in that file)
            elif group_id in metadata:
                 tax_status = metadata[group_id]['tax_status']
                 group_name = metadata[group_id].get('group_name')
            # 3. Case-insensitive fallback
            else:
                 for m_id, m_data in metadata.items():
                     if m_id.strip().lower() == lookup_key.strip().lower() or m_id.strip().lower() == group_id.strip().lower():
                         tax_status = m_data['tax_status']
                         group_name = m_data.get('group_name')
                         break
            
            # If no manual group name override, use the import account_id as the group
            final_group_id = group_name if group_name else group_id
            
            display_name = f"{final_group_id} - {acc_num}" if acc_num else final_group_id

            accounts[key] = {
                "account_id": display_name,
                "group_id": final_group_id,
                "account_number": acc_num,
                "lookup_key": lookup_key,
                "tax_status": tax_status,
                "group_name": group_name,
                "total_market_value": 0.0,
                "total_cost_basis": 0.0
            }
        
        accounts[key]["total_market_value"] += (h['market_value'] or 0.0)
        accounts[key]["total_cost_basis"] += (h['cost_basis'] or 0.0)

    # Calculate Gains and Format
    result = []
    for acc in accounts.values():
        mv = acc['total_market_value']
        cb = acc['total_cost_basis']
        gain = mv - cb
        gain_pct = (gain / cb) * 100 if cb != 0 else 0.0
        
        acc['total_gain'] = round(gain, 2)
        acc['total_gain_percent'] = round(gain_pct, 2)
        acc['total_market_value'] = round(mv, 2)
        acc['total_cost_basis'] = round(cb, 2)
        result.append(acc)
        
    # Sort by Group ID, then Market Value desc
    return sorted(result, key=lambda x: (x['group_id'], -x['total_market_value']))

# --- NEW: Layered Returns Calculation ---
def calculate_layered_returns_summary() -> Dict[str, Any]:
    """
    Calculates a full breakdown of returns from gross to after-tax and prepares Sankey data.
    All calculations are since inception.
    """
    # 1. Gross Return (since inception gain)
    gains_summary = calculate_portfolio_summary_metrics()
    gross_return = gains_summary.get('total_gain_dollars', 0)
    notes = [gains_summary.get('notes', "Gains since inception.")]

    # 2. Fees (since inception)
    total_fees = db.get_total_investment_fees_for_period('all')

    # 3. Tax Estimation
    estimated_taxes = 0
    notes.append("Taxes estimated using standard 15% Long-Term Capital Gains rate.")
    if gross_return > 0:
        estimated_taxes = gross_return * 0.15

    # 4. Final Metrics & Sankey Values
    # Ensure leakage values don't exceed the gross return for a clean visualization.
    fees_for_sankey = min(total_fees, gross_return) if gross_return > 0 else 0
    taxes_for_sankey = min(estimated_taxes, max(0, gross_return - fees_for_sankey)) if gross_return > 0 else 0
    after_tax_return = gross_return - fees_for_sankey - taxes_for_sankey

    # 5. Sankey Data Structure
    sankey_data = { "nodes": [], "links": [] }
    if gross_return > 0:
        sankey_data["nodes"] = [
            {"id": "Gross Return"},
            {"id": "Fees"},
            {"id": "Taxes"},
            {"id": "After-Tax Return"}
        ]
        sankey_data["links"] = [
            {"source": "Gross Return", "target": "Fees", "value": round(fees_for_sankey, 2)},
            {"source": "Gross Return", "target": "Taxes", "value": round(taxes_for_sankey, 2)},
            {"source": "Gross Return", "target": "After-Tax Return", "value": round(after_tax_return, 2)}
        ]

    return {
        "metrics": {
            "gross_return": round(gross_return, 2),
            "total_fees": round(total_fees, 2),
            "estimated_taxes": round(estimated_taxes, 2),
            "after_tax_return": round(after_tax_return, 2)
        },
        "sankey_data": sankey_data,
        "notes": " ".join(notes)
    }

# --- REVISED: Portfolio Waterfall Calculation for Performance Attribution ---
def calculate_portfolio_waterfall(period: str) -> Dict[str, Any]:
    """
    Calculates a full performance attribution waterfall for a given period.
    This version requires historical portfolio value snapshots to work correctly.
    (PRS Section 4.5, "Operation Snapshot")
    """
    notes = [f"Performance analysis for period '{period}'."]
    
    # 1. Determine Date Range from Period string
    end_date = date.today()
    start_date = None
    
    inception_date_str = db.get_setting('portfolio_inception_date')
    inception_date = date.fromisoformat(inception_date_str) if inception_date_str else None

    if period.isdigit() and len(period) == 4:
        year = int(period)
        start_date = date(year, 1, 1)
        end_date = date(year, 12, 31)
    elif period.endswith('m'):
        months = int(period[:-1])
        start_date = end_date - relativedelta(months=months)
    else: # 'all'
        if inception_date:
            start_date = inception_date
        else:
            # Fallback if no inception date is set
            start_date = date(1970, 1, 1)
            notes.append("WARNING: No portfolio inception date set. Using earliest available data.")

    # The actual period start is the day *before* our start_date for value lookup
    start_value_lookup_date = (start_date - timedelta(days=1)).isoformat()
    end_value_lookup_date = end_date.isoformat()

    # 2. Get Start and End Values from Snapshots
    start_snapshot = db.get_closest_snapshot_value_before_date(start_value_lookup_date)
    end_snapshot = db.get_closest_snapshot_value_before_date(end_value_lookup_date)

    start_value = start_snapshot['market_value'] if start_snapshot else 0
    end_value = end_snapshot['market_value'] if end_snapshot else 0
    
    if start_snapshot:
        notes.append(f"Start value from snapshot on {start_snapshot['snapshot_date']}.")
    else:
        notes.append("WARNING: No portfolio snapshot found for start of period. Assuming $0.")
        
    if end_snapshot:
        notes.append(f"End value from snapshot on {end_snapshot['snapshot_date']}.")
    else:
        notes.append("WARNING: No portfolio snapshot found for end of period. Using $0.")

    # 3. Calculate Cash Flows for the period
    contributions = db.get_external_contributions(period)
    portfolio_yield = db.get_investment_income_for_period(period)
    withdrawals = db.get_withdrawals_for_spending(period)
    fees = db.get_total_investment_fees_for_period(period)
    
    # --- Tax Calculation (on yield only) ---
    estimated_taxes = 0
    if portfolio_yield > 0:
        estimated_taxes = portfolio_yield * 0.15
        notes.append("Taxes on yield estimated using standard 15% Long-Term Capital Gains rate.")

    # 4. Calculate Net Cash Flow and Market Growth
    net_cash_flow = (contributions + portfolio_yield) - (withdrawals + fees + estimated_taxes)
    
    # Market growth is the plug: (End Value - Start Value) - Net Cash Flow
    market_growth = 0
    if start_value > 0 and end_value > 0:
        market_growth = (end_value - start_value) - net_cash_flow
    else:
        notes.append("Market growth cannot be calculated without start and end values.")
    
    return {
        "start_of_period_value": round(start_value, 2) if start_value is not None else None,
        "external_contributions": round(contributions, 2),
        "portfolio_yield": round(portfolio_yield, 2),
        "withdrawals_for_spending": round(withdrawals, 2),
        "fees_and_estimated_taxes": round(fees + estimated_taxes, 2),
        "net_cash_flow": round(net_cash_flow, 2),
        "market_growth_or_loss": round(market_growth, 2),
        "end_of_period_value": round(end_value, 2) if end_value is not None else None,
        "notes": " ".join(notes)
    }
