# Trust Financial System

**A Local-First, Open Source Financial Control Center & Retirement Forecasting Engine.**

## 🎯 Mission

The Trust Financial System is a privacy-centric application designed for **retirees and serious financial planners** who demand high-fidelity modeling without sacrificing data sovereignty.

Unlike commercial aggregators that scrape your passwords and sell your data, **Trust** runs entirely on your local machine. You import your own ledgers; the system enriches them with live market data to answer the critical questions of retirement:

1.  **Will the capital last?** (Modeling market conditions against spending needs)
2.  **How do life phases impact our runway?** (Transitioning from "Go" years to "Slow Go" and "No Go" years)
3.  **Are we tax-optimized?** (Visualizing the impact of RMDs, Roth conversions, and specific withdrawal orders)
4.  **What is our True Net Worth?** (Liquid Assets + Real Estate Equity - Liabilities)

**This project is Open Source.** We offer this codebase so you can build your own *private* financial planning system, audit the logic yourself, and expand it to handle scenarios unique to your life.

---

## 👤 The Ideal User

This system is built for the **hands-on planner**.

*   **You value privacy above convenience.** You prefer uploading CSVs once a month over giving a third-party app your bank login credentials.
*   **You want "Live" Net Worth.** While you manage the transaction history, the system automatically pulls end-of-day stock and bond prices to keep your portfolio value current.
*   **You are planning complex scenarios.** You need to model selling a primary residence in 2030, paying for a wedding in 2032, or funding long-term care in 2045.
*   **You care about Tax Drag.** You want to see how drawing from your IRA vs. your Brokerage account affects your long-term survival rate.
*   **No cost to operate.** Market updates use a slow drip strategy to stay under the pay levels for market prices. Add free API keys from Massive and/or AlphaVantage to enable the free daily price refresh after market close, and a mid-day refresh of your top 25 holdings.

---

## 🚀 Key Features

### 1. "The Time Machine" Forecast Engine
*   **Life Phase Modeling:** distinct spending multipliers for your "Go" (Active), "Slow Go" (Aging), and "No Go" (Late stage) years.
*   **Strategic Levers:** Toggle "Roth Conversion" strategies to fill low tax brackets.
*   **Real Estate Logic:** Model the sale of a primary residence and the subsequent liquidity event.
*   **Event Injection:** Schedule one-time large expenses (Weddings, Gifts) or recurring future costs (Caregivers, Retirement Homes).
*   **Tax Awareness:** Automatically calculates Required Minimum Distributions (RMDs) and applies progressive tax brackets to your withdrawals.

### 2. The Bridge (Dashboard)
*   **Real-Time Net Worth:** Aggregates portfolio holdings and real estate equity.
*   **Asset Allocation:** Visualizes exposure across asset classes.
*   **Tax Status Breakdown:** Tracks assets by tax bucket (Taxable, Deferred, Roth, Exempt).

### 3. Capital Flow Analysis
*   **Sankey Diagrams:** A visual flow of money from Income → Allocations → Expenses.
*   **Tabular Breakdown:** Detailed categorization of inflows and outflows.

### 4. Portfolio Performance
*   **Waterfall Analysis:** Breaks down performance into Contributions, Yield, Withdrawals, Fees, and Market Growth.
*   **Layered Returns:** Calculates Gross Return → Net of Fees → Net of Taxes.

---

## 🛠️ Setup & Installation

### Prerequisites
- Python 3.11 or higher
- Node.js 18 or higher
- Git

### 1. Clone the Repository
```bash
git clone https://github.com/your-username/trust.git
cd trust/projects/trust
```

### 2. Configure Environment
Create a `.env` file in the `projects/trust` directory:
```bash
cp .env.example .env
```
Edit `.env` and add your API keys (optional, but required for live market updates):
```ini
MASSIVE_API_KEY="your_key_here"
ALPHA_VANTAGE_API_KEY="your_key_here"
```

### 3. Launch the Development Environment
We provide a unified startup script that spins up both the Python backend and React frontend:

```bash
./scripts/start_dev_environment.sh
```

*   **Frontend:** http://localhost:5173
*   **Backend API:** http://localhost:8000/docs

---

## 🧪 Trying the Demo Dataset (The Calibration Matrix)

If you want to explore the system's features without uploading your own personal data, we provide a mathematically perfect test dataset featuring a fictional 55-year-old user with a $2.5M net worth.

1. Ensure the system is running.
2. In a separate terminal, generate the demo database:
   ```bash
   python scripts/build_demo_db.py
   ```
3. Navigate to **Data & Settings** in the application.
4. Under **System Backup & Restore**, select the newly created `demo_data/trust_demo.db` file and click **Restore**.

---

## 📂 Usage Guide

### Importing Data
1.  Navigate to the **Data & Settings** view.
2.  **Transactions:** Upload CSVs from your bank. The system uses a flexible importer that attempts to auto-detect columns.
3.  **Holdings:** Upload CSVs of your investment positions (Symbol, Quantity, Cost Basis).

### Categorization Rules
The system includes a regex-based Rules Engine. You can create rules in the **Cashflow** view to automatically tag and categorize transactions based on merchant names, amounts, or descriptions.

### Forecasting
Navigate to **Forecast**. Adjust the "Flight Controls" (Inflation, Return Rate, Retirement Age) to simulate different futures. Use **Discretionary Budget** to add one-time expenses (e.g., "Wedding in 2030").

---

## 🤝 Contributing

This project is open source to encourage private financial sovereignty. Pull requests are welcome. If you find a bug in the tax calculation logic or want to add a new importer for a specific brokerage, please open an issue.
