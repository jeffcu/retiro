from datetime import date
from decimal import Decimal
from typing import List, Dict, Any, Optional
from . import database as db

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

def get_rmd_divisor(age: int) -> float:
    # Fallback logic for ages > 100
    if age > 100:
        return max(3.0, 6.4 - (0.3 * (age - 100)))
    return RMD_DIVISORS.get(age, 27.4)

def calculate_forecast() -> Dict[str, Any]:
    """
    The Time Machine Simulation Engine.
    Projects Net Worth year-over-year from the current year until Age 95.
    
    MAJOR UPGRADE (v2.1):
    - Multi-Bucket Simulation (Taxable, Deferred, Roth).
    - RMD Logic implementation.
    - Strategic Withdrawal Order.
    - Residence Sale Logic Fix.
    - Restored detailed expense telemetry for UI.
    - [Scotty] Added Annualized CoL Averaging support.
    """
    
    # 1. Gather Simulation Inputs
    birth_year = db.get_setting('forecast_birth_year')
    inflation_rate = float(db.get_setting('forecast_inflation_rate') or 0.03)
    return_rate = float(db.get_setting('forecast_return_rate') or 0.05)
    withdrawal_tax_rate = float(db.get_setting('forecast_withdrawal_tax_rate') or 0.15)
    
    retirement_age = int(db.get_setting('forecast_retirement_age') or 65)
    nogo_age = int(db.get_setting('forecast_nogo_age') or 80)
    
    # Residence Sale Strategy
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
    
    # Scotty: Get the lookback averaging setting (default 1 year)
    lookback_years = int(db.get_setting('forecast_base_col_lookback_years') or 1)

    if not birth_year:
        return {"error": "Birth Year not set. Please configure settings."}

    # 2. Establish Starting State (Buckets)
    account_metadata = db.get_account_metadata()
    holdings = db.get_holdings()
    
    # Bucketize Holdings
    buckets = {
        "Taxable": 0.0,
        "Deferred": 0.0,
        "Roth": 0.0,
        "Exempt": 0.0
    }
    
    # Group by tax status
    for h in holdings:
        if h.get('market_value'):
            acct_id = h['account_id']
            # Default to 'Taxable' if not set
            status = account_metadata.get(acct_id, {}).get('tax_status', 'Taxable')
            buckets[status] += float(h['market_value'])

    properties = db.get_all_properties()
    
    # Scotty: Pass the lookback years to the breakdown function
    base_col_breakdown = db.get_base_col_breakdown(base_col_categories, lookback_years)
    base_col_total_initial = sum(base_col_breakdown.values())
    
    discretionary_items = db.get_discretionary_budget_items()
    future_income_streams = db.get_all_future_income_streams()
    
    # 3. The Simulation Loop
    current_year = date.today().year
    end_year = birth_year + 95
    simulation_data = []
    alerts = []

    # Alert Check for Residence Sale
    if residence_sale_enabled and residence_sale_year:
        has_primary = any(p['is_primary'] for p in properties)
        if not has_primary:
            alerts.append("Residence Sale Strategy is enabled, but no property is marked as 'Principal Residence'. No sale will occur.")

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

        # --- 2. Calculate RMDs (Required Minimum Distributions) ---
        # RMDs apply to Deferred buckets starting age 75 (simplified SECURE 2.0)
        year_rmd = 0.0
        if age >= 75 and buckets['Deferred'] > 0:
            divisor = get_rmd_divisor(age)
            year_rmd = buckets['Deferred'] / divisor
            # RMD is forced out of Deferred
            buckets['Deferred'] -= year_rmd
            # Logic: RMDs are taxable income. We treat them as cashflow inflow (income),
            # but we must account for taxes on them immediately.
            # For simplicity, we add to year_income, and the net cashflow logic handles the tax drag
            # if we end up saving it (taxable bucket) or spending it.
            # HOWEVER, RMDs *force* a tax event. 
            # We will assume RMD is added to 'year_income' but it carries a tax liability.
            # To keep the model simple: Add to income. If expenses < income, it goes to Taxable Bucket.
            year_income += year_rmd

        # --- 3. Calculate Expenses ---
        years_from_start = year - current_year
        inflation_factor = (1 + inflation_rate) ** years_from_start
        
        year_base_col = 0.0
        for cat, amount in base_col_breakdown.items():
            multiplier = get_phase_multiplier(cat, phase_key)
            year_base_col += (amount * inflation_factor * multiplier)
        
        year_discretionary = 0.0
        for item in discretionary_items:
            item_start = item['start_year']
            item_end = item['end_year'] if item['end_year'] else (9999 if item['is_recurring'] else item_start)
            if item_start <= year <= item_end:
                item_amount = item['amount']
                phase_mult = get_phase_multiplier(item.get('category'), phase_key)
                item_amount = item_amount * phase_mult
                if item['inflation_adjusted']:
                    item_amount = item_amount * inflation_factor
                year_discretionary += item_amount

        total_expenses = year_base_col + year_discretionary

        # --- 4. Sale of Residence Logic ---
        sale_proceeds = 0.0
        sale_event_triggered = False
        if residence_sale_enabled and residence_sale_year and year == residence_sale_year:
            primary_props = [p for p in working_properties if p['is_primary']]
            for prop in primary_props:
                proceeds = max(0.0, prop['value'] - prop['debt'])
                sale_proceeds += proceeds
                working_properties.remove(prop)
                sale_event_triggered = True

        # --- 5. Net Cashflow & Strategic Withdrawal ---
        # Logic: 
        #   Net = Income (incl RMDs) + Sale Proceeds - Expenses
        #   If Net > 0: Surplus -> Invest in Taxable
        #   If Net < 0: Deficit -> Withdraw from Taxable -> Deferred -> Roth
        
        net_cashflow = year_income + sale_proceeds - total_expenses
        
        tax_drag = 0.0

        if net_cashflow > 0:
            # SURPLUS: Add to Taxable Bucket
            # Note: We already paid tax on RMDs implicitly by not having a 100% tax drag here.
            # Ideally, we'd subtract tax from RMD before adding to surplus.
            # Simplified: Surplus goes to Taxable.
            buckets['Taxable'] += net_cashflow
        else:
            # DEFICIT: Need to withdraw
            amount_needed = abs(net_cashflow)
            
            # A. Try Taxable first
            from_taxable = min(buckets['Taxable'], amount_needed)
            buckets['Taxable'] -= from_taxable
            amount_needed -= from_taxable
            
            # B. Try Roth next (Tax Free)
            # (Strategic change: Roth is usually last to preserve tax-free growth, 
            # but some strategies use it to fill low tax brackets. We'll put it LAST for standard advice).
            
            # B. Try Deferred (Taxable Withdrawal)
            if amount_needed > 0:
                # We need to withdraw enough to cover amount_needed PLUS taxes.
                # Gross_Withdrawal = Amount / (1 - Tax_Rate)
                gross_withdrawal_needed = amount_needed / (1.0 - withdrawal_tax_rate)
                from_deferred = min(buckets['Deferred'], gross_withdrawal_needed)
                
                buckets['Deferred'] -= from_deferred
                
                # Net cash realized is what we actually spend
                net_from_deferred = from_deferred * (1.0 - withdrawal_tax_rate)
                amount_needed -= net_from_deferred
                tax_drag += (from_deferred - net_from_deferred)

            # C. Try Roth (Tax Free) - Last Resort
            if amount_needed > 0:
                from_roth = min(buckets['Roth'], amount_needed)
                buckets['Roth'] -= from_roth
                amount_needed -= from_roth

            # If amount_needed > 0 here, we are bankrupt for this year.

        # --- 6. Investment Growth (End of Year) ---
        # Grow all buckets
        # Note: We apply growth AFTER withdrawals to be conservative (withdraw at start of year)
        buckets['Taxable'] *= (1 + return_rate)
        buckets['Deferred'] *= (1 + return_rate)
        buckets['Roth'] *= (1 + return_rate)
        buckets['Exempt'] *= (1 + return_rate)
        
        total_investment_growth = (buckets['Taxable'] + buckets['Deferred'] + buckets['Roth'] + buckets['Exempt']) * (return_rate / (1+return_rate))

        # --- 7. Real Estate Growth ---
        year_re_value = 0.0
        year_re_debt = 0.0
        for prop in working_properties:
            prop['value'] = prop['value'] * (1 + prop['rate'])
            year_re_value += prop['value']
            year_re_debt += prop['debt']

        total_liquid = sum(buckets.values())
        total_net_worth = total_liquid + (year_re_value - year_re_debt)

        simulation_data.append({
            "year": year,
            "age": age,
            "phase": phase_key,
            "liquid_assets": round(total_liquid, 2),
            "bucket_taxable": round(buckets['Taxable'], 2),
            "bucket_deferred": round(buckets['Deferred'], 2),
            "bucket_roth": round(buckets['Roth'], 2),
            "rmd_event": round(year_rmd, 2),
            "real_estate_equity": round(year_re_value - year_re_debt, 2),
            "total_net_worth": round(total_net_worth, 2),
            "total_income": round(year_income, 2),
            "total_expenses": round(total_expenses, 2),
            "base_col_expense": round(year_base_col, 2), # RESTORED
            "discretionary_expense": round(year_discretionary, 2), # RESTORED
            "net_cashflow": round(year_income - total_expenses + sale_proceeds, 2),
            "investment_growth": round(total_investment_growth, 2),
            "sale_event": sale_event_triggered
        })
        
    return {
        "simulation_series": simulation_data,
        "alerts": alerts,
        "settings": {
            "birth_year": birth_year,
            "starting_nw": total_liquid + (year_re_value - year_re_debt if 'year_re_value' in locals() else 0),
            "starting_base_col": round(base_col_total_initial, 2)
        }
    }
