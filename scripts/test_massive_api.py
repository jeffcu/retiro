import os
import sys
from dotenv import load_dotenv

# Add the project root to the Python path to allow imports from `src`
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.market_data import massive_provider

def run_test():
    """
    Tests LIVE connectivity to the Massive API provider.
    """
    print("--- Massive API LIVE Connectivity Test Utility ---")

    # Load environment variables from projects/trust/.env
    dotenv_path = os.path.join(project_root, '.env')
    load_dotenv(dotenv_path=dotenv_path)

    api_key = os.getenv("MASSIVE_API_KEY")

    if not api_key or "YOUR_API_KEY_HERE" in api_key or len(api_key) < 10:
        print(f"CRITICAL ERROR: MASSIVE_API_KEY not found or is a placeholder in {dotenv_path}")
        print("Please set the key to run the connectivity test.")
        sys.exit(1)

    print(f"SUCCESS: Found MASSIVE_API_KEY in {dotenv_path}")
    
    # Use a common, real-world symbol for a true test
    test_symbol = "AAPL"
    print(f"Attempting to fetch LIVE data for symbol '{test_symbol}'...")

    try:
        result = massive_provider.get_quotes_sync([test_symbol])
        quote = result.get(test_symbol, {})

        if "error" in quote:
            raise RuntimeError(quote["error"])

        price = quote.get("price")
        if price is not None and price > 0:
            print(f"SUCCESS: Provider returned a plausible live price: {price}")
            print("--- LIVE Connectivity Test Passed ---")
        else:
            print(f"ERROR: Provider did not return a valid price. A price must be a number greater than 0.")
            print(f"Provider response: {result}")
            sys.exit(1)

    except Exception as e:
        print(f"\nCRITICAL ERROR: The test failed during the live API call.")
        print(f"This could be a network issue, an invalid API key, or a change in the API's endpoint/response.")
        print(f"Error details: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_test()
