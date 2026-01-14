"""
Implementation of the market data provider interface for the Massive API.
"""
import os
from typing import List, Dict, Any
from datetime import date
from tenacity import retry, stop_after_attempt, wait_exponential
from massive_client import MassiveClient

# Initialize the client once. It will be shared.
API_KEY = os.getenv("MASSIVE_API_KEY")
if not API_KEY:
    print("WARNING: MASSIVE_API_KEY is not set in the .env file. The market data provider will be disabled.")
    CLIENT = None
else:
    CLIENT = MassiveClient(api_key=API_KEY)

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=6))
def get_quotes_sync(symbols: List[str]) -> Dict[str, Dict[str, Any]]:
    """
    Synchronous wrapper to fetch the latest EOD quote for a list of symbols using the Massive API client.
    NOTE: The client library is not async, so we run it synchronously.

    Args:
        symbols: A list of standard stock/ETF symbols.

    Returns:
        A dictionary formatted similarly to other providers.
    """
    if not CLIENT:
        return {symbol: {"error": "Massive API client not initialized."} for symbol in symbols}

    results = {}
    today = date.today().isoformat()

    for symbol in symbols:
        # Massive API expects a suffix for US stocks, e.g., 'AAPL.US'
        # We will assume '.US' for now as it's the most common case.
        massive_symbol = f"{symbol.upper()}.US"
        try:
            # The get_eod_single function is perfect for getting the latest closing price.
            data = CLIENT.get_eod_single(massive_symbol, today)
            
            if data and data.get('close') is not None:
                results[symbol] = {
                    "price": str(data['close']),
                    "timestamp": data.get('date', today),
                    "source": "massive"
                }
            else:
                error_msg = data.get('message', f"No data returned for {symbol}")
                print(f"Massive API Warning for {symbol}: {error_msg}")
                results[symbol] = {"error": error_msg}

        except Exception as e:
            print(f"Error fetching data from Massive API for {symbol}: {e}")
            results[symbol] = {"error": f"Massive API client failed: {e}"}
            
    return results
