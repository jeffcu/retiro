import csv
import io
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
import hashlib
from typing import List, Tuple, Optional, Dict, Any

from ..data_model import Transaction
from ..rules_engine import apply_rules_to_transaction, load_rules_from_db

def _normalize_header(header: str) -> str:
    """Cleans a CSV header for matching by making it lowercase and removing noise."""
    if not header:
        return ""
    return re.sub(r'[^a-z0-9]', '', header.lower().strip())

def _find_header_row(lines: List[str]) -> Optional[Tuple[List[str], int]]:
    """
    Scans the first few lines of a CSV to find the most plausible header row.
    A good header should contain keywords like 'date', 'description', and 'amount'.
    Returns the header row and its index.
    """
    CANDIDATE_KEYWORDS = {'date', 'description', 'amount', 'category'}
    
    # Use csv.reader to handle quoted fields correctly during scanning
    reader = csv.reader(lines[:15]) # Scan up to 15 lines
    for i, row in enumerate(reader):
        if not row or not any(row): # Skip empty/blank rows
            continue
            
        normalized_row = {_normalize_header(h) for h in row}
        
        found_keywords_count = 0
        for keyword in CANDIDATE_KEYWORDS:
            for norm_h in normalized_row:
                if keyword in norm_h:
                    found_keywords_count += 1
                    break # Don't count same keyword twice

        if found_keywords_count >= 2:
            return row, i
            
    print("Warning: Could not automatically detect a header row. Returning None.")
    return None

def _clean_amount(amount_str: str) -> Decimal:
    """
    Cleans a currency string into a Decimal, handling symbols, commas, and parentheses.
    """
    if not isinstance(amount_str, str) or not amount_str.strip():
        return Decimal('0')
    
    cleaned_str = amount_str.strip()
    if cleaned_str.startswith('(') and cleaned_str.endswith(')'):
        cleaned_str = '-' + cleaned_str[1:-1]
        
    # CORRECTED: This now removes non-numeric characters, preserving digits, dots, and minus signs.
    cleaned_str = re.sub(r'[^\d.-]', '', cleaned_str)
    
    try:
        return Decimal(cleaned_str) if cleaned_str and cleaned_str != '.' and cleaned_str != '-' else Decimal('0')
    except InvalidOperation:
        print(f"Warning: Could not convert amount '{amount_str}' to a number. Treating as zero.")
        return Decimal('0')

def parse_standard_csv(file_contents: bytes, account_id_fallback: str) -> Tuple[list[Transaction], Dict[str, Any]]:
    """
    Parses a transaction CSV with flexible headers for Date, Description, Amount, and more.
    Prioritizes data from the CSV (like account name) over form-submitted data.
    Returns the transactions and a summary dictionary for auditing.
    """
    transactions = []
    
    try:
        content_str = file_contents.decode('utf-8-sig')
    except UnicodeDecodeError:
        content_str = file_contents.decode('latin-1')
    
    lines = content_str.splitlines()
    if not lines:
        print("ERROR: CSV file is empty.")
        return [], {}

    header_info = _find_header_row(lines)
    
    if header_info:
        header_row, header_index = header_info
        data_lines = lines[header_index + 1:]
    else:
        # Fallback: assume first non-empty line is the header
        for i, line in enumerate(lines):
            if line.strip():
                header_row = next(csv.reader([line]))
                data_lines = lines[i + 1:]
                print(f"Fallback: Assuming first non-empty row is the header: {header_row}")
                break
        else:
             print("ERROR: CSV file contains no data rows.")
             return [], {}
    
    if not header_row:
        print("ERROR: Could not determine header row.")
        return [], {}

    reader = csv.DictReader(data_lines, fieldnames=header_row)

    rules = load_rules_from_db()
    print(f"Loaded {len(rules)} rules for categorization.")

    HEADER_ALIASES = {
        'date': ['date', 'posted', 'transactiondate'],
        'description': ['description', 'payee', 'merchant', 'details'],
        'amount': ['amount', 'price'],
        'category': ['category', 'type'],
        'institution': ['firmname', 'institution', 'firm', 'firm name'],
        'account_name': ['accountname', 'account', 'account name'],
    }
    
    header_map = {}
    normalized_to_original = {_normalize_header(h): h for h in header_row if h}

    for canonical_name, aliases in HEADER_ALIASES.items():
        for alias in aliases:
            # Normalize the alias for comparison
            norm_alias = _normalize_header(alias)
            if norm_alias in normalized_to_original:
                header_map[canonical_name] = normalized_to_original[norm_alias]
                break
            # Fallback for direct matching
            for norm_header, orig_header in normalized_to_original.items():
                if alias in norm_header:
                    header_map[canonical_name] = orig_header
                    break
            if canonical_name in header_map:
                break
    
    required_fields = ['date', 'description', 'amount']
    missing_fields = [f for f in required_fields if f not in header_map]
    if missing_fields:
        print(f"ERROR: Could not find required columns for: {missing_fields}.")
        print(f"Available headers: {header_row}")
        return [], {}
    
    print(f"CSV Importer mapped headers: {header_map}")

    imported_count, skipped_count = 0, 0
    for row in reader:
        if None in row:
            print(f"Skipping malformed row with extra columns: {row[None]}")
            skipped_count += 1
            continue

        try:
            date_str = row.get(header_map['date'])
            description = row.get(header_map['description'], '').strip()
            amount_str = row.get(header_map['amount'])

            if not all([date_str, description, amount_str]):
                skipped_count += 1
                continue

            try:
                transaction_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                transaction_date = datetime.strptime(date_str, '%m/%d/%Y').date()

            amount = _clean_amount(amount_str)
            
            account_name_in_row = row.get(header_map.get('account_name'))
            final_account_id = account_name_in_row.strip() if account_name_in_row else account_id_fallback

            original_category = row.get(header_map.get('category'), '').strip()
            institution = row.get(header_map.get('institution'), '').strip()

        except (ValueError, TypeError, KeyError) as e:
            print(f"Skipping row due to parsing error: {row} - {e}")
            skipped_count += 1
            continue

        raw_data = f"{transaction_date}-{description}-{amount}-{final_account_id}"
        transaction_hash = hashlib.sha256(raw_data.encode('utf-8')).hexdigest()

        tx = Transaction(
            transaction_id=transaction_hash, 
            account_id=final_account_id,
            transaction_date=transaction_date, 
            amount=amount,
            description=description, 
            raw_data_hash=transaction_hash,
            institution=institution or None,
            original_category=original_category or None
        )

        if original_category:
            tx.tags.append(original_category)

        tx = apply_rules_to_transaction(tx, rules)
        transactions.append(tx)
        imported_count += 1

    print(f"Parse complete. Imported: {imported_count}, Skipped: {skipped_count}.")
    
    total_amount = sum(tx.amount for tx in transactions)
    summary = {
        "record_count": imported_count,
        "total_amount": total_amount
    }

    return transactions, summary
