# Curie Trust Financial Control Center
## Master Design Specification (MDS) v1.2

---

### 1. Overview

This document outlines the technical architecture for the Curie Trust Financial Control Center, a local-first desktop application designed for comprehensive financial tracking, analysis, and forecasting. The system ingests data from various financial institutions, normalizes it against an internal model, enriches it with market data via external APIs, and presents insights through a Sankey-forward user interface.

The prime directive is to answer three core questions with high clarity:
1.  What is our latest net worth (Liquid + Real Estate)?
2.  Where did our income go?
3.  What is our investment rate of return (gross, after fees, after taxes)?

### 2. System Architecture

The application will follow a simple, robust, local-first architecture.

*   **Backend:** A Python application responsible for all business logic, data processing, storage, and external API communication. This ensures deterministic calculations and direct control over the data pipeline.
*   **Frontend:** A web-based user interface (e.g., built with React or Vue) served locally by the Python backend. This allows for a modern, interactive UX without the complexities of a native GUI framework.
*   **Storage:** A single-file SQLite database for all persistent data. This provides transactional integrity and simplifies backup/restore operations.
*   **Communication:** The frontend will communicate with the backend via a local REST or WebSocket API.

```mermaid
graph TD
    A[User] --> B{Frontend (Web UI)};
    B <--> C{Backend API (Python/FastAPI)};
    C --> D[Business Logic];
    D <--> E[SQLite Database];
    D --> F(External APIs: Massive, Alphavantage);
    G[CSV/Spreadsheet Files] --> C;
```

### 3. Core Modules

The system is decomposed into the following distinct modules within the `src` directory:

*   `src/data_model.py`: Defines the core Python data structures (`Transaction`, `Holding`, `Property`, etc.) using dataclasses and Enums.
*   `src/database.py`: Manages all interaction with the SQLite database, including schema creation, CRUD operations, and transaction management.
*   `src/importers/`: A package for data ingestion. Contains parsers for different CSV formats and the logic for mapping, normalization, and deduplication.
*   `src/rules_engine.py`: Handles the logic for automatically categorizing transactions based on user-defined rules (e.g., merchant regex matching).
*   `src/market_data/`: A package for fetching external market data. Contains the provider interface and specific implementations for the Massive API and Alphavantage.
*   `src/analysis.py`: Contains functions for financial calculations, generating Sankey diagram data, calculating portfolio returns, and running forecasts.
*   `src/main.py` or `src/api.py`: The main application entry point. Runs the web server (e.g., FastAPI) and exposes the API endpoints for the frontend.

### 4. Data Model & Storage

*   **Database:** SQLite
*   **Location:** `data/trust.db` (within the project structure, but outside `src`)
*   **Schema:** The database schema will directly mirror the entities defined in `src/data_model.py` and the PRS Section 8.

**Key Tables:**
*   `transactions`: Stores all financial events (income, expense, transfer, capex).
*   `accounts`: Represents financial accounts (e.g., checking, credit card).
*   `assets`: Represents major abstract assets (legacy/future use).
*   `properties`: Stores Real Estate assets. Columns: `property_id` (PK), `name`, `purchase_price`, `mortgage_balance`, `current_value`, `appreciation_rate`, `is_primary`.
*   `holdings`: Stores portfolio positions (e.g., 100 shares of AAPL in Account X). Includes a `last_price_update_failed` flag for UI error reporting.
*   `price_history`: Caches historical and intraday price quotes for securities.
*   `rules`: Stores user-defined rules for transaction categorization.
*   `import_profiles`: Saves column mappings and settings for specific CSV formats.
*   `tax_year_facts`: Stores key data from annual tax returns to calculate after-tax returns. Contains columns like `tax_year` (PK), `filing_status`, `fed_taxable_income`, `fed_total_tax`, `state_taxable_income`, `state_total_tax`.
*   `future_income_streams`: Stores definitions for projected, recurring cashflows for forecasting (e.g., Social Security, RMDs).

### 5. API Interfaces

#### 5.1 Internal Backend API

The backend will expose RESTful endpoints for the frontend, such as:
*   `GET /api/net-worth`: Returns the latest calculated net worth.
*   `GET /api/sankey/income?period=YTD`: Returns data formatted for the Income->Uses Sankey.
*   `POST /api/import/csv`: Accepts a CSV file for ingestion.
*   `GET /api/properties`: Retrieves real estate records.
*   `POST /api/properties`: Adds a new property.
*   `PUT /api/properties/{id}`: Updates a property.

#### 5.2 External APIs

The system employs a multi-provider strategy for market data, orchestrated by the `polling_service`.

### 6. Security

As a local-first application, the primary security concerns are key management and data integrity.

*   **API Key Storage:** API keys (`MASSIVE_API_KEY`, `ALPHA_VANTAGE_API_KEY`) must not be hardcoded. They will be stored in a configuration file (`.env`) that is explicitly excluded from version control via `.gitignore`.
*   **Data Storage:** The `trust.db` SQLite file contains sensitive financial data. While encryption-at-rest is optional for v1.0, the design should accommodate a future implementation.
*   **Input Validation:** All data from imported files will be strictly validated and sanitized before being inserted into the database.
*   **No Inbound Network Access:** The application server will bind to `localhost` by default, ensuring it is not exposed to the local network.

### 7. Phased Implementation Plan

Development will follow the user-feature centric plan outlined in the PRS (Section 10).

*   **Phase 0-6:** Completed (Core pipeline, Sankey, Portfolio, Returns).
*   **Phase 7:** Retirement & Estate Forecasting (In Progress). Includes Real Estate logic integration.
