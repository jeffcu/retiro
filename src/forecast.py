from datetime import date
from decimal import Decimal
from typing import List, Dict, Any, Optional
from . import database as db
from . import analysis # Re-use analysis for account aggregation consistency

# Uniform Lifetime Table for RMD divisors (Simplified)
# Source: IRS Publication 590-B
RMD_DIVISORS = {
    73: 26.5, 74: 25.5, 75: 24.6, 76: 23.7, 77: 22.9,
    78: 22.0, 79: 21.1, 80: 20.2, 81: 19.4, 82: 18.5,
    83: 17.7, 84: 16.8, 85: 16.0, 86: 15.2, 87: 14.4,
    88: 13.7, 89: 12.9, 90: 12.2, 91: 11.5, 92: 10.8,
    93: 10.1, 94: 9.5, 95: 8.9, 96: 8.4, 97: 7.8,
    98: 7.3, 99: 6.8, 100: 6.4
}

# 2024 Federal Tax Brackets (Taxable Income)
# Rate, Single Ceiling, Joint Ceiling
TAX_BRACKETS_2024 = [
    (0.10, 11600, 23200),
    (0.12, 47150, 94300),
    (0.22, 100525, 201050),
    (0.24, 191950, 383900),
    (0.32, 243725, 487450),
    (0.35, 609350, 1218700),
    (0.37, float('inf'), float('inf'))
]

STANDARD_DEDUCTION_2024 = {
    'single': 14600,
    'joint': 29200
}

# Categories to automatically exclude from Base CoL because they are calculated dynamically
EXCLUDED_EXPENSE_CATEGORIES = ["Taxes", "Federal Tax", "State Tax", "Income Tax"]

def get_rmd_divisor(age: int) -> float:
    # Fallback logic for ages > 100
    if age > 100:
        return max(3.0, 6.4 - (0.3 * (age - 100)))
    return RMD_DIVISORS.get(age, 27.4)

def calculate_progressive_tax(gross_income: float, filing_status: str, state_rate: float) -> Dict[str, float]:
    """
    Calculates estimated federal tax (progressive) and state tax (flat effective).
    Returns tax metrics including room to next bracket.
    """
    std_deduction = STANDARD_DEDUCTION_2024.get(filing_status, 14600)
    taxable_income = max(0, gross_income - std_deduction)
    
    fed_tax_bill = 0.0
    previous_ceiling = 0.0
    
    # Calculate Federal Tax
    for rate, single_ceil, joint_ceil in TAX_BRACKETS_2024:
        ceiling = joint_ceil if filing_status == 'joint' else single_ceil
        
        if taxable_income > ceiling:
            fed_tax_bill += (ceiling - previous_ceiling) * rate
            previous_ceiling = ceiling
        else:
            fed_tax_bill += (taxable_income - previous_ceiling) * rate
            break
            
    # Calculate State Tax (Simplified Effective Rate on Taxable Income)
    state_tax_bill = taxable_income * state_rate

    total_tax = fed_tax_bill + state_tax_bill
    effective_rate = (total_tax / gross_income) if gross_income > 0 else 0.0
    
    # Calculate Room to 24% Bracket (Top of 22% bracket)
    bracket_22_ceiling = TAX_BRACKETS_2024[2][2] if filing_status == 'joint' else TAX_BRACKETS_2024[2][1]
    dist_to_24 = max(0, bracket_22_ceiling - taxable_income)
    
    return {
        "federal_tax": fed_tax_bill,
        "state_tax": state_tax_bill,
        "total_tax": total_tax,
        "effective_rate": effective_rate,
        "taxable_income": taxable_income,
        "headroom_24_pct": dist_to_24
    }

def calculate_forecast() -> Dict[str, Any]:
    """
    The Time Machine Simulation Engine.
    Projects Net Worth year-over-year from the current year until Age 95.
    """
    
    # 1. Gather Simulation Inputs
    birth_year = db.get_setting('forecast_birth_year')
    inflation_rate = float(db.get_setting('forecast_inflation_rate') or 0.03)
    return_rate = float(db.get_setting('forecast_return_rate') or 0.05)
    withdrawal_tax_rate = float(db.get_setting('forecast_withdrawal_tax_rate') or 0.15) # For gross-up estimation
    
    state_tax_rate = float(db.get_setting('forecast_state_tax_rate') or 0.0) 
    if state_tax_rate > 0.5:
        print(f"Warning: State Tax Rate {state_tax_rate} seems high. Dividing by 100.")
        state_tax_rate = state_tax_rate / 100.0
    
    filing_status = db.get_setting('forecast_tax_filing_status') or 'single'
    if filing_status not in ['single', 'joint']: filing_status = 'single'

    tax_drag_rate = float(db.get_setting('forecast_tax_drag_rate') or 0.005) 
    
    retirement_age = int(db.get_setting('forecast_retirement_age') or 65)
    nogo_age = int(db.get_setting('forecast_nogo_age') or 80)
    
    withdrawal_strategy = db.get_setting('forecast_withdrawal_strategy') or 'standard'
    roth_conversion_target = db.get_setting('forecast_roth_conversion_target') or 'none'
    
    residence_sale_enabled = bool(db.get_setting('forecast_residence_sale_enabled') or False)
    residence_sale_year = db.get_setting('forecast_residence_sale_year')
    try:
        if residence_sale_year:
            residence_sale_year = int(residence_sale_year)
        else:
            residence_sale_year = None
    except (ValueError, TypeError):
        residence_sale_year = None

    phase_multipliers = db.get_setting('forecast_phase_multipliers') or {}
    base_col_categories = db.get_setting('forecast_base_col_categories') or []
    lookback_years = int(db.get_setting('forecast_base_col_lookback_years') or 1)

    if not birth_year:
        return {"error": "Birth Year not set. Please configure settings."}

    # 2. Establish Starting State (Buckets)
    # --- CRITICAL UPDATE v1.9.3: Use shared analysis function for bucket consistency with Home View ---
    account_summaries = analysis.get_account_performance_summary()
    
    buckets = {
        "Taxable": 0.0,
        "Deferred": 0.0,
        "Roth": 0.0,
        "Exempt": 0.0
    }
    
    unconfigured_accounts = set()
    alerts = []

    for acc in account_summaries:
        status = acc['tax_status']
        val = acc['total_market_value']
        if val <= 0: continue

        # Map tax status string to bucket key safely
        norm_status = status.strip().lower()
        if 'deferred' in norm_status or 'ira' in norm_status or '401' in norm_status:
            buckets['Deferred'] += val
        elif 'roth' in norm_status:
            buckets['Roth'] += val
        elif 'exempt' in norm_status:
            buckets['Exempt'] += val
        else:
            buckets['Taxable'] += val
            # If status is the default 'Taxable' but maybe shouldn't be, we can't easily detect that here without more logic.
            # But if the account metadata was missing, analysis.py defaults to Taxable. 
            # We can check if metadata exists in analysis.py, but for now we rely on the user checking the Home Page table.

    print(f"Forecast Engine Initialized with Buckets: {buckets}")

    properties = db.get_all_properties()
    
    # --- Filter Excluded Categories from Base CoL ---
    filtered_col_categories = [c for c in base_col_categories if c not in EXCLUDED_EXPENSE_CATEGORIES]
    
    base_col_breakdown = db.get_base_col_breakdown(filtered_col_categories, lookback_years)
    base_col_total_initial = sum(base_col_breakdown.values())
    
    discretionary_items = db.get_discretionary_budget_items()
    future_income_streams = db.get_all_future_income_streams()
    
    # 3. The Simulation Loop
    current_year = date.today().year
    end_year = birth_year + 95
    simulation_data = []
    
    previous_net_worth = 0.0

    # Alert Checks
    if residence_sale_enabled and residence_sale_year:
        has_primary = any(p['is_primary'] for p in properties)
        if not has_primary:
            alerts.append("Residence Sale Strategy is enabled, but no property is marked as 'Principal Residence'.")
    
    if buckets['Deferred'] == 0 and buckets['Roth'] == 0 and sum(buckets.values()) > 0:
         alerts.append("System Alert: All assets are classified as 'Taxable'. Verify your Account Settings if you have IRAs/401ks.")

    working_properties = [
        {
            "id": p['property_id'], 
            "value": float(p['current_value']),
            "debt": float(p['mortgage_balance']),
            "rate": float(p['appreciation_rate']),
            "is_primary": bool(p['is_primary'])
        } 
        for p in properties
    ]

    def get_phase_multiplier(category_name: str, phase_key: str) -> float:
        if not category_name or category_name not in phase_multipliers:
            return 1.0
        raw_val = phase_multipliers[category_name].get(phase_key, 100)
        if raw_val is None or raw_val == '': val = 100.0
        else:
            try: val = float(raw_val)
            except: val = 100.0
        return val / 100.0

    for year in range(current_year, end_year + 1):
        age = year - birth_year
        phase_key = "no" if age >= nogo_age else ("slow" if age >= retirement_age else "go")
        
        # Track events that add to Ordinary Income (Streams, RMDs, Conversions, Deferred Withdrawals)
        ordinary_income_events = 0.0

        # --- 1. Calculate Income (Non-Portfolio) ---
        year_income = 0.0
        for stream in future_income_streams:
            start = date.fromisoformat(stream['start_date'])
            end = date.fromisoformat(stream['end_date']) if stream['end_date'] else None
            if start.year <= year and (end is None or end.year >= year):
                amount = stream['amount']
                annual_amount = amount * 12 if stream['frequency'] == 'monthly' else amount
                increase_rate = stream['annual_increase_rate']
                adjusted_amount = annual_amount * ((1 + increase_rate) ** (year - start.year))
                year_income += adjusted_amount
                ordinary_income_events += adjusted_amount

        # --- 2. Calculate RMDs ---
        year_rmd = 0.0
        if age >= 75 and buckets['Deferred'] > 0:
            divisor = get_rmd_divisor(age)
            year_rmd = buckets['Deferred'] / divisor
            buckets['Deferred'] -= year_rmd
            year_income += year_rmd
            ordinary_income_events += year_rmd

        # --- 3. Calculate Living Expenses (Excluding Tax) ---
        years_from_start = year - current_year
        inflation_factor = (1 + inflation_rate) ** years_from_start
        
        year_living_expenses = 0.0
        expense_breakdown = {}

        for cat, amount in base_col_breakdown.items():
            multiplier = get_phase_multiplier(cat, phase_key)
            cost = (amount * inflation_factor * multiplier)
            year_living_expenses += cost
            expense_breakdown[cat] = round(cost, 2)
        
        year_discretionary = 0.0
        for item in discretionary_items:
            if not item.get('is_enabled', True): continue
            item_start = item['start_year']
            item_end = item['end_year'] if item['end_year'] else (9999 if item['is_recurring'] else item_start)
            if item_start <= year <= item_end:
                item_amount = item['amount']
                phase_mult = get_phase_multiplier(item.get('category'), phase_key)
                item_amount = item_amount * phase_mult
                if item['inflation_adjusted']: item_amount = item_amount * inflation_factor
                year_discretionary += item_amount
                expense_breakdown[item['name']] = round(item_amount, 2)

        # --- 4. Preliminary Tax Check (Pre-Withdrawal/Conversion) ---
        tax_metrics_pre = calculate_progressive_tax(ordinary_income_events, filing_status, state_tax_rate)

        # --- 5. ROTH CONVERSION STRATEGY (Phase 10) ---
        conversion_amount = 0.0
        if roth_conversion_target == 'fill_22' or roth_conversion_target == 'fill_24':
            # Determine ceiling based on target
            # Using 2024 brackets: 22% ends at 100k/201k. 24% ends at 191k/383k.
            # We use the generic 'headroom_24_pct' from our function which calculates distance to end of 22% (start of 24%)
            # If user wants to fill 24%, we need logic for that. For now, we support 'Fill to Top of 22%' which is common.
            
            if roth_conversion_target == 'fill_22':
                room = tax_metrics_pre['headroom_24_pct'] # This is distance to 24%
                if room > 0 and buckets['Deferred'] > 0:
                    conversion_amount = min(buckets['Deferred'], room)
                    buckets['Deferred'] -= conversion_amount
                    buckets['Roth'] += conversion_amount
                    ordinary_income_events += conversion_amount

        # --- 6. Residence Sale ---
        sale_proceeds = 0.0
        sale_event_triggered = False
        if residence_sale_enabled and residence_sale_year and year == residence_sale_year:
            primary_props = [p for p in working_properties if p['is_primary']]
            for prop in primary_props:
                proceeds = max(0.0, prop['value'] - prop['debt'])
                sale_proceeds += proceeds
                working_properties.remove(prop)
                sale_event_triggered = True

        # --- 7. Net Cashflow & Strategic Withdrawal ---
        # We must recalculate tax because of Conversions
        tax_metrics_post_conversion = calculate_progressive_tax(ordinary_income_events, filing_status, state_tax_rate)
        annual_tax_bill = tax_metrics_post_conversion['total_tax']
        expense_breakdown['Est. Income Tax'] = round(annual_tax_bill, 2)

        total_expenses = year_living_expenses + year_discretionary + annual_tax_bill

        net_cashflow = year_income + sale_proceeds - total_expenses
        strategy_executed = "Standard"
        deferred_withdrawals_for_spend = 0.0

        if net_cashflow > 0:
            strategy_executed = "Accumulation"
            buckets['Taxable'] += net_cashflow
        else:
            amount_needed = abs(net_cashflow)
            
            if withdrawal_strategy == 'deferred_first' and age >= 60:
                strategy_executed = "Deferred First"
                if amount_needed > 0:
                    # Gross up using estimated marginal rate
                    gross_needed = amount_needed / (1.0 - withdrawal_tax_rate)
                    from_deferred = min(buckets['Deferred'], gross_needed)
                    buckets['Deferred'] -= from_deferred
                    net_from_deferred = from_deferred * (1.0 - withdrawal_tax_rate)
                    deferred_withdrawals_for_spend += from_deferred
                    amount_needed -= net_from_deferred

                if amount_needed > 0:
                    from_taxable = min(buckets['Taxable'], amount_needed)
                    buckets['Taxable'] -= from_taxable
                    amount_needed -= from_taxable

                if amount_needed > 0:
                    from_roth = min(buckets['Roth'], amount_needed)
                    buckets['Roth'] -= from_roth
                    amount_needed -= from_roth

            else:
                strategy_executed = "Standard"
                from_taxable = min(buckets['Taxable'], amount_needed)
                buckets['Taxable'] -= from_taxable
                amount_needed -= from_taxable
                
                if amount_needed > 0:
                    gross_needed = amount_needed / (1.0 - withdrawal_tax_rate)
                    from_deferred = min(buckets['Deferred'], gross_needed)
                    buckets['Deferred'] -= from_deferred
                    net_from_deferred = from_deferred * (1.0 - withdrawal_tax_rate)
                    deferred_withdrawals_for_spend += from_deferred
                    amount_needed -= net_from_deferred

                if amount_needed > 0:
                    from_roth = min(buckets['Roth'], amount_needed)
                    buckets['Roth'] -= from_roth
                    amount_needed -= from_roth
        
        # --- 8. Final Tax Recalculation (Post-Withdrawal) ---
        # If we pulled more from deferred to pay bills, we owe more tax.
        ordinary_income_events += deferred_withdrawals_for_spend
        final_tax_metrics = calculate_progressive_tax(ordinary_income_events, filing_status, state_tax_rate)

        # --- 9. Investment Growth ---
        taxable_return = return_rate - tax_drag_rate
        if taxable_return < 0: taxable_return = 0

        buckets['Taxable'] *= (1 + taxable_return)
        buckets['Deferred'] *= (1 + return_rate)
        buckets['Roth'] *= (1 + return_rate)
        buckets['Exempt'] *= (1 + return_rate)
        
        total_investment_growth = \
            (buckets['Taxable'] * (taxable_return / (1+taxable_return))) + \
            ((buckets['Deferred'] + buckets['Roth'] + buckets['Exempt']) * (return_rate / (1+return_rate)))

        # --- 10. Real Estate Growth ---
        year_re_value = 0.0
        year_re_debt = 0.0
        for prop in working_properties:
            prop['value'] = prop['value'] * (1 + prop['rate'])
            year_re_value += prop['value']
            year_re_debt += prop['debt']

        total_liquid = sum(buckets.values())
        total_net_worth = total_liquid + (year_re_value - year_re_debt)
        
        nw_delta = 0
        if year > current_year:
            nw_delta = total_net_worth - previous_net_worth
        previous_net_worth = total_net_worth

        simulation_data.append({
            "year": year,
            "age": age,
            "phase": phase_key,
            "liquid_assets": round(total_liquid, 2),
            "bucket_taxable": round(buckets['Taxable'], 2),
            "bucket_deferred": round(buckets['Deferred'], 2),
            "bucket_roth": round(buckets['Roth'], 2),
            "rmd_event": round(year_rmd, 2),
            "roth_conversion": round(conversion_amount, 2),
            "real_estate_equity": round(year_re_value - year_re_debt, 2),
            "total_net_worth": round(total_net_worth, 2),
            "nw_delta": round(nw_delta, 2),
            "total_income": round(year_income, 2),
            "total_expenses": round(total_expenses, 2),
            "base_col_expense": round(year_living_expenses, 2),
            "discretionary_expense": round(year_discretionary, 2),
            "expense_breakdown": expense_breakdown,
            "net_cashflow": round(year_income - total_expenses + sale_proceeds, 2),
            "investment_growth": round(total_investment_growth, 2),
            "sale_event": sale_event_triggered,
            "strategy_executed": strategy_executed,
            "tax_metrics": {
                "taxable_income": round(final_tax_metrics['taxable_income'], 2),
                "effective_rate": round(final_tax_metrics['effective_rate'] * 100, 2),
                "headroom_24_pct": round(final_tax_metrics['headroom_24_pct'], 2),
                "total_tax": round(final_tax_metrics['total_tax'], 2)
            }
        })
        
    return {
        "simulation_series": simulation_data,
        "alerts": alerts,
        "settings": {
            "birth_year": birth_year,
            "starting_nw": total_liquid + (year_re_value - year_re_debt if 'year_re_value' in locals() else 0),
            "starting_base_col": round(base_col_total_initial, 2),
            "withdrawal_strategy": withdrawal_strategy
        }
    }
