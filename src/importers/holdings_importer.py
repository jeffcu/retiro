import csv
import io
import hashlib
from decimal import Decimal
from typing import List

from ..data_model import Holding

def parse_holdings_csv(file_contents: bytes, account_id: str) -> List[Holding]:
    """
    Parses a holdings CSV with Symbol, Quantity, CostBasis columns.
    (PRS Section 5.1)
    """
    holdings = []
    file_stream = io.StringIO(file_contents.decode('utf-8'))
    reader = csv.DictReader(file_stream)

    for row in reader:
        try:
            symbol = row['Symbol'].strip().upper()
            quantity = Decimal(row['Quantity'])
            cost_basis = Decimal(row['CostBasis'])
        except (KeyError, ValueError, TypeError) as e:
            print(f"Skipping row due to parsing error: {row} - {e}")
            continue

        # Create a unique, deterministic ID for the holding
        raw_id = f"{account_id}-{symbol}"
        holding_id = hashlib.sha256(raw_id.encode('utf-8')).hexdigest()

        holding = Holding(
            holding_id=holding_id,
            account_id=account_id,
            symbol=symbol,
            quantity=quantity,
            cost_basis=cost_basis
        )
        holdings.append(holding)
    
    return holdings
