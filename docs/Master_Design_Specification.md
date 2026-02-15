# Curie Trust Financial Control Center
## Master Design Specification (MDS) v1.5

---

### 1. Overview
[... Unchanged ...]

### 2. System Architecture
[... Unchanged ...]

### 3. Core Modules

*   `src/data_model.py`: [...]
*   `src/database.py`: [...]
*   `src/importers/`: [...]
*   `src/rules_engine.py`: [...]
*   `src/market_data/`: [...]
*   `src/analysis.py`: Enhanced in v1.4.
*   `src/forecast.py`: **New Module**. Encapsulates the "Time Machine" simulation logic.
    *   `calculate_forecast()`: The core loop. Takes current NW, settings, and budget items. Returns a year-by-year list of projected values.

### 4. Data Model & Storage

*   **Database:** SQLite `data/trust.db`

**New Tables (v1.5):**
*   `discretionary_budget_items`:
    *   `item_id` (TEXT PK)
    *   `name` (TEXT)
    *   `amount` (REAL)
    *   `start_year` (INTEGER)
    *   `is_recurring` (INTEGER/BOOL)
    *   `inflation_adjusted` (INTEGER/BOOL)
*   `app_settings` (Existing): Will now store:
    *   `forecast_inflation_rate` (REAL, default 0.03)
    *   `forecast_return_rate` (REAL, default 0.05) - *New in v1.5*
    *   `forecast_birth_year` (INTEGER)
    *   `forecast_col_categories` (JSON list of category names)

### 5. API Interfaces

#### 5.3 Forecast API (New)
*   `GET /api/forecast/config`: Get inflation, birth year, return rate.
*   `PUT /api/forecast/config`: Update settings.
*   `GET /api/forecast/base-col`: Returns the calculated "Year 0" cost based on last 12 months of selected categories.
*   `POST /api/forecast/discretionary`: CRUD for budget items.
*   `GET /api/forecast/simulation`: Returns the projection series:
    *   `year`: 2024, 2025...
    *   `age`: 50, 51...
    *   `starting_net_worth`: Value at start of year.
    *   `income`: Total income for year (from Future Streams).
    *   `expenses`: Base CoL + Discretionary for year.
    *   `investment_growth`: Calculated growth on liquid assets.
    *   `ending_net_worth`: Value at end of year.

### 6. Security
[... Unchanged ...]

### 7. Phased Implementation Plan

*   **Phase 8:** Data Protection (Completed).
*   **Phase 9:** Forecast Planner (Next).