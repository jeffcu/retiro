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
    transaction_id: str  # A unique identifier, possibly a hash of the raw data.
    account_id: str
    transaction_date: date
    amount: Decimal
    description: str  # The original description from the financial institution.
    merchant: str | None = None  # Normalized merchant name.
    category: str | None = None
    cashflow_type: CashflowType | None = None
    tags: list[str] = field(default_factory=list)
    is_transfer: bool = False  # Derived from cashflow_type for quick filtering.

    # Link to other entities
    asset_id: str | None = None  # For CapEx transactions, linking to a specific asset.

    # Audit trail
    import_run_id: str | None = None
    raw_data_hash: str | None = None


@dataclass
class Holding:
    """
    Represents a single portfolio holding in a specific account.
    (PRS Section 8)
    """
    holding_id: str  # Unique ID, typically a hash of account_id and symbol.
    account_id: str
    symbol: str
    quantity: Decimal
    cost_basis: Decimal
    # Market data to be added in Phase 5
    last_price: Decimal | None = None
    last_price_timestamp: datetime | None = None
