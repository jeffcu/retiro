# Curie Trust Financial Control Center
## Master Design Specification (MDS) v1.9.3

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
    *   *Upgrade 10.7:* `Property` requires new temporal fields: `purchase_year`, `sale_year`, `annual_maintenance`.
*   `src/database.py`: Handles all SQL operations, schema migrations, JSON settings, and the Tag Aggregation Engine.
*   `src/forecast.py`: **Major Upgrades in 10.6 & 10.7**.
    *   `TaxEngine` Class: Handles progressive tax calculations (Fed + State).
    *   `RMDCalculator` Class: Determines mandatory withdrawals.
    *   `SimulationEngine`: Includes withdrawal order strategies, dual real estate strategies, Embedded Capital Gains tracking, DAF/Charitable Transfer bypass logic, and **Temporal Property Lifecycles** (future buys/sells).

### 4. Data Model & Storage

*   **Database:** SQLite `data/trust.db`

**Schema Alterations (Phase 10.7):**
*   `properties` table requires columns: `purchase_year` (INTEGER), `sale_year` (INTEGER), `annual_maintenance` (REAL).

**Settings Keys (v1.9.3):**
*   `forecast_tax_filing_status`: 'single' | 'joint'
*   `forecast_withdrawal_strategy`: 'standard' | 'deferred_first'
*   `forecast_roth_conversion_target`: 'none' | 'fill_12' | 'fill_22' | 'fill_24' | 'fill_32'
*   `forecast_rmd_start_age`: INTEGER (Default 73)
*   `forecast_residence_lease_enabled`: BOOLEAN
*   `forecast_residence_lease_year`: INTEGER
*   `forecast_residence_lease_monthly_value`: FLOAT
*   `forecast_taxable_embedded_gains_ratio`: FLOAT 
*   `forecast_daf_transfers`: JSON ARRAY

### 5. API Interfaces

#### 5.3 Forecast API
*   `GET /api/forecast/simulation`: Returns `simulation_series`.
*   `GET /api/properties`: Updated to return temporal property lifecycle data.

### 6. Security
*   Local-only access.
*   API Keys stored in `.env`.

### 7. Phased Implementation Plan

*   **Phase 10.5:** Tax Physics Refinement - **Stable**.
*   **Phase 10.6:** Advanced Capital Evasion (DAFs) - **On Deck**.
*   **Phase 10.7:** Real Estate Lifecycle Engine - **On Deck**.
    1. Migrate `properties` table to include temporal fields.
    2. Update UI form to capture future dates and maintenance costs.
    3. Wire `forecast.py` to deduct purchase price from Taxable bucket in `purchase_year`.
    4. Wire `forecast.py` to add `annual_maintenance` to expenses during ownership window.
    5. Wire `forecast.py` to liquidate asset to Taxable bucket in `sale_year`.
*   **Phase 11:** Legacy & Liquidation View.