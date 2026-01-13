from __future__ import annotations
import logging
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
    INVESTMENT = "Investment"

    @classmethod
    def from_string(cls, value: str | None) -> CashflowType | None:
        if not value:
            return None
        clean_value = value.strip().lower()
        for member in cls:
            if member.value.lower() == clean_value:
                return member
        logging.warning(f"Unknown CashflowType value: '{value}'. Treating as None.")
        return None


@dataclass
class Transaction:
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
    holding_id: str
    account_id: str
    symbol: str
    quantity: Decimal
    cost_basis: Decimal
    asset_type: str | None = None
    market_value: Decimal | None = None
    last_price: Decimal | None = None
    last_price_timestamp: datetime | None = None
    tags: list[str] = field(default_factory=list)


@dataclass
class PriceQuote:
    """ Represents a single price point fetched from an external API. """
    quote_id: str
    symbol: str
    price: Decimal
    quote_timestamp: datetime
    source: str | None = None
