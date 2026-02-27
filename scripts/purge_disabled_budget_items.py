import sys
import os
import sqlite3

# This script purges all DISABLED (ghost/draft) items from the Discretionary Budget table.
# It assumes that anything marked 'is_enabled = 0' is a ghost item you want removed.

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.database import get_db_connection

def purge_ghosts():
    print("--- Discretionary Budget Ghost Protocol Initiated ---")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check what we are about to delete
    cursor.execute("SELECT item_id, name, amount FROM discretionary_budget_items WHERE is_enabled = 0")
    ghosts = cursor.fetchall()
    
    count = len(ghosts)
    
    if count == 0:
        print("Sensors indicate no disabled/ghost items found. The table is clean.")
        conn.close()
        return
    
    print(f"Found {count} ghost items (Disabled entries):")
    for ghost in ghosts:
        print(f" - [DELETE] {ghost['name']} (${ghost['amount']})")
    
    # Execute Purge
    try:
        cursor.execute("DELETE FROM discretionary_budget_items WHERE is_enabled = 0")
        conn.commit()
        print(f"\nSUCCESS: Vaporized {count} ghost items. The budget is clear.")
    except Exception as e:
        print(f"ERROR: Hull breach detected: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    purge_ghosts()
