# Phase 10.7: Real Estate Lifecycle Engine Implementation

## 1. Data Model & Database Architecture
**Files to Modify:** 
* `projects/trust/src/data_model.py`
* `projects/trust/src/database.py`

**Action Items:**
* In `data_model.py`, update the `Property` dataclass to include:
  * `purchase_year: Optional[int] = None`
  * `sale_year: Optional[int] = None`
  * `annual_maintenance: Decimal = Decimal('0.0')`
* In `database.py` (`_ensure_schema`), add these three columns to the `properties` table definition (`INTEGER` for the years, `REAL` for maintenance).
* Add a schema migration block in `_ensure_schema` to `ALTER TABLE properties ADD COLUMN...` for the new fields so existing databases don't crash.
* Update `create_property` and `update_property` to insert/update these new fields.

## 2. API Layer
**Files to Modify:** 
* `projects/trust/src/main.py`

**Action Items:**
* Update the `PropertyCreate` Pydantic model to include `purchase_year`, `sale_year`, and `annual_maintenance` (all optional, with maintenance defaulting to 0).
* Ensure these fields map correctly into the `Property` object creation inside the `/api/properties` POST and PUT endpoints.

## 3. UI Presentation Layer
**Files to Modify:** 
* `projects/trust/src/components/RealEstateView.jsx`

**Action Items:**
* Update `initialForm` state to include `purchase_year: ''`, `sale_year: ''`, and `annual_maintenance: 0`.
* Add three new input fields to the property form grid to capture these values.
* Update `PropertyCard` to cleanly display the Purchase Year, Sale Year (if set), and Annual Maintenance alongside the existing details.

## 4. The Temporal Forecast Engine (The Crown Jewel)
**Files to Modify:** 
* `projects/trust/src/forecast.py`

**Action Items:**
* **Initialization:** When building `working_properties` before the simulation loop, *exclude* any property where `purchase_year` is greater than the `current_year`. 
* **The Purchase Event:** Inside the main simulation loop (for each `year`), check the `base_properties` list. If a property's `purchase_year == year`, deduct its `purchase_price` from `buckets['Taxable']` (triggering normal net cashflow math) and append the property to `working_properties`.
* **Maintenance Drag:** While iterating through expenses, loop through current `working_properties`. Add `prop['annual_maintenance'] * inflation_factor` to `year_living_expenses`. Record this in the `expense_breakdown` under the property's name (e.g., `f"{prop['name']} Maintenance"`).
* **Liquidation Event:** During the Residence Sale check step, add logic for *all* `working_properties`. If `prop['sale_year'] == year`, calculate its equity (`value - debt`), add that equity to `sale_proceeds`, and remove the property from `working_properties`. 

*Note for @N1: Ensure the progressive tax calculation properly accounts for these massive capital movements by funneling them through the existing net cashflow logic.*