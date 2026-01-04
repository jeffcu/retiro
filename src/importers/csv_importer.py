import csv
import io
from datetime import datetime
from decimal import Decimal
import hashlib

from ..data_model import Transaction

def parse_standard_csv(file_contents: bytes, account_id: str) -> list[Transaction]:
    """
    Parses a standard CSV file with Date,Description,Amount columns.
    (PRS Section 5)
    """
    transactions = []
    file_stream = io.StringIO(file_contents.decode('utf-8'))
    reader = csv.DictReader(file_stream)

    for row in reader:
        # Basic data validation and cleaning
        try:
            transaction_date = datetime.strptime(row['Date'], '%Y-%m-%d').date()
            amount = Decimal(row['Amount'])
            description = row['Description']
        except (KeyError, ValueError) as e:
            print(f"Skipping row due to parsing error: {row} - {e}")
            continue

        # Create a unique ID for the transaction (PRS Section 8 - dedupe)
        # A simple hash of key fields is a good start.
        raw_data = f"{transaction_date}-{description}-{amount}-{account_id}"
        transaction_hash = hashlib.sha256(raw_data.encode('utf-8')).hexdigest()

        transactions.append(
            Transaction(
                transaction_id=transaction_hash,
                account_id=account_id,
                transaction_date=transaction_date,
                amount=amount,
                description=description,
                raw_data_hash=transaction_hash # Store for deduplication
            )
        )

    return transactions
