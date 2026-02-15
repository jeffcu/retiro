# Phase 9: Forecast Planner Verification Checklist

Use this checklist to manually verify the calculation engine of the "Time Machine" forecast.

## 1. Environment Setup
- [ ] **Data Check**: Ensure you have imported `transactions.csv` (for Base CoL actuals) and `holdings.csv` (for Net Worth).
- [ ] **Settings**: Go to the Forecast Settings UI (or use API `PUT /api/forecast/config`) and set:
    - Birth Year: e.g., 1975
    - Inflation Rate: 0.03 (3%)
    - Return Rate: 0.05 (5%)

## 2. Base Cost of Living (Actuals)
- [ ] **Select Categories**: Identify 2-3 specific expense categories (e.g., "Groceries", "Utilities") that have data in the last 12 months.
- [ ] **Run Verification**: 
    - Call `GET /api/forecast/base-col?categories=Groceries,Utilities`
    - **Verify**: The returned `base_col` matches the sum of those categories in your CSV for the last 12 months.

## 3. Discretionary Budget
- [ ] **Create Item**: Add a "World Tour" item:
    - Amount: 20,000
    - Start Year: Current Year + 5
    - Recurring: No
    - Inflation Adjusted: Yes
- [ ] **Verify Storage**: Call `GET /api/forecast/discretionary` and ensure the item exists.

## 4. Simulation Engine Logic
- [ ] **Run Simulation**: Call `GET /api/forecast/simulation`.
- [ ] **Verify Year 0**: 
    - `liquid_assets` should match your current Portfolio Value.
    - `real_estate_equity` should match your Properties (Value - Mortgage).
- [ ] **Verify Growth (Year 1)**:
    - Manually calculate: `Expected_Liquid = Current_Liquid * 1.05 + (Income - Expenses)`.
    - Compare against the API response for Year 1.
- [ ] **Verify Inflation**:
    - Check expenses in Year 10. 
    - Formula: `Base_CoL * (1.03)^10`.
- [ ] **Verify Drawdown**:
    - Set `Return Rate` to -0.10 (-10%) temporarily.
    - Run simulation.
    - **Verify**: The `liquid_assets` line drops significantly year-over-year.

## 5. Real Estate Appreciation
- [ ] **Setup**: Ensure you have a property with an appreciation rate (e.g., 0.03).
- [ ] **Verify**: In the simulation data, `real_estate_equity` should increase annually, independent of the portfolio return rate.
