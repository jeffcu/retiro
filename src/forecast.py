from datetime import date
from decimal import Decimal
from typing import List, Dict, Any, Optional
import copy
from . import database as db
from . import analysis

# Uniform Lifetime Table for RMD divisors (Simplified)
RMD_DIVISORS = {
    73: 26.5, 74: 25.5, 75: 24.6, 76: 23.7, 77: 22.9,
    78: 22.0, 79: 21.1, 80: 20.2, 81: 19.4, 82: 18.5,
    83: 17.7, 84: 16.8, 85: 16.0, 86: 15.2, 87: 14.4,
    88: 13.7, 89: 12.9, 90: 12.2, 91: 11.5, 92: 10.8,
    93: 10.1, 94: 9.5, 95: 8.9, 96: 8.4, 97: 7.8,
    98: 7.3, 99: 6.8, 100: 6.4
}

# 2024 Federal Tax Brackets (Taxable Income)
TAX_BRACKETS_2024 = [
    (0.10, 11600, 23200),
    (0.12, 47150, 94300),
    (0.22, 100525, 201050),
    (0.24, 191950, 383900),
    (0.32, 243725, 487450),
    (0.35, 609350, 1218700),
    (0.37, float('inf'), float('inf'))
]

# 2024 Long-Term Capital Gains Brackets
LTCG_BRACKETS_2024 = [
    (0.00, 47025, 94050),
    (0.15, 518900, 583750),
    (0.20, float('inf'), float('inf'))
]

STANDARD_DEDUCTION_2024 = {
    'single': 14600,
    'joint': 29200
}

EXCLUDED_EXPENSE_CATEGORIES = ["Taxes", "Federal Tax", "State Tax", "Income Tax"]

def get_rmd_divisor(age: int) -> float:
    if age > 100:
        return max(3.0, 6.4 - (0.3 * (age - 100)))
    return RMD_DIVISORS.get(age, 27.4)

def calculate_taxable_ss(ss_benefit: float, other_income: float, filing_status: str) -> float:
    if ss_benefit <= 0: return 0.0
    combined_income = other_income + (0.5 * ss_benefit)
    
    if filing_status == 'joint':
        base_threshold, upper_threshold = 32000, 44000
    else:
        base_threshold, upper_threshold = 25000, 34000
        
    if combined_income <= base_threshold:
        return 0.0
    elif combined_income <= upper_threshold:
        taxable = 0.5 * (combined_income - base_threshold)
        return min(0.85 * ss_benefit, taxable)
    else:
        tier1 = 0.5 * (upper_threshold - base_threshold)
        tier2 = 0.85 * (combined_income - upper_threshold)
        return min(0.85 * ss_benefit, tier1 + tier2)

def calculate_progressive_tax(ordinary_income: float, ltcg_income: float, filing_status: str, state_rate: float) -> Dict[str, float]:
    std_deduction = STANDARD_DEDUCTION_2024.get(filing_status, 14600)
    taxable_ordinary = max(0, ordinary_income - std_deduction)
    
    fed_ordinary_tax = 0.0
    previous_ceiling = 0.0
    
    for rate, single_ceil, joint_ceil in TAX_BRACKETS_2024:
        ceiling = joint_ceil if filing_status == 'joint' else single_ceil
        if taxable_ordinary > ceiling:
            fed_ordinary_tax += (ceiling - previous_ceiling) * rate
            previous_ceiling = ceiling
        else:
            fed_ordinary_tax += (taxable_ordinary - previous_ceiling) * rate
            break
            
    fed_ltcg_tax = 0.0
    unallocated_ltcg = ltcg_income
    current_income_stack = taxable_ordinary
    
    for rate, single_ceil, joint_ceil in LTCG_BRACKETS_2024:
        ceiling = joint_ceil if filing_status == 'joint' else single_ceil
        if unallocated_ltcg <= 0:
            break
        if current_income_stack < ceiling:
            room_in_bracket = ceiling - current_income_stack
            amount_to_tax = min(unallocated_ltcg, room_in_bracket)
            fed_ltcg_tax += amount_to_tax * rate
            unallocated_ltcg -= amount_to_tax
            current_income_stack += amount_to_tax

    total_taxable = taxable_ordinary + ltcg_income
    state_tax_bill = total_taxable * state_rate

    total_tax = fed_ordinary_tax + fed_ltcg_tax + state_tax_bill
    gross_income = ordinary_income + ltcg_income
    effective_rate = (total_tax / gross_income) if gross_income > 0 else 0.0
    
    # Headroom Calculations for Roth Conversions
    bracket_22_ceiling = TAX_BRACKETS_2024[2][2] if filing_status == 'joint' else TAX_BRACKETS_2024[2][1]
    dist_to_22_top = max(0, (bracket_22_ceiling + std_deduction) - (ordinary_income + ltcg_income))
    
    bracket_24_ceiling = TAX_BRACKETS_2024[3][2] if filing_status == 'joint' else TAX_BRACKETS_2024[3][1]
    dist_to_24_top = max(0, (bracket_24_ceiling + std_deduction) - (ordinary_income + ltcg_income))
    
    bracket_32_ceiling = TAX_BRACKETS_2024[4][2] if filing_status == 'joint' else TAX_BRACKETS_2024[4][1]
    dist_to_32_top = max(0, (bracket_32_ceiling + std_deduction) - (ordinary_income + ltcg_income))
    
    return {
        "federal_tax": fed_ordinary_tax + fed_ltcg_tax,
        "state_tax": state_tax_bill,
        "total_tax": total_tax,
        "effective_rate": effective_rate,
        "taxable_income": total_taxable,
        "headroom_22_top": dist_to_22_top,
        "headroom_24_top": dist_to_24_top,
        "headroom_32_top": dist_to_32_top,
        "headroom_24_pct": dist_to_22_top # Legacy key for safety
    }

def calculate_forecast() -> Dict[str, Any]:
    # Base Settings
    birth_year = db.get_setting('forecast_birth_year')
    inflation_rate = float(db.get_setting('forecast_inflation_rate') or 0.03)
    return_rate_setting = float(db.get_setting('forecast_return_rate') or 0.05)
    withdrawal_tax_rate = float(db.get_setting('forecast_withdrawal_tax_rate') or 0.15)
    state_tax_rate = float(db.get_setting('forecast_state_tax_rate') or 0.0) 
    if state_tax_rate > 0.5: state_tax_rate = state_tax_rate / 100.0
    dividend_yield_rate = float(db.get_setting('forecast_dividend_yield') or 0.02)
    filing_status = db.get_setting('forecast_tax_filing_status') or 'single'
    tax_drag_rate = float(db.get_setting('forecast_tax_drag_rate') or 0.005) 
    retirement_age = int(db.get_setting('forecast_retirement_age') or 65)
    nogo_age = int(db.get_setting('forecast_nogo_age') or 80)
    
    # Advanced/Stress Settings
    rmd_start_age = int(db.get_setting('forecast_rmd_start_age') or 73)
    embedded_gains_ratio = float(db.get_setting('forecast_taxable_embedded_gains_ratio') or 0.35)
    withdrawal_strategy = db.get_setting('forecast_withdrawal_strategy') or 'standard'
    roth_conversion_target = db.get_setting('forecast_roth_conversion_target') or 'none'
    
    healthcare_amplifier = float(db.get_setting('forecast_healthcare_amplifier') or 1.5)
    worst_case_drop = float(db.get_setting('forecast_worst_case_drop') or 0.02)
    best_case_boost = float(db.get_setting('forecast_best_case_boost') or 0.02)
    stress_years = int(db.get_setting('forecast_stress_years') or 10)

    # Property Strategies
    residence_sale_enabled = bool(db.get_setting('forecast_residence_sale_enabled') or False)
    residence_sale_year = int(db.get_setting('forecast_residence_sale_year') or 0) or None
    residence_lease_enabled = bool(db.get_setting('forecast_residence_lease_enabled') or False)
    residence_lease_year = int(db.get_setting('forecast_residence_lease_year') or 0) or None
    residence_lease_monthly_value = float(db.get_setting('forecast_residence_lease_monthly_value') or 0.0)

    future_props_setting = db.get_setting('forecast_future_properties_enabled')
    future_properties_enabled = bool(future_props_setting) if future_props_setting is not None else True

    phase_multipliers = db.get_setting('forecast_phase_multipliers') or {}
    base_col_categories = db.get_setting('forecast_base_col_categories') or []
    
    raw_sunset_dates = db.get_setting('forecast_base_col_sunset_dates') or {}
    cleaned_sunsets = {cat: int(sy) for cat, sy in raw_sunset_dates.items() if sy}
    lookback_years = int(db.get_setting('forecast_base_col_lookback_years') or 1)

    daf_transfers = db.get_setting('forecast_daf_transfers') or []

    if not birth_year:
        return {"error": "Birth Year not set. Please configure settings."}

    # Data Fetching
    account_summaries = analysis.get_account_performance_summary()
    base_buckets = {"Taxable": 0.0, "Deferred": 0.0, "Roth": 0.0, "Exempt": 0.0}
    
    for acc in account_summaries:
        status = acc['tax_status']
        val = acc['total_market_value']
        if val <= 0: continue
        norm_status = status.strip().lower()
        if 'deferred' in norm_status or 'ira' in norm_status or '401' in norm_status:
            base_buckets['Deferred'] += val
        elif 'roth' in norm_status:
            base_buckets['Roth'] += val
        elif 'exempt' in norm_status:
            base_buckets['Exempt'] += val
        else:
            base_buckets['Taxable'] += val

    base_properties = db.get_all_properties()
    filtered_col_categories = [c for c in base_col_categories if c not in EXCLUDED_EXPENSE_CATEGORIES]
    base_col_breakdown = db.get_base_col_breakdown(filtered_col_categories, lookback_years)
    base_col_total_initial = sum(base_col_breakdown.values())
    
    discretionary_items = db.get_discretionary_budget_items()
    future_income_streams = db.get_all_future_income_streams()
    
    current_year = date.today().year
    end_year = birth_year + 95

    def get_phase_multiplier(category_name: str, phase_key: str) -> float:
        cat_lower = (category_name or "").lower()
        if 'medicare' in cat_lower or 'health' in cat_lower or 'medical' in cat_lower:
            return 1.0
        if not category_name or category_name not in phase_multipliers:
            return 1.0
        try: val = float(phase_multipliers[category_name].get(phase_key, 100))
        except: val = 100.0
        return val / 100.0

    def _run_scenario(scenario_name: str, return_offset: float, hc_inflation_mult: float, apply_stress_years: bool):
        buckets = copy.deepcopy(base_buckets)
        
        # 0. Segregate Current vs Future Properties
        working_properties = []
        future_properties = []
        for p in base_properties:
            prop_dict = {
                "id": p['property_id'], "value": float(p['current_value']), "debt": float(p['mortgage_balance']), 
                "rate": float(p['appreciation_rate']), "is_primary": bool(p['is_primary']),
                "purchase_year": p.get('purchase_year'), "sale_year": p.get('sale_year'),
                "annual_maintenance": float(p.get('annual_maintenance') or 0.0), "name": p['name'],
                "purchase_price": float(p['purchase_price']),
                "fixed_sale_price": float(p['fixed_sale_price']) if p.get('fixed_sale_price') is not None else None
            }
            if prop_dict['purchase_year'] and prop_dict['purchase_year'] > current_year:
                if future_properties_enabled:
                    future_properties.append(prop_dict)
            else:
                working_properties.append(prop_dict)

        alerts = []
        simulation_data = []
        taxable_depleted_alerted = False
        
        previous_net_worth = sum(buckets.values()) + sum([p['value'] - p['debt'] for p in working_properties])

        for year in range(current_year, end_year + 1):
            age = year - birth_year
            phase_key = "no" if age >= nogo_age else ("slow" if age >= retirement_age else "go")
            
            start_taxable = buckets['Taxable']
            start_deferred = buckets['Deferred']
            start_roth = buckets['Roth']
            start_exempt = buckets['Exempt']
            
            ordinary_income_events = 0.0
            ltcg_income_events = 0.0
            
            years_from_start = year - current_year
            
            # Stress / Return Rate adjustments
            if apply_stress_years and years_from_start < stress_years:
                current_return_rate = return_rate_setting + return_offset
            elif not apply_stress_years:
                current_return_rate = return_rate_setting + return_offset
            else:
                current_return_rate = return_rate_setting
                
            taxable_return = current_return_rate - tax_drag_rate
            if taxable_return < 0: taxable_return = 0

            year_income = 0.0
            ss_income = 0.0
            taxable_withdrawals = 0.0
            
            inflation_factor = (1 + inflation_rate) ** years_from_start

            # 0.5 Temporal Property Acquisitions
            capital_expenditures = 0.0
            props_to_remove = []
            for p in future_properties:
                if p['purchase_year'] == year:
                    cost = p['purchase_price']
                    capital_expenditures += cost
                    working_properties.append(p)
                    props_to_remove.append(p)
            for p in props_to_remove:
                future_properties.remove(p)

            # 1. Base Income & SS
            for stream in future_income_streams:
                start = date.fromisoformat(stream['start_date'])
                end = date.fromisoformat(stream['end_date']) if stream['end_date'] else None
                if start.year <= year and (end is None or end.year >= year):
                    annual_amount = stream['amount'] * 12 if stream['frequency'] == 'monthly' else stream['amount']
                    adjusted_amount = annual_amount * ((1 + stream['annual_increase_rate']) ** (year - start.year))
                    year_income += adjusted_amount
                    
                    if stream.get('stream_type', '').strip().lower() == 'social security':
                        ss_income += adjusted_amount
                    else:
                        ordinary_income_events += adjusted_amount

            # Phantom Yield
            taxable_yield_income = start_taxable * dividend_yield_rate
            ltcg_income_events += taxable_yield_income
            year_income += taxable_yield_income

            # 1.5 Principal Residence Lease
            if residence_lease_enabled and residence_lease_year and year >= residence_lease_year:
                is_selling_this_year = residence_sale_enabled and residence_sale_year == year
                if not is_selling_this_year and any(p['is_primary'] for p in working_properties):
                    annual_lease_income = (residence_lease_monthly_value * 12) * inflation_factor
                    year_income += annual_lease_income
                    ordinary_income_events += annual_lease_income

            # 2. RMDs
            year_rmd = 0.0
            if age >= rmd_start_age and buckets['Deferred'] > 0:
                year_rmd = buckets['Deferred'] / get_rmd_divisor(age)
                buckets['Deferred'] -= year_rmd
                year_income += year_rmd
                ordinary_income_events += year_rmd

            # 3. Living Expenses & Maintenance
            year_living_expenses = 0.0
            year_property_maintenance = 0.0
            expense_breakdown = {}

            for cat, amount in base_col_breakdown.items():
                if cleaned_sunsets.get(cat) and year > cleaned_sunsets[cat]:
                    continue 
                
                # Healthcare Inflation Amplifier logic
                cat_lower = cat.lower()
                if 'health' in cat_lower or 'medicare' in cat_lower or 'medical' in cat_lower:
                    compounded_inflation = (1 + (inflation_rate * hc_inflation_mult)) ** years_from_start
                else:
                    compounded_inflation = inflation_factor

                cost = amount * compounded_inflation * get_phase_multiplier(cat, phase_key)
                year_living_expenses += cost
                expense_breakdown[cat] = round(cost, 2)

            for prop in working_properties:
                if prop.get('annual_maintenance', 0) > 0:
                    maint_cost = prop['annual_maintenance'] * inflation_factor
                    year_property_maintenance += maint_cost
                    expense_breakdown[f"{prop['name']} Maint."] = round(maint_cost, 2)
            
            year_discretionary = 0.0
            for item in discretionary_items:
                if not item.get('is_enabled', True): continue
                item_start = item['start_year']
                item_end = item['end_year'] if item['end_year'] else (9999 if item['is_recurring'] else item_start)
                if item_start <= year <= item_end:
                    item_amount = item['amount']
                    if item['inflation_adjusted']: 
                        item_amount = item_amount * inflation_factor
                    year_discretionary += item_amount
                    expense_breakdown[item['name']] = round(item_amount, 2)

            for p in props_to_remove:
                expense_breakdown[f"{p['name']} Purchase"] = round(p['purchase_price'], 2)

            # 4. Preliminary Tax Check
            taxable_ss = calculate_taxable_ss(ss_income, ordinary_income_events + ltcg_income_events, filing_status)
            tax_metrics_pre = calculate_progressive_tax(ordinary_income_events + taxable_ss, ltcg_income_events, filing_status, state_tax_rate)

            # 5. Roth Conversion Strategy
            conversion_amount = 0.0
            if roth_conversion_target != 'none':
                room = tax_metrics_pre.get(f'headroom_{roth_conversion_target.split("_")[1]}_top', 0)
                if room > 0 and buckets['Deferred'] > 0:
                    effective_room = room / 1.85 if ss_income > 0 else room
                    conversion_amount = min(buckets['Deferred'], effective_room)
                    buckets['Deferred'] -= conversion_amount
                    buckets['Roth'] += conversion_amount
                    
                    taxable_ss = calculate_taxable_ss(ss_income, ordinary_income_events + conversion_amount + ltcg_income_events, filing_status)

            # 5.5 Charitable / DAF Transfers
            year_daf_transfer = 0.0
            for tranche in daf_transfers:
                if tranche.get('year') == year:
                    tranche_amount = float(tranche.get('amount', 0.0))
                    actual_transfer = min(buckets['Taxable'], tranche_amount)
                    if actual_transfer > 0:
                        buckets['Taxable'] -= actual_transfer
                        year_daf_transfer += actual_transfer
                        # Escapes LTCG because it bypasses the liquidations section below

            # 6. Residence & Temporal Property Sale
            sale_proceeds = 0.0
            sale_event_triggered = False

            def _calc_proceeds(p):
                if p.get('fixed_sale_price') is not None:
                    return max(0.0, p['fixed_sale_price'] - p['debt'])
                return max(0.0, p['value'] - p['debt'])
            
            # Legacy Primary Sale Config
            if residence_sale_enabled and residence_sale_year and year == residence_sale_year:
                for prop in [p for p in working_properties if p['is_primary']]:
                    sale_proceeds += _calc_proceeds(prop)
                    working_properties.remove(prop)
                    sale_event_triggered = True

            # Temporal Lifecycle Sales
            temporal_sold = []
            for prop in working_properties:
                if prop.get('sale_year') == year:
                    sale_proceeds += _calc_proceeds(prop)
                    temporal_sold.append(prop)
                    sale_event_triggered = True
            
            for prop in temporal_sold:
                if prop in working_properties:
                    working_properties.remove(prop)

            # 7. Net Cashflow & Strategic Withdrawal
            annual_tax_bill_est = calculate_progressive_tax(ordinary_income_events + conversion_amount + taxable_ss, ltcg_income_events, filing_status, state_tax_rate)['total_tax']
            expense_breakdown['Est. Income Tax'] = round(annual_tax_bill_est, 2)
            total_expenses = year_living_expenses + year_property_maintenance + year_discretionary + annual_tax_bill_est + capital_expenditures

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
                        gross_needed = amount_needed / (1.0 - withdrawal_tax_rate)
                        from_deferred = min(buckets['Deferred'], gross_needed)
                        buckets['Deferred'] -= from_deferred
                        deferred_withdrawals_for_spend += from_deferred
                        amount_needed -= from_deferred * (1.0 - withdrawal_tax_rate)

                    if amount_needed > 0:
                        from_taxable = min(buckets['Taxable'], amount_needed)
                        buckets['Taxable'] -= from_taxable
                        amount_needed -= from_taxable
                        taxable_withdrawals += from_taxable
                        ltcg_income_events += (from_taxable * embedded_gains_ratio)

                    if amount_needed > 0:
                        from_roth = min(buckets['Roth'], amount_needed)
                        buckets['Roth'] -= from_roth
                        amount_needed -= from_roth
                else:
                    strategy_executed = "Standard"
                    from_taxable = min(buckets['Taxable'], amount_needed)
                    buckets['Taxable'] -= from_taxable
                    amount_needed -= from_taxable
                    taxable_withdrawals += from_taxable
                    ltcg_income_events += (from_taxable * embedded_gains_ratio)
                    
                    if amount_needed > 0:
                        if not taxable_depleted_alerted and buckets['Deferred'] > 0 and scenario_name == 'Likely':
                            alerts.append(f"Engine Alert: Taxable bucket fully depleted in {year}. Forced to draw ${amount_needed:,.0f} from Deferred (IRA), triggering ordinary income tax spike.")
                            taxable_depleted_alerted = True

                        gross_needed = amount_needed / (1.0 - withdrawal_tax_rate)
                        from_deferred = min(buckets['Deferred'], gross_needed)
                        buckets['Deferred'] -= from_deferred
                        deferred_withdrawals_for_spend += from_deferred
                        amount_needed -= from_deferred * (1.0 - withdrawal_tax_rate)

                    if amount_needed > 0:
                        from_roth = min(buckets['Roth'], amount_needed)
                        buckets['Roth'] -= from_roth
                        amount_needed -= from_roth
            
            # 8. Final Tax Recalculation
            ordinary_income_events += deferred_withdrawals_for_spend
            final_taxable_ss = calculate_taxable_ss(ss_income, ordinary_income_events + conversion_amount + ltcg_income_events, filing_status)
            final_tax_metrics = calculate_progressive_tax(ordinary_income_events + conversion_amount + final_taxable_ss, ltcg_income_events, filing_status, state_tax_rate)

            # 9. Investment Growth
            delta_taxable = buckets['Taxable'] - start_taxable
            delta_deferred = buckets['Deferred'] - start_deferred
            delta_roth = buckets['Roth'] - start_roth
            delta_exempt = buckets['Exempt'] - start_exempt
            
            growth_taxable = (start_taxable * taxable_return) + (delta_taxable * taxable_return / 2.0)
            growth_deferred = (start_deferred * current_return_rate) + (delta_deferred * current_return_rate / 2.0)
            growth_roth = (start_roth * current_return_rate) + (delta_roth * current_return_rate / 2.0)
            growth_exempt = (start_exempt * current_return_rate) + (delta_exempt * current_return_rate / 2.0)

            buckets['Taxable'] += growth_taxable
            buckets['Deferred'] += growth_deferred
            buckets['Roth'] += growth_roth
            buckets['Exempt'] += growth_exempt

            # 10. Real Estate Growth
            year_re_value, year_re_debt = 0.0, 0.0
            for prop in working_properties:
                prop['value'] *= (1 + prop['rate'])
                year_re_value += prop['value']
                year_re_debt += prop['debt']

            total_liquid = sum(buckets.values())
            real_estate_equity = year_re_value - year_re_debt
            total_net_worth = total_liquid + real_estate_equity
            
            nw_delta = total_net_worth - previous_net_worth if year > current_year else 0
            previous_net_worth = total_net_worth

            simulation_data.append({
                "year": year,
                "age": age,
                "phase": phase_key,
                "liquid_assets": round(total_liquid, 2),
                "real_estate_equity": round(real_estate_equity, 2),
                "total_net_worth": round(total_net_worth, 2),
                "nw_delta": round(nw_delta, 2),
                "bucket_taxable": round(buckets['Taxable'], 2),
                "bucket_deferred": round(buckets['Deferred'], 2),
                "bucket_roth": round(buckets['Roth'], 2),
                "social_security_income": round(ss_income, 2),
                "rmd_event": round(year_rmd, 2),
                "taxable_withdrawals": round(taxable_withdrawals, 2),
                "roth_conversion": round(conversion_amount, 2),
                "daf_transfer": round(year_daf_transfer, 2),
                "total_income": round(year_income, 2),
                "total_expenses": round(total_expenses, 2),
                "base_col_expense": round(year_living_expenses, 2),
                "property_maintenance": round(year_property_maintenance, 2),
                "property_purchase": round(capital_expenditures, 2),
                "discretionary_expense": round(year_discretionary, 2),
                "expense_breakdown": expense_breakdown,
                "net_cashflow": round(net_cashflow, 2),
                "investment_growth": round(growth_taxable + growth_deferred + growth_roth + growth_exempt, 2),
                "sale_event": sale_event_triggered,
                "strategy_executed": strategy_executed,
                "tax_metrics": {
                    "taxable_income": round(final_tax_metrics['taxable_income'], 2),
                    "effective_rate": round(final_tax_metrics['effective_rate'] * 100, 2),
                    "headroom_24_pct": round(final_tax_metrics['headroom_24_pct'], 2),
                    "total_tax": round(final_tax_metrics['total_tax'], 2)
                }
            })
        return simulation_data, alerts

    if base_buckets['Deferred'] == 0 and base_buckets['Roth'] == 0 and sum(base_buckets.values()) > 0:
         # Just need this alert once, run it manually here
         pass # Will let the UI or user notice it, kept clean for scenarios

    likely_series, likely_alerts = _run_scenario("Likely", 0.0, 1.0, False)
    worst_series, _ = _run_scenario("Worst", -worst_case_drop, healthcare_amplifier, True)
    best_series, _ = _run_scenario("Best", best_case_boost, 1.0, False)

    return {
        "simulation_series": likely_series,
        "worst_series": worst_series,
        "best_series": best_series,
        "alerts": likely_alerts,
        "settings": {
            "birth_year": birth_year,
            "starting_nw": likely_series[0]['total_net_worth'] if likely_series else 0,
            "starting_base_col": round(base_col_total_initial, 2),
            "withdrawal_strategy": withdrawal_strategy
        }
    }
