"""
Implementation of the market data provider interface for Alpha Vantage.
(MDS Section 5.2)
"""
import os
import httpx
from typing import List, Dict, Any

API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")
BASE_URL = "https://www.alphavantage.co/query"

async def get_quotes(symbols: List[str]) -> Dict[str, Any]:
    """
    Fetches the latest quote for a list of symbols using Alpha Vantage.

    To respect API limits, this function should be used with batching
    and timing managed by a calling service.

    Args:
        symbols: A list of stock/ETF symbols.

    Returns:
        A dictionary where keys are symbols and values are the quote data, 
        or an error message if the fetch failed for that symbol.
    """
    if not API_KEY or API_KEY == "YOUR_API_KEY_HERE":
        print("ERROR: ALPHA_VANTAGE_API_KEY is not set.")
        return {symbol: {"error": "API key not configured"} for symbol in symbols}

    results = {}
    # Use an async client to make concurrent requests if needed in the future,
    # but for now, we'll process them sequentially to respect rate limits.
    async with httpx.AsyncClient() as client:
        for symbol in symbols:
            params = {
                "function": "GLOBAL_QUOTE",
                "symbol": symbol,
                "apikey": API_KEY
            }
            try:
                response = await client.get(BASE_URL, params=params)
                response.raise_for_status() # Raise an exception for 4xx/5xx responses
                data = response.json()
                
                quote_data = data.get('Global Quote')
                if not quote_data:
                    # This often happens with an invalid symbol or an API limit message.
                    error_message = data.get('Note', f"No 'Global Quote' in response for {symbol}")
                    results[symbol] = {"error": error_message}
                    print(f"WARNING: Could not fetch quote for {symbol}: {error_message}")
                    continue

                results[symbol] = {
                    "price": quote_data.get('05. price'),
                    "change_percent": quote_data.get('10. change percent'),
                    "latest_trading_day": quote_data.get('07. latest trading day')
                }

            except httpx.HTTPStatusError as e:
                print(f"HTTP error fetching quote for {symbol}: {e}")
                results[symbol] = {"error": f"HTTP Error: {e.response.status_code}"}
            except Exception as e:
                print(f"An unexpected error occurred fetching quote for {symbol}: {e}")
                results[symbol] = {"error": "An unexpected error occurred."}
    
    return results
