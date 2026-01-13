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

def _clean_decimal(value_str: str, row_num: int, field_name: str, warnings: list) -> Decimal:
    """Safely converts a string to a Decimal, logging warnings and defaulting to 0 on failure."""
    if not value_str or not isinstance(value_str, str):
        return Decimal('0')
    
    cleaned = value_str.strip().replace(',', '').replace('$', '')
    if not cleaned or cleaned == '-':
        return Decimal('0')
        
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        warnings.append({
            "row_number": row_num,
            "field": field_name,
            "value": value_str,
            "message": "Could not parse value as a number; defaulted to 0."
        })
        return Decimal('0')

def parse_holdings_csv(file_contents: bytes, account_id: str) -> Tuple[List[Holding], Dict[str, Any], List[Dict], List[Dict]]:
    """
    Parses a holdings CSV, dynamically mapping common column names to the internal model.
    This version now aggregates data for duplicate symbols within the same file,
    summing quantity, cost basis, and market value.
    """
    holdings_map = {} # Use a dictionary to handle aggregation of duplicate symbols.
    skipped_rows = []
    warnings = []

    try:
        file_stream = io.StringIO(file_contents.decode('utf-8-sig'))
    except UnicodeDecodeError:
        file_stream = io.StringIO(file_contents.decode('latin-1'))
        
    reader = csv.DictReader(file_stream)
    
    if not reader.fieldnames:
        print("Warning: Holdings CSV file is empty or has no headers.")
        return [], {}, [], []

    HEADER_ALIASES = {
        'symbol': ['symbol', 'ticker', 'symbolcusip'],
        'quantity': ['quantity', 'shares', 'units'],
        'cost_basis': ['costbasis', 'cost', 'totalcost', 'costbasis($)'],
        'market_value': ['marketvalue', 'value', 'totalvalue', 'value($)'],
        'tags': ['tags', 'group', 'category'],
        'asset_type': ['assettype', 'type', 'assetclass', 'securitytypedescription'],
    }

    header_map = {}
    original_fieldnames = reader.fieldnames
    normalized_to_original = { _normalize_header(h): h for h in original_fieldnames }

    # CORRECTED: More flexible header matching logic.
    # Prioritize exact matches, then fall back to substring matches.
    for canonical_name, aliases in HEADER_ALIASES.items():
        found = False
        # 1. Try for an exact match of the normalized alias
        for alias in aliases:
            if alias in normalized_to_original:
                header_map[canonical_name] = normalized_to_original[alias]
                found = True
                break
        if found:
            continue

        # 2. If no exact match, fall back to substring matching
        for norm_header, orig_header in normalized_to_original.items():
            if any(alias in norm_header for alias in aliases):
                header_map[canonical_name] = orig_header
                break

    required_fields = ['symbol', 'quantity']
    for field in required_fields:
        if field not in header_map:
            err_msg = f"ERROR: Could not find a required column for '{field}' in CSV headers."
            print(err_msg)
            print(f"Available headers (normalized): {list(normalized_to_original.keys())}")
            # Return the error in the skipped_rows for visibility in the UI
            skipped_rows.append({"row_number": 1, "row_data": original_fieldnames, "reason": err_msg})
            return [], {}, skipped_rows, warnings

    print(f"Mapped CSV headers: {header_map}")
    
    for i, row in enumerate(reader):
        row_num = i + 2 # 1-based index for header, then data rows
        symbol_key = header_map.get('symbol')

        # A row is only skipped if its identifier (symbol) is missing.
        if not symbol_key or not row.get(symbol_key) or not row.get(symbol_key).strip():
            skipped_rows.append({"row_number": row_num, "row_data": row, "reason": "Symbol is missing or empty."})
            continue

        symbol = row[symbol_key].strip().upper()

        quantity_key = header_map.get('quantity')
        quantity = _clean_decimal(row.get(quantity_key, '0'), row_num, 'quantity', warnings)

        cost_basis_key = header_map.get('cost_basis')
        cost_basis = _clean_decimal(row.get(cost_basis_key, '0'), row_num, 'cost_basis', warnings)
        
        market_value = None
        market_value_key = header_map.get('market_value')
        if market_value_key and row.get(market_value_key):
            market_value = _clean_decimal(row.get(market_value_key), row_num, 'market_value', warnings)

        tags = []
        tags_key = header_map.get('tags')
        if tags_key and row.get(tags_key):
            tags = [t.strip() for t in row[tags_key].split(',') if t.strip()]

        asset_type = None
        asset_type_key = header_map.get('asset_type')
        if asset_type_key and row.get(asset_type_key):
            asset_type = row[asset_type_key].strip()

        # --- AGGREGATION LOGIC ---
        if symbol in holdings_map:
            # Aggregate data for the existing symbol
            existing_holding = holdings_map[symbol]
            existing_holding.quantity += quantity
            existing_holding.cost_basis += cost_basis
            if existing_holding.market_value is not None and market_value is not None:
                existing_holding.market_value += market_value
            elif market_value is not None:
                existing_holding.market_value = market_value
            
            # Merge tags, ensuring uniqueness
            existing_holding.tags = list(set(existing_holding.tags) | set(tags))
            # First non-empty asset type wins
            if asset_type and not existing_holding.asset_type:
                 existing_holding.asset_type = asset_type
            
            warnings.append({
                "row_number": row_num,
                "field": "symbol",
                "value": symbol,
                "message": "Duplicate symbol found; values were aggregated."
            })
        else:
            # Create a new holding entry
            raw_id = f"{account_id}-{symbol}"
            holding_id = hashlib.sha256(raw_id.encode('utf-8')).hexdigest()
            
            holdings_map[symbol] = Holding(
                holding_id=holding_id,
                account_id=account_id,
                symbol=symbol,
                quantity=quantity,
                cost_basis=cost_basis,
                market_value=market_value,
                tags=tags,
                asset_type=asset_type
            )

    holdings = list(holdings_map.values())
    
    total_market_value = sum(h.market_value for h in holdings if h.market_value is not None)
    total_cost_basis = sum(h.cost_basis for h in holdings if h.cost_basis is not None)
    summary = {
        "record_count": len(holdings),
        "total_market_value": total_market_value,
        "total_cost_basis": total_cost_basis
    }

    return holdings, summary, skipped_rows, warnings
