"""
Service to orchestrate the fetching of market data from various providers,
apply rate-limiting, and persist the results to the database.
(PRS Section 6.3)
"""
import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, List

from src import database as db
from src.market_data import alpha_vantage_provider, stooq_provider

# Per AlphaVantage free tier: 5 calls per minute.
# We will make calls one by one, with a delay.
SECONDS_BETWEEN_CALLS = 15 # (60 seconds / 4 calls = 15s/call)

async def refresh_market_data(top_n: int = 25) -> Dict[str, Any]:
    """
    Refreshes market data for top N holdings by market value.
    Tries the primary provider first, then falls back to a secondary provider.
    Respects API rate limits by delaying individual calls.
    """
    print(f"--- Starting market data refresh for top {top_n} holdings... ---")
    
    all_holdings = db.get_holdings()
    if not all_holdings:
        return {"message": "No holdings found. Nothing to refresh.", "refreshed_symbols": [], "failed_symbols": []}

    all_holdings.sort(key=lambda h: h.get('market_value', 0) or 0, reverse=True)
    
    seen = set()
    unique_symbols_ranked = [h['symbol'] for h in all_holdings if not (h['symbol'] in seen or seen.add(h['symbol']))]
    
    symbols_to_refresh = unique_symbols_ranked[:top_n]
    if not symbols_to_refresh:
        return {"message": "Holdings exist, but no symbols to refresh.", "refreshed_symbols": [], "failed_symbols": []}
        
    print(f"Identified {len(symbols_to_refresh)} unique symbols to refresh: {symbols_to_refresh}")

    successful_quotes: Dict[str, Dict[str, Any]] = {}
    symbols_for_fallback: List[str] = []

    # --- Primary Provider: Alpha Vantage ---
    print("--- Stage 1: Querying Primary Provider (Alpha Vantage) ---")
    for i, symbol in enumerate(symbols_to_refresh):
        print(f"Processing {symbol} ({i+1}/{len(symbols_to_refresh)})...")
        quotes = await alpha_vantage_provider.get_quotes([symbol])
        quote_data = quotes.get(symbol, {})

        if "error" in quote_data or not quote_data.get("price"):
            print(f"Primary provider failed for {symbol}. Adding to fallback queue.")
            symbols_for_fallback.append(symbol)
        else:
            successful_quotes[symbol] = {
                "price": quote_data['price'],
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "source": quote_data['source']
            }
        
        # Wait before the next call to respect rate limits
        if (i + 1) < len(symbols_to_refresh):
            await asyncio.sleep(SECONDS_BETWEEN_CALLS)

    # --- Fallback Provider: Stooq ---
    if symbols_for_fallback:
        print(f"--- Stage 2: Querying Fallback Provider (Stooq) for {len(symbols_for_fallback)} symbols ---")
        # Stooq is safe to batch
        fallback_quotes = await stooq_provider.get_quotes(symbols_for_fallback)
        for symbol, data in fallback_quotes.items():
            if "error" in data or not data.get("price"):
                print(f"Fallback provider also failed for {symbol}: {data.get('error')}")
            else:
                print(f"Successfully fetched {symbol} from fallback.")
                successful_quotes[symbol] = {
                    "price": data['price'],
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "source": data['source']
                }

    # --- Persist results to the database ---
    if successful_quotes:
        print(f"Updating database with {len(successful_quotes)} new price points.")
        db.update_holdings_with_new_prices(successful_quotes)
        db.save_price_quotes(successful_quotes)
    else:
        print("No new price points to update in the database.")

    print("--- Market data refresh complete. ---")
    
    final_failed_symbols = [s for s in symbols_to_refresh if s not in successful_quotes]
    
    return {
        "message": "Market data refresh process finished.",
        "refreshed_symbols": list(successful_quotes.keys()),
        "failed_symbols": final_failed_symbols,
        "total_symbols_processed": len(symbols_to_refresh)
    }