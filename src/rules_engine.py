import re
from dataclasses import dataclass, field
from typing import List
from datetime import datetime
from decimal import Decimal

from .data_model import Transaction, CashflowType
from . import database as db


@dataclass
class Rule:
    """ 
    Represents a single categorization rule.
    (PRS Section 5.3)
    """
    rule_id: str
    pattern: str  # The regex pattern to match against the transaction description.
    category: str
    cashflow_type: CashflowType
    tags: List[str] = field(default_factory=list)
    priority: int = 100

def _reset_and_apply_defaults(transaction: Transaction) -> Transaction:
    """
    Resets classification fields to their defaults before reapplying rules.
    This is crucial for re-categorization when rules have been changed or deleted.
    """
    # Reset rule-derived fields
    transaction.category = None
    transaction.cashflow_type = None
    transaction.tags = []
    transaction.is_transfer = False

    # Apply default classification based on amount
    if transaction.amount > 0:
        transaction.cashflow_type = CashflowType.INCOME
        transaction.category = 'Income'
    elif transaction.amount < 0:
        transaction.cashflow_type = CashflowType.EXPENSE
        # CORRECTED: Explicitly set default category for expenses.
        transaction.category = 'Uncategorized'

    return transaction

def apply_rules_to_transaction(transaction: Transaction, rules: List[Rule]) -> Transaction:
    """
    Applies a list of rules to a single transaction, modifying it in place.
    The first rule that matches (by priority, then by order) wins.
    """
    # First, reset the transaction to its default state
    transaction = _reset_and_apply_defaults(transaction)

    # Sort rules by priority. Lower number means higher priority.
    sorted_rules = sorted(rules, key=lambda r: r.priority)

    for rule in sorted_rules:
        try:
            if re.search(rule.pattern, transaction.description, re.IGNORECASE):
                print(f"Rule '{rule.pattern}' matched description '{transaction.description}'. Applying category '{rule.category}'.")
                transaction.category = rule.category
                transaction.cashflow_type = rule.cashflow_type
                transaction.tags = list(set(transaction.tags + rule.tags)) # Merge and dedupe tags
                
                # Set is_transfer flag for convenience
                if rule.cashflow_type == CashflowType.TRANSFER:
                    transaction.is_transfer = True
                else:
                    transaction.is_transfer = False
                
                # First match wins, so we break.
                break 
        except re.error as e:
            print(f"Skipping invalid regex pattern in rule {rule.rule_id}: '{rule.pattern}' - {e}")
            continue

    return transaction

def load_rules_from_db() -> List[Rule]:
    """
    Loads all rules from the database and returns them as Rule objects.
    """
    rule_records = db.get_all_rules()
    rules = [
        Rule(
            rule_id=r['rule_id'],
            pattern=r['pattern'],
            category=r['category'],
            cashflow_type=CashflowType(r['cashflow_type']),
            tags=r.get('tags', []), # The DB layer now returns a list
            priority=r['priority']
        ) for r in rule_records
    ]
    return rules

def recategorize_all_transactions() -> int:
    """
    Fetches all transactions, re-applies all current rules, and saves them back to the DB.
    Returns the number of transactions processed.
    """
    print("--- Starting global re-categorization process... ---")
    rules = load_rules_from_db()
    transaction_dicts = db.get_all_transactions()
    updated_transactions = []

    for tx_dict in transaction_dicts:
        # Convert dict from DB back into a Transaction object for processing
        # This ensures type safety and consistency with the data model.
        tx_obj = Transaction(
            transaction_id=tx_dict['transaction_id'],
            account_id=tx_dict['account_id'],
            transaction_date=datetime.strptime(tx_dict['transaction_date'].split(' ')[0], '%Y-%m-%d').date(),
            amount=Decimal(str(tx_dict['amount'])),
            description=tx_dict['description'],
            merchant=tx_dict.get('merchant'),
            asset_id=tx_dict.get('asset_id'),
            import_run_id=tx_dict.get('import_run_id'),
            raw_data_hash=tx_dict.get('raw_data_hash')
        )

        # Apply the full rule set to the reconstituted transaction object
        updated_tx = apply_rules_to_transaction(tx_obj, rules)
        updated_transactions.append(updated_tx)

    if updated_transactions:
        db.save_transactions(updated_transactions)
    
    print(f"--- Re-categorization complete. Processed {len(updated_transactions)} transactions. ---")
    return len(updated_transactions)
