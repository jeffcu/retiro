import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, List
import re

from src import database as db
from src.market_data import massive_provider, alphavantage_provider

# Per user requirement: 5 calls per minute.
SECONDS_BETWEEN_CALLS = 12 # (60 seconds / 5 calls = 12s/call)

# --- NEW: Mutual exclusion lock ---
# This lock prevents multiple refresh tasks from running concurrently and violating API rate limits.
_refresh_lock = asyncio.Lock()


def _is_supported_symbol(symbol: str) -> bool:
    """Validates if a symbol is likely supported by the API."""
    symbol = symbol.strip().upper()
    # Exclude junk, numeric-only, CUSIP-like, or internal identifiers.
    if not symbol or symbol == '----' or symbol.isdigit() or re.match(r'^[0-9A-Z]{9,}$', symbol):
        return False
    return True

async def refresh_market_data(top_n: int = 0) -> Dict[str, Any]:
    """
    Refreshes market data for holdings using an intelligent, multi-provider routing strategy.
    This function is now protected by a lock to prevent concurrent runs.
    """
    if _refresh_lock.locked():
        print("--- Market data refresh is already in progress. Skipping this run. ---")
        return {"message": "Refresh already in progress.", "refreshed_symbols": [], "failed_symbols": []}

    async with _refresh_lock:
        mode = f"top {top_n}" if top_n > 0 else "ALL"
        print(f"--- Starting market data refresh for {mode} holdings via multi-provider... ---")
        
        all_holdings = db.get_holdings()
        if not all_holdings:
            return {"message": "No holdings found. Nothing to refresh.", "refreshed_symbols": [], "failed_symbols": []}

        all_holdings.sort(key=lambda h: h.get('market_value', 0) or 0, reverse=True)
        
        # Create a mapping of each unique symbol to its asset type for routing
        symbol_to_asset_type = {}
        seen_symbols = set()
        ranked_symbols = []
        for h in all_holdings:
            symbol = h['symbol']
            if symbol not in seen_symbols:
                seen_symbols.add(symbol)
                ranked_symbols.append(symbol)
                # Store the asset type for routing logic
                symbol_to_asset_type[symbol] = h.get('asset_type')

        symbols_to_process = ranked_symbols[:top_n] if top_n > 0 else ranked_symbols
        
        if not symbols_to_process:
            return {"message": "No symbols found to refresh.", "refreshed_symbols": [], "failed_symbols": []}
            
        print(f"Identified {len(symbols_to_process)} unique symbols for potential refresh.")

        successful_quotes: Dict[str, Dict[str, Any]] = {}
        failed_symbols: List[str] = []

        loop = asyncio.get_running_loop()

        for i, symbol in enumerate(symbols_to_process):
            if not _is_supported_symbol(symbol):
                continue

            asset_type = symbol_to_asset_type.get(symbol)
            provider_module = None

            # --- Provider Routing Logic ---
            if asset_type == "Common Stock":
                provider_module = massive_provider
            elif asset_type in ["Mutual Fund Open", "Mutual Fund Closed"]:
                provider_module = alphavantage_provider
            else:
                print(f"Skipping {symbol}: unsupported asset type '{asset_type}'.")
                continue

            print(f"Processing {symbol} ({i+1}/{len(symbols_to_process)}) via {provider_module.__name__}... ")
            try:
                quote_data = await loop.run_in_executor(
                    None, provider_module.get_eod_single, symbol
                )

                if "error" in quote_data or not quote_data.get("price"):
                    print(f"  └── Provider failed for {symbol}: {quote_data.get('error')}")
                    failed_symbols.append(symbol)
                else:
                    print(f"  └── Success: {quote_data['price']}")
                    successful_quotes[symbol] = {
                        "price": quote_data['price'],
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "source": quote_data['source']
                    }
            except Exception as e:
                print(f"An unexpected error occurred while processing {symbol}: {e}")
                failed_symbols.append(symbol)

            # Wait before the next call to respect rate limits across all providers.
            if (i + 1) < len(symbols_to_process):
                await asyncio.sleep(SECONDS_BETWEEN_CALLS)

        # --- Persist results to the database --- 
        if successful_quotes:
            print(f"Updating database with {len(successful_quotes)} successful price points.")
            db.update_holdings_with_new_prices(successful_quotes)
            db.save_price_quotes(successful_quotes)
        
        if failed_symbols:
            print(f"Marking {len(failed_symbols)} symbols as failed in the database.")
            db.mark_holdings_as_failed(failed_symbols)

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
