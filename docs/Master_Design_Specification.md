# Curie Trust Financial Control Center
## Master Design Specification (MDS) v1.1

---

### 1. Overview

This document outlines the technical architecture for the Curie Trust Financial Control Center, a local-first desktop application designed for comprehensive financial tracking, analysis, and forecasting. The system ingests data from various financial institutions, normalizes it against an internal model, enriches it with market data via external APIs, and presents insights through a Sankey-forward user interface.

The prime directive is to answer three core questions with high clarity:
1.  What is our latest net worth?
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

*   `src/data_model.py`: Defines the core Python data structures (`Transaction`, `Holding`, etc.) using dataclasses and Enums.
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
*   `assets`: Represents major assets, primarily for tracking basis (e.g., 'Main Residence').
*   `holdings`: Stores portfolio positions (e.g., 100 shares of AAPL in Account X). Includes a `last_price_update_failed` flag for UI error reporting.
*   `price_history`: Caches historical and intraday price quotes for securities.
*   `rules`: Stores user-defined rules for transaction categorization.
*   `import_profiles`: Saves column mappings and settings for specific CSV formats.

### 5. API Interfaces

#### 5.1 Internal Backend API

The backend will expose RESTful endpoints for the frontend, such as:
*   `GET /api/net-worth`: Returns the latest calculated net worth.
*   `GET /api/sankey/income?period=YTD`: Returns data formatted for the Income->Uses Sankey.
*   `POST /api/import/csv`: Accepts a CSV file for ingestion.
*   `GET /api/transactions?category=Travel`: Retrieves transactions based on filters.
*   `PUT /api/transaction/{id}`: Updates a single transaction (e.g., manual re-categorization).

#### 5.2 External APIs

The system employs a multi-provider strategy for market data, orchestrated by the `polling_service`.

**Provider 1: Massive API**
*   **Usage:** Primary provider for assets of type `Common Stock`.
*   **Authentication:** API Key (`MASSIVE_API_KEY`).
*   **Module:** `src/market_data/massive_provider.py`

**Provider 2: Alphavantage**
*   **Usage:** Primary provider for assets of type `Mutual Fund Open` and `Mutual Fund Closed`.
*   **Authentication:** API Key (`ALPHA_VANTAGE_API_KEY`).
*   **Module:** `src/market_data/alphavantage_provider.py`

**Implementation Details:**
*   The `polling_service` determines which provider to use based on the `asset_type` of a holding.
*   To respect all provider rate limits, the service will enforce a 12-second delay between individual API calls, regardless of the provider used.
*   The polling algorithm from PRS Section 6.3 is implemented in the `polling_service` and orchestrated by the `market_scheduler`.
*   All API responses are cached in the `price_history` table. The `holdings` table is updated with the latest price and a status flag indicating success or failure of the last attempt.

### 6. Security

As a local-first application, the primary security concerns are key management and data integrity.

*   **API Key Storage:** API keys (`MASSIVE_API_KEY`, `ALPHA_VANTAGE_API_KEY`) must not be hardcoded. They will be stored in a configuration file (`.env`) that is explicitly excluded from version control via `.gitignore`.
*   **Data Storage:** The `trust.db` SQLite file contains sensitive financial data. While encryption-at-rest is optional for v1.0, the design should accommodate a future implementation.
*   **Input Validation:** All data from imported files will be strictly validated and sanitized before being inserted into the database.
*   **No Inbound Network Access:** The application server will bind to `localhost` by default, ensuring it is not exposed to the local network.

### 7. Phased Implementation Plan

Development will follow the user-feature centric plan outlined in the PRS (Section 10).

*   **Phase 0: The Walking Skeleton (Completed)**
    *   Goal: Prove the end-to-end data pipeline is viable.

*   **Phase 1: The Dynamic Sankey (Completed)**
    *   Goal: Visualize real, user-imported data in the primary Sankey chart.

*   **Phase 2: Interactive Drill-Downs & Rules Management (Completed)**
    *   Goal: Allow users to inspect their data and manage categorization.

*   **Phase 3: Introducing Capital Expenditures (CapEx) (Completed)**
    *   Goal: Differentiate consumption expenses from asset-building expenses.

*   **Phase 4: The Portfolio View (Completed)**
    *   Goal: Establish initial portfolio tracking.

*   **Phase 5: Automated Market Data & Layered Returns (In Progress)**
    *   Goal: Automate portfolio pricing using a multi-provider strategy and introduce advanced return metrics.

*   **Phase 6: Forecasting**
    *   Goal: Provide future-looking financial projections.
