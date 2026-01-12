"""
Implementation of the market data provider interface for Stooq.
This provider serves as a fallback.
"""
import pandas_datareader.data as web
import pandas as pd
from datetime import date, timedelta
from typing import List, Dict, Any
from tenacity import retry, stop_after_attempt, wait_exponential

def _map_symbol_to_stooq(symbol: str) -> str:
    """Converts a standard ticker to a Stooq-compatible ticker. Defaults to .US suffix."""
    if '.' in symbol:
        return symbol # Already has a suffix
    return f"{symbol}.US"

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=6))
async def get_quotes(symbols: List[str]) -> Dict[str, Dict[str, Any]]:
    """
    Fetches the latest quote for a list of symbols using Stooq.
    This function is async to maintain a consistent interface with other providers.

    Args:
        symbols: A list of standard stock/ETF symbols.

    Returns:
        A dictionary formatted similarly to the Alpha Vantage provider.
    """
    results = {}
    stooq_symbols = [_map_symbol_to_stooq(s) for s in symbols]
    
    end_date = date.today()
    start_date = end_date - timedelta(days=14) # Look back 2 weeks to find a trading day

    try:
        df = web.DataReader(stooq_symbols, "stooq", start=start_date, end=end_date)
        close_prices = df['Close']

        for original_symbol, stooq_symbol in zip(symbols, stooq_symbols):
            if stooq_symbol not in close_prices.columns:
                results[original_symbol] = {"error": f"Symbol {stooq_symbol} not found by Stooq."}
                continue

            latest_data = close_prices[stooq_symbol].dropna()
            if latest_data.empty:
                results[original_symbol] = {"error": f"No recent data for {stooq_symbol}."}
                continue

            # Most recent data is at the top for Stooq
            latest_price = latest_data.iloc[0]
            latest_date = latest_data.index[0]

            results[original_symbol] = {
                "price": str(latest_price),
                "timestamp": latest_date.strftime('%Y-%m-%d'),
                "source": "stooq"
            }
            
    except Exception as e:
        print(f"Error fetching data from Stooq: {e}")
        # If the entire request fails, mark all symbols as failed for this provider
        for symbol in symbols:
            if symbol not in results:
                results[symbol] = {"error": f"Stooq API failed: {e}"}

    return results
