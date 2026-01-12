"""
Implementation of the market data provider interface for Alpha Vantage.
(MDS Section 5.2)
"""
import os
import httpx
from typing import List, Dict, Any
from tenacity import retry, stop_after_attempt, wait_exponential

API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")
BASE_URL = "https://www.alphavantage.co/query"

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
async def get_quotes(symbols: List[str]) -> Dict[str, Dict[str, Any]]:
    """
    Fetches the latest quote for a list of symbols using Alpha Vantage.

    Args:
        symbols: A list of stock/ETF symbols.

    Returns:
        A dictionary where keys are symbols and values are a dict containing the quote data 
        (price, timestamp, etc.) or an error message.
    """
    if not API_KEY or API_KEY == "YOUR_API_KEY_HERE":
        print("ERROR: ALPHA_VANTAGE_API_KEY is not set.")
        return {symbol: {"error": "API key not configured"} for symbol in symbols}

    results = {}
    async with httpx.AsyncClient(timeout=15.0) as client:
        for symbol in symbols:
            params = {
                "function": "GLOBAL_QUOTE",
                "symbol": symbol,
                "apikey": API_KEY
            }
            try:
                response = await client.get(BASE_URL, params=params)
                response.raise_for_status() 
                data = response.json()
                
                quote_data = data.get('Global Quote')
                if not quote_data or not quote_data.get('05. price'):
                    error_message = data.get('Note', f"No valid 'Global Quote' in response for {symbol}")
                    results[symbol] = {"error": error_message}
                    print(f"WARNING: AlphaVantage could not fetch quote for {symbol}: {error_message}")
                    continue

                results[symbol] = {
                    "price": quote_data.get('05. price'),
                    "timestamp": quote_data.get('07. latest trading day'),
                    "source": "alpha_vantage"
                }

            except httpx.HTTPStatusError as e:
                print(f"HTTP error fetching quote for {symbol} from AlphaVantage: {e}")
                results[symbol] = {"error": f"HTTP Error: {e.response.status_code}"}
            except Exception as e:
                print(f"An unexpected error occurred fetching {symbol} from AlphaVantage: {e}")
                results[symbol] = {"error": "An unexpected error occurred."}
    
    return results