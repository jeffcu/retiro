# Curie Trust Financial Control Center
## Master Design Specification (MDS) v1.9

---

### 1. Overview
The Curie Trust Financial Control Center is a local-first, privacy-centric application designed to aggregate, visualize, and forecast the financial health of the Curie Trust. It operates on a Python/FastAPI backend with a React/Vite frontend, storing data in a local SQLite database.

### 2. System Architecture
*   **Backend:** Python 3.11+ (FastAPI, Pandas, SQLite).
*   **Frontend:** React 18 (Vite, Nivo Charts).
*   **Data Store:** `data/trust.db` (SQLite).
*   **Market Data:** Massive (Primary), AlphaVantage (Secondary).

### 3. Core Modules

*   `src/data_model.py`: Defines core data classes (Transaction, Holding, Property).
*   `src/database.py`: Handles all SQL operations, schema migrations, JSON settings, and the Tag Aggregation Engine.
*   `src/forecast.py`: **Major Upgrade in Phase 10**.
    *   `TaxEngine` Class: Handles progressive tax calculations (Fed + State).
    *   `RMDCalculator` Class: Determines mandatory withdrawals based on IRS tables.
    *   `SimulationEngine`: Now includes configurable withdrawal order strategies.

### 4. Data Model & Storage

*   **Database:** SQLite `data/trust.db`

**New Settings Keys (v1.9):**
*   `forecast_tax_filing_status`: 'single' | 'joint'
*   `forecast_withdrawal_strategy`: 'standard' | 'deferred_first' (Added in v1.9.1)
*   `forecast_roth_conversion_target`: 'none' | 'fill_12' | 'fill_22' | 'fill_24' | 'fill_32'
*   `forecast_rmd_start_age`: INTEGER (Default 75)

### 5. API Interfaces

#### 5.3 Forecast API (Updated for Phase 10)
*   `GET /api/forecast/simulation`: Returns `simulation_series` with new fields:
    *   `taxable_income`: Total income subject to tax (RMDs + SS + Withdrawals + Conversions).
    *   `federal_tax_paid`: Estimated federal tax bill.
    *   `effective_tax_rate`: `federal_tax_paid / taxable_income`.
    *   `rmd_amount`: The mandatory distribution amount for that year.
    *   `withdrawal_strategy_used`: The logic applied for that year (e.g. "IRA First").

#### 5.4 Tag Engine API (New)
*   `GET /api/tags/summary`: Returns aggregated counts and monetary volumes for all tags across transactions and holdings.
*   `GET /api/tags/{tag_name}/records`: Returns exact records (transactions and holdings) matching a specific tag.

### 6. Security
*   Local-only access.
*   API Keys stored in `.env`.

### 7. Phased Implementation Plan

*   **Phase 9:** Forecast Planner (Base Simulation) - **Completed/Stable**.

*   **Phase 10:** The Strategic Tax Engine (UI Specification) - **Next**.
    
    **A. New UI Component: `TaxStrategyConfig`**
    *   **Location:** Forecast View Grid.
    *   **Inputs:**
        1.  **Filing Status:** Toggle [Single | Joint].
        2.  **Withdrawal Order:** [Standard (Taxable First) | Legacy Saver (IRA First)].
        3.  **Strategy:** Dropdown for Roth Conversions.
    
    **B. New Visualization: `TaxExposureChart`**
    *   Visualizes Income vs. Tax Brackets over time.

*   **Phase 11:** Legacy & Liquidation View.
    1.  Add "After-Tax Net Worth" calculation.
    2.  Visualize the efficiency of different asset buckets for heirs.