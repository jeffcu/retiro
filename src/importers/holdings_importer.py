import csv
import io
import hashlib
from decimal import Decimal, InvalidOperation
from typing import List, Tuple, Dict, Any

from ..data_model import Holding

def _normalize_header(header: str) -> str:
    """Cleans a CSV header for matching.""" 
    if not header:
        return ""
    # Lowercase, strip whitespace, remove spaces, and remove common special chars/suffixes
    return header.lower().strip().replace(' ', '').replace('($)', '').replace('_', '').replace('/', '')

def parse_holdings_csv(file_contents: bytes, account_id: str) -> Tuple[List[Holding], Dict[str, Any]]:
    """
    Parses a holdings CSV, dynamically mapping common column names to the internal model.
    Handles UTF-8 with BOM and various header naming conventions.
    Returns the holdings and a summary dictionary for auditing.
    """
    holdings = []
    try:
        file_stream = io.StringIO(file_contents.decode('utf-8-sig'))
    except UnicodeDecodeError:
        file_stream = io.StringIO(file_contents.decode('latin-1'))
        
    reader = csv.DictReader(file_stream)
    
    if not reader.fieldnames:
        print("Warning: Holdings CSV file is empty or has no headers.")
        return [], {}

    HEADER_ALIASES = {
        'symbol': ['symbol', 'symbolcusip', 'ticker'],
        'quantity': ['quantity', 'shares', 'units'],
        'cost_basis': ['costbasis', 'cost', 'totalcost', 'costbasis($)'],
        'market_value': ['marketvalue', 'value', 'totalvalue', 'value($)'],
    }

    header_map = {}
    original_fieldnames = reader.fieldnames
    normalized_to_original = { _normalize_header(h): h for h in original_fieldnames }

    for canonical_name, aliases in HEADER_ALIASES.items():
        for alias in aliases:
            if alias in normalized_to_original:
                header_map[canonical_name] = normalized_to_original[alias]
                break 

    required_fields = ['symbol', 'quantity']
    for field in required_fields:
        if field not in header_map:
            print(f"ERROR: Could not find a required column for '{field}' in CSV headers.")
            print(f"Available headers (normalized): {list(normalized_to_original.keys())}")
            return [], {}

    print(f"Mapped CSV headers: {header_map}")
    
    for row in reader:
        symbol_key = header_map.get('symbol')
        if not symbol_key or not row.get(symbol_key):
            continue

        try:
            symbol = row[symbol_key].strip().upper()
            if not symbol:
                continue

            quantity_key = header_map.get('quantity')
            raw_quantity = row.get(quantity_key, '0').strip().replace(',', '')
            quantity = Decimal(raw_quantity if raw_quantity and raw_quantity != '-' else '0')

            cost_basis_key = header_map.get('cost_basis')
            raw_cost_basis = row.get(cost_basis_key, '0').strip().replace(',', '').replace('$', '')
            cost_basis = Decimal(raw_cost_basis if raw_cost_basis and raw_cost_basis != '-' else '0')
            
            market_value = None
            market_value_key = header_map.get('market_value')
            if market_value_key and row.get(market_value_key):
                raw_market_value = row[market_value_key].strip().replace(',', '').replace('$', '')
                if raw_market_value and raw_market_value != '-':
                    market_value = Decimal(raw_market_value)
        
        except (InvalidOperation, ValueError, TypeError) as e:
            print(f"Skipping row due to data conversion error: {row} - {e}")
            continue

        raw_id = f"{account_id}-{symbol}"
        holding_id = hashlib.sha256(raw_id.encode('utf-8')).hexdigest()

        holding = Holding(
            holding_id=holding_id,
            account_id=account_id,
            symbol=symbol,
            quantity=quantity,
            cost_basis=cost_basis,
            market_value=market_value
        )
        holdings.append(holding)
    
    total_market_value = sum(h.market_value for h in holdings if h.market_value is not None)
    total_cost_basis = sum(h.cost_basis for h in holdings if h.cost_basis is not None)
    summary = {
        "record_count": len(holdings),
        "total_market_value": total_market_value,
        "total_cost_basis": total_cost_basis
    }

    return holdings, summary
