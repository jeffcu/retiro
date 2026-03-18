import sys
import os
from pathlib import Path

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# 1. Hijack the database path to point to the Demo Matrix
import src.database as db
demo_db_path = Path(project_root) / "demo_data" / "trust_demo.db"

if not demo_db_path.exists():
    print("CRITICAL: Calibration Matrix not found. Run build_demo_db.py first.")
    sys.exit(1)

# Override the engine's target file BEFORE importing the forecast engine
db.DB_FILE = demo_db_path

from src import forecast
from src import analysis

def run_verification():
    print(f"--- Initiating Forecast Verification against {demo_db_path.name} ---")
    
    # 1. Verify Pre-Simulation Mass (The True Start)
    account_summaries = analysis.get_account_performance_summary()
    starting_liquid = sum(acc['total_market_value'] for acc in account_summaries)
    starting_re = db.get_total_real_estate_equity()
    starting_nw = starting_liquid + starting_re

    # 2. Execute the Simulation
    result = forecast.calculate_forecast()
    
    if "error" in result:
        print(f"ENGINE FAILURE: {result['error']}")
        sys.exit(1)
        
    likely_series = result["simulation_series"]
    settings = result["settings"]
    
    year_0 = likely_series[0] # End of Current Year (0 years inflation)
    year_1 = likely_series[1] # End of Future Year 1 (3% inflation + Vacation)
    
    # 3. Assert Deterministic Physics
    print("\n[Verifying Pre-Simulation Initial Mass]")
    
    expected_liquid = 1500000.00
    expected_equity = 1000000.00
    expected_nw = 2500000.00
    expected_col = 72000.00
    
    liquid_pass = abs(starting_liquid - expected_liquid) < 0.01
    equity_pass = abs(starting_re - expected_equity) < 0.01
    nw_pass = abs(starting_nw - expected_nw) < 0.01
    col_pass = abs(settings['starting_base_col'] - expected_col) < 0.01
    
    print(f"Liquid Assets:   ${starting_liquid:,.2f} | Expected: ${expected_liquid:,.2f} -> {'✅' if liquid_pass else '❌'}")
    print(f"Real Estate Eq:  ${starting_re:,.2f} | Expected: ${expected_equity:,.2f} -> {'✅' if equity_pass else '❌'}")
    print(f"Total Net Worth: ${starting_nw:,.2f} | Expected: ${expected_nw:,.2f} -> {'✅' if nw_pass else '❌'}")
    print(f"Base Living (Yr):${settings['starting_base_col']:,.2f} | Expected: ${expected_col:,.2f} -> {'✅' if col_pass else '❌'}")

    print("\n[Verifying Current Year Trajectory (Year 0)]")
    
    expected_y0_nw = 2547054.00
    expected_y0_exp = 84400.00
    expected_y0_grw = 85454.00

    y0_nw_pass = abs(year_0['total_net_worth'] - expected_y0_nw) < 0.01
    y0_exp_pass = abs(year_0['total_expenses'] - expected_y0_exp) < 0.01
    y0_grw_pass = abs(year_0['investment_growth'] - expected_y0_grw) < 0.01

    print(f"Year 0 Net Worth: ${year_0['total_net_worth']:,.2f} | Expected: ${expected_y0_nw:,.2f} -> {'✅' if y0_nw_pass else '❌'}")
    print(f"Year 0 Expenses:  ${year_0['total_expenses']:,.2f} | Expected: ${expected_y0_exp:,.2f} -> {'✅' if y0_exp_pass else '❌'}")
    print(f"Year 0 Growth:    ${year_0['investment_growth']:,.2f} | Expected: ${expected_y0_grw:,.2f} -> {'✅' if y0_grw_pass else '❌'}")

    print("\n[Verifying Future Trajectory (Year 1)]")
    
    expected_y1_nw = 2576666.19
    expected_y1_exp = 102330.84
    expected_y1_grw = 85841.95

    y1_nw_pass = abs(year_1['total_net_worth'] - expected_y1_nw) < 0.01
    y1_exp_pass = abs(year_1['total_expenses'] - expected_y1_exp) < 0.01
    y1_grw_pass = abs(year_1['investment_growth'] - expected_y1_grw) < 0.01

    print(f"Year 1 Net Worth: ${year_1['total_net_worth']:,.2f} | Expected: ${expected_y1_nw:,.2f} -> {'✅' if y1_nw_pass else '❌'}")
    print(f"Year 1 Expenses:  ${year_1['total_expenses']:,.2f} | Expected: ${expected_y1_exp:,.2f} -> {'✅' if y1_exp_pass else '❌'}")
    print(f"Year 1 Growth:    ${year_1['investment_growth']:,.2f} | Expected: ${expected_y1_grw:,.2f} -> {'✅' if y1_grw_pass else '❌'}")
    
    if all([liquid_pass, equity_pass, nw_pass, col_pass, y0_nw_pass, y0_exp_pass, y0_grw_pass, y1_nw_pass, y1_exp_pass, y1_grw_pass]):
        print("\nSUCCESS: The Forecast Engine's mathematical baseline and temporal acceleration are perfectly anchored.")
    else:
        print("\nWARNING: Hull breach detected in mathematical aggregation. Logic has drifted.")
        sys.exit(1)

if __name__ == "__main__":
    run_verification()
