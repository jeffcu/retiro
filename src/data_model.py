from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import Enum


class CashflowType(Enum):
    """ PRS Section 3.1: Mutually exclusive cashflow types. """
    INCOME = "Income"
    EXPENSE = "Expense"
    TRANSFER = "Transfer"
    CAPEX = "Capital Expenditure"


@dataclass
class Transaction:
    """
    Represents a single, normalized financial transaction based on the internal data model.
    See PRS Section 8.
    """
    transaction_id: str
    account_id: str
    transaction_date: date
    amount: Decimal
    description: str
    merchant: str | None = None
    category: str | None = None
    cashflow_type: CashflowType | None = None
    tags: list[str] = field(default_factory=list)
    is_transfer: bool = False
    asset_id: str | None = None
    import_run_id: str | None = None
    raw_data_hash: str | None = None
    institution: str | None = None
    original_category: str | None = None


@dataclass
class Holding:
    """
    Represents a single portfolio holding in a specific account.
    (PRS Section 8)
    """
    holding_id: str
    account_id: str
    symbol: str
    quantity: Decimal
    cost_basis: Decimal
    # UPDATED for Phase 4.5: Added market_value, populated from CSV or API
    market_value: Decimal | None = None
    last_price: Decimal | None = None
    last_price_timestamp: datetime | None = None
