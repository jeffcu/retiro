import sys
import os
import sqlite3

# This script resets (clears) all tags for a specific account ID.
# Useful when an import accidentally sets tags you didn't want.
# Usage: python scripts/reset_tags.py <Account_ID>

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.database import get_db_connection

def reset_tags(account_id):
    print(f"--- Resetting tags for Account Group: '{account_id}' ---")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check how many holdings will be affected
    cursor.execute("SELECT COUNT(*) FROM holdings WHERE trim(lower(account_id)) = trim(lower(?))", (account_id,))
    count = cursor.fetchone()[0]
    
    if count == 0:
        print(f"No holdings found for account '{account_id}'. Check the name and try again.")
        conn.close()
        return
    
    print(f"Found {count} holdings. Clearing tags...")
    
    try:
        cursor.execute("UPDATE holdings SET tags = NULL WHERE trim(lower(account_id)) = trim(lower(?))", (account_id,))
        conn.commit()
        print("SUCCESS: Tags have been cleared.")
    except Exception as e:
        print(f"ERROR: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/reset_tags.py <Account_ID>")
        print("Example: python scripts/reset_tags.py Highway1")
        sys.exit(1)
    
    target_account = sys.argv[1]
    reset_tags(target_account)
