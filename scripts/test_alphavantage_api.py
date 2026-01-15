import os
import sys
import time
from dotenv import load_dotenv
import httpx

# Add the project root to the Python path
# This allows the script to be run from the root of the project `python scripts/test_...`
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# --- CONFIGURATION ---
SYMBOLS_TO_TEST = ["VTSAX", "VTIAX", "VBTLX", "VFIAX"] # Common Mutual Funds
API_CALL_INTERVAL_SECONDS = 12 # Alphavantage free tier is 5 calls/min
BASE_URL = "https://www.alphavantage.co/query"

def run_test():
    """
    Tests connectivity to the Alphavantage API for a list of mutual funds.
    """
    print("--- Alphavantage API Connectivity Test (Mutual Funds) ---")
    print(f"Polling Rate: 1 call every {API_CALL_INTERVAL_SECONDS} seconds.\n")

    # Load environment variables from projects/trust/.env
    dotenv_path = os.path.join(project_root, '.env')
    if not os.path.exists(dotenv_path):
        print(f"CRITICAL ERROR: .env file not found at {dotenv_path}")
        print("Please ensure the .env file exists in the 'projects/trust' directory.")
        sys.exit(1)
    
    load_dotenv(dotenv_path=dotenv_path)

    api_key = os.getenv("ALPHA_VANTAGE_API_KEY")

    if not api_key or "YOUR_API_KEY_HERE" in api_key or len(api_key) < 10:
        print(f"CRITICAL ERROR: ALPHA_VANTAGE_API_KEY not found or is a placeholder in {dotenv_path}")
        print("Please set the key to run the connectivity test.")
        sys.exit(1)

    print(f"SUCCESS: Found ALPHA_VANTAGE_API_KEY in {dotenv_path}")
    print("-" * 50)

    for i, symbol in enumerate(SYMBOLS_TO_TEST):
        print(f"Testing Symbol: {symbol}...")
        
        params = {
            "function": "GLOBAL_QUOTE",
            "symbol": symbol,
            "apikey": api_key
        }

        try:
            with httpx.Client() as client:
                response = client.get(BASE_URL, params=params, timeout=15.0)
                response.raise_for_status()
                data = response.json()

            # Check for a valid quote
            if "Global Quote" in data and data["Global Quote"] and "05. price" in data["Global Quote"]:
                price = data["Global Quote"]["05. price"]
                print(f"  └── SUCCESS: Found price for {symbol}: {price}")
            # Check for API error messages
            elif "Note" in data:
                print(f"  └── FAILURE: API rate limit likely hit. Response: {data['Note']}")
            elif "Information" in data:
                 print(f"  └── FAILURE: Invalid API Key or other issue. Response: {data['Information']}")
            else:
                print(f"  └── FAILURE: Could not find a valid quote for {symbol}.")
                print(f"      API Response: {data}")

        except httpx.HTTPStatusError as e:
            print(f"  └── FAILURE: HTTP Error! Status: {e.response.status_code}")
            print(f"      Response: {e.response.text}")
        except httpx.RequestError as e:
            print(f"  └── FAILURE: Network error. Could not connect to the API.")
            print(f"      Error: {e}")
        except Exception as e:
            print(f"  └── FAILURE: An unexpected error occurred.")
            print(f"      Error: {e}")
        
        # Respect the rate limit before the next call
        if i < len(SYMBOLS_TO_TEST) - 1:
            time.sleep(API_CALL_INTERVAL_SECONDS)
    
    print("-" * 50)
    print("--- Test complete. ---")


if __name__ == "__main__":
    run_test()
