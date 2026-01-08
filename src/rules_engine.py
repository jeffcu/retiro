import re
import logging
from dataclasses import dataclass, field
from typing import List
from datetime import datetime
from decimal import Decimal

from .data_model import Transaction, CashflowType
from . import database as db


@dataclass
class Rule:
    """ 
    Represents a single v2 categorization rule.
    (PRS Section 5.3)
    """
    rule_id: str
    pattern: str | None
    category: str # Action: what to set the category to
    cashflow_type: CashflowType # Action: what to set the type to
    tags: List[str] = field(default_factory=list)
    priority: int = 100
    case_sensitive: bool = False
    account_filter_mode: str = 'include'
    account_filter_list: List[str] = field(default_factory=list)
    # New condition fields
    condition_category: str | None = None
    condition_institution: str | None = None
    condition_cashflow_type: str | None = None
    condition_tags: str | None = None

def apply_rules_to_transaction(transaction: Transaction, rules: List[Rule]) -> Transaction:
    """
    Applies a list of rules to a single transaction, modifying it in place.
    The first rule that matches all conditions (by priority) wins.
    If no rule matches, it falls back to the original category or a default.
    """
    sorted_rules = sorted(rules, key=lambda r: r.priority)
    rule_matched = False

    # Preserve the original state before modification for condition checking
    original_category = transaction.category
    original_cashflow_type = transaction.cashflow_type

    # Reset volatile fields before rule application
    transaction.tags = []
    transaction.is_transfer = False

    for rule in sorted_rules:
        # --- Condition 1: Account Filter ---
        if rule.account_filter_list:
            account_matches = any(acc.lower() == transaction.account_id.lower() for acc in rule.account_filter_list)
            
            if rule.account_filter_mode == 'include' and not account_matches:
                continue # Skip: transaction account not in the include list
            if rule.account_filter_mode == 'exclude' and account_matches:
                continue # Skip: transaction account is in the exclude list

        # --- Condition 2: Institution ---
        if rule.condition_institution and rule.condition_institution.lower() != (transaction.institution or '').lower():
            continue

        # --- Condition 3: Category ---
        # Check against the category the transaction had *before* any rules were applied.
        if rule.condition_category and rule.condition_category.lower() != (original_category or '').lower():
            continue
        
        # --- Condition 4: Cashflow Type ---
        if rule.condition_cashflow_type and original_cashflow_type and \
           rule.condition_cashflow_type.lower() != original_cashflow_type.value.lower():
            continue

        # --- Condition 5: Tags (simple string contains) ---
        # This is a weak check. A better implementation would require dedicated tag storage.
        if rule.condition_tags:
            # Tags in DB are a comma-separated string. We check if the condition tag is a substring.
            db_tags = transaction.tags # This should be the raw tags from DB
            if not any(rule.condition_tags.lower() in tag.lower() for tag in db_tags):
                 continue

        # --- Condition 6: Description Pattern ---
        if rule.pattern:
            try:
                flags = 0 if rule.case_sensitive else re.IGNORECASE
                if not re.search(rule.pattern, transaction.description, flags):
                    continue # Description doesn't match, so skip to next rule
            except re.error as e:
                print(f"Skipping invalid regex pattern in rule {rule.rule_id}: '{rule.pattern}' - {e}")
                continue
        
        # If we reached here, all conditions for this rule have passed.
        # Apply the action.
        print(f"Rule '{rule.rule_id}' ('{rule.pattern or 'any'}') matched description '{transaction.description}'. Applying category '{rule.category}'.")
        transaction.category = rule.category
        transaction.cashflow_type = rule.cashflow_type
        transaction.tags = list(set(transaction.tags + rule.tags)) # Merge and dedupe tags
        
        transaction.is_transfer = rule.cashflow_type == CashflowType.TRANSFER
        
        rule_matched = True
        break # First match wins

    # --- Fallback Logic: If no rules matched --- #
    if not rule_matched:
        # Restore original category if it existed.
        transaction.category = original_category

        # Apply default cashflow type and category ONLY if they are not already set.
        if transaction.amount > 0:
            transaction.cashflow_type = CashflowType.INCOME
            if not transaction.category:
                transaction.category = 'Income'
        elif transaction.amount < 0:
            transaction.cashflow_type = CashflowType.EXPENSE
            if not transaction.category:
                transaction.category = 'Uncategorized'

    return transaction

def load_rules_from_db() -> List[Rule]:
    """
    Loads all rules from the database and returns them as Rule objects.
    """
    rule_records = db.get_all_rules()
    rules = []
    for r in rule_records:
        cf_type = CashflowType.from_string(r['cashflow_type'])
        if not cf_type:
            logging.warning(f"Skipping corrupt or invalid rule {r['rule_id']} due to un-parseable cashflow_type: '{r['cashflow_type']}'")
            continue
        
        rules.append(Rule(
            rule_id=r['rule_id'],
            pattern=r.get('pattern'),
            category=r['category'],
            cashflow_type=cf_type,
            tags=r.get('tags', []),
            priority=r['priority'],
            case_sensitive=r.get('case_sensitive', False),
            account_filter_mode=r.get('account_filter_mode', 'include'),
            account_filter_list=r.get('account_filter_list', []),
            condition_category=r.get('condition_category'),
            condition_institution=r.get('condition_institution'),
            condition_cashflow_type=r.get('condition_cashflow_type'),
            condition_tags=r.get('condition_tags')
        ))
    return rules

def recategorize_all_transactions() -> int:
    """
    Fetches all transactions, re-applies all current rules, and saves them back to the DB.
    Returns the number of transactions processed.
    """
    print("--- Starting global re-categorization process... ---")
    rules = load_rules_from_db()
    transaction_dicts = db.get_transactions()
    updated_transactions = []

    for tx_dict in transaction_dicts:
        # Convert dict from DB back into a Transaction object for processing
        tx_obj = Transaction(
            transaction_id=tx_dict['transaction_id'],
            account_id=tx_dict['account_id'],
            transaction_date=datetime.strptime(tx_dict['transaction_date'].split(' ')[0], '%Y-%m-%d').date(),
            amount=Decimal(str(tx_dict['amount'])),
            description=tx_dict['description'],
            merchant=tx_dict.get('merchant'),
            category=tx_dict.get('category'), # Pass current category
            cashflow_type=CashflowType.from_string(tx_dict.get('cashflow_type')),
            tags=tx_dict.get('tags', '').split(',') if tx_dict.get('tags') else [],
            asset_id=tx_dict.get('asset_id'),
            import_run_id=tx_dict.get('import_run_id'),
            raw_data_hash=tx_dict.get('raw_data_hash'),
            institution=tx_dict.get('institution'),
            original_category=tx_dict.get('original_category')
        )

        # Apply the full rule set to the reconstituted transaction object
        updated_tx = apply_rules_to_transaction(tx_obj, rules)
        updated_transactions.append(updated_tx)

    if updated_transactions:
        db.save_transactions(updated_transactions)
    
    print(f"--- Re-categorization complete. Processed {len(updated_transactions)} transactions. ---")
    return len(updated_transactions)
