import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, List
import re

from src import database as db
from src.market_data import massive_provider

# Per user requirement: 5 calls per minute.
SECONDS_BETWEEN_CALLS = 12 # (60 seconds / 5 calls = 12s/call)

def _is_supported_symbol(symbol: str) -> bool:
    """Validates if a symbol is likely supported by the API."""
    symbol = symbol.strip().upper()
    # Exclude junk, numeric-only, CUSIP-like, or internal identifiers.
    if not symbol or symbol == '----' or symbol.isdigit() or re.match(r'^[0-9A-Z]{9,}$', symbol):
        return False
    return True

async def refresh_market_data(top_n: int = 0) -> Dict[str, Any]:
    """
    Refreshes market data for holdings using the Massive API, respecting rate limits.

    Args:
        top_n: Number of top holdings to refresh. If 0, refreshes all holdings.
    """
    mode = f"top {top_n}" if top_n > 0 else "ALL"
    print(f"--- Starting market data refresh for {mode} holdings via Massive API... ---")
    
    all_holdings = db.get_holdings()
    if not all_holdings:
        return {"message": "No holdings found. Nothing to refresh.", "refreshed_symbols": [], "failed_symbols": []}

    all_holdings.sort(key=lambda h: h.get('market_value', 0) or 0, reverse=True)
    
    seen = set()
    unique_symbols_ranked = [h['symbol'] for h in all_holdings if not (h['symbol'] in seen or seen.add(h['symbol']))]
    
    symbols_to_process = unique_symbols_ranked[:top_n] if top_n > 0 else unique_symbols_ranked
    symbols_to_refresh = [s for s in symbols_to_process if _is_supported_symbol(s)]
    
    if not symbols_to_refresh:
        return {"message": "No supported symbols found to refresh.", "refreshed_symbols": [], "failed_symbols": []}
        
    print(f"Identified {len(symbols_to_refresh)} unique, supported symbols for refresh.")

    successful_quotes: Dict[str, Dict[str, Any]] = {}
    failed_symbols: List[str] = [s for s in symbols_to_process if not _is_supported_symbol(s)]

    loop = asyncio.get_running_loop()

    for i, symbol in enumerate(symbols_to_refresh):
        print(f"Processing {symbol} ({i+1}/{len(symbols_to_refresh)})... ")
        try:
            # The Massive client is not async, so we run it in a default executor.
            quotes = await loop.run_in_executor(
                None, massive_provider.get_quotes_sync, [symbol]
            )
            quote_data = quotes.get(symbol, {})

            if "error" in quote_data or not quote_data.get("price"):
                print(f"Provider failed for {symbol}: {quote_data.get('error')}")
                failed_symbols.append(symbol)
            else:
                successful_quotes[symbol] = {
                    "price": quote_data['price'],
                    "timestamp": datetime.now(timezone.utc).isoformat(), # Use current time for live refresh
                    "source": quote_data['source']
                }
        except Exception as e:
            print(f"An unexpected error occurred while processing {symbol}: {e}")
            failed_symbols.append(symbol)

        # Wait before the next call to respect rate limits.
        if (i + 1) < len(symbols_to_refresh):
            await asyncio.sleep(SECONDS_BETWEEN_CALLS)

    # --- Persist results to the database ---
    if successful_quotes:
        print(f"Updating database with {len(successful_quotes)} new price points.")
        db.update_holdings_with_new_prices(successful_quotes)
        db.save_price_quotes(successful_quotes)
    else:
        print("No new price points to update in the database.")

    print("--- Market data refresh complete. ---")
    
    return {
        "message": "Market data refresh process finished.",
        "refreshed_symbols": list(successful_quotes.keys()),
        "failed_symbols": failed_symbols,
        "total_symbols_processed": len(symbols_to_process)
    }

# The EOD refresh is now just a call to the main function with no limit.
async def refresh_eod_data() -> Dict[str, Any]:
    return await refresh_market_data(top_n=0)
