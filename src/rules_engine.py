import re
from dataclasses import dataclass, field
from typing import List

from .data_model import Transaction, CashflowType
from .database import get_all_rules as db_get_all_rules


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


def apply_rules_to_transaction(transaction: Transaction, rules: List[Rule]) -> Transaction:
    """
    Applies a list of rules to a single transaction, modifying it in place.
    The first rule that matches (by priority, then by order) wins.
    """
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
    rule_records = db_get_all_rules()
    rules = [
        Rule(
            rule_id=r['rule_id'],
            pattern=r['pattern'],
            category=r['category'],
            cashflow_type=CashflowType(r['cashflow_type']),
            tags=r['tags'].split(',') if r['tags'] else [],
            priority=r['priority']
        ) for r in rule_records
    ]
    return rules
