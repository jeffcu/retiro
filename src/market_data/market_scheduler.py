import asyncio
from datetime import datetime, time, timezone
from src.market_data.polling_service import refresh_market_data

# Market hours (US Eastern Time) adjusted for UTC approximations
# Assuming Daylight Saving Time (DST) for standard market definition: 9:30 ET to 4:00 ET
# UTC equivalents: 13:30 UTC to 20:00 UTC
MARKET_OPEN_HOUR_UTC = 13
MARKET_CLOSE_HOUR_UTC = 20
POLL_INTERVAL_SECONDS = 3600 # 1 hour

def is_market_open_time(now_utc: datetime) -> bool:
    """Checks if the current UTC time falls within approximate US market hours (13:30 to 20:00 UTC) on a weekday."""
    # Check for weekends (Monday=0, Sunday=6)
    if now_utc.weekday() >= 5:
        return False

    now_time_utc = now_utc.time()
    
    # Check the hour range, focusing on the 13:30 to 20:00 window
    market_open_time = time(MARKET_OPEN_HOUR_UTC, 30, 0)
    market_close_time = time(MARKET_CLOSE_HOUR_UTC, 0, 0)
    
    if now_time_utc >= market_open_time and now_time_utc < market_close_time:
        return True
    
    return False

async def background_market_poller():
    """
    The main background worker loop for the market data drip service.
    Runs hourly checks during market hours for the Top 25 (PRS 6.3).
    Runs an additional check for EOD (Long Tail) updates in the hour after close.
    """
    print("Market Polling Scheduler: Background task initialized. Polling interval: 1 hour.")
    
    # Initial wait: Wait 10 seconds on startup to allow the API to fully initialize.
    await asyncio.sleep(10)
    
    while True:
        now_utc = datetime.now(timezone.utc)
        
        # --- Hourly Refresh (Top 25) ---
        if is_market_open_time(now_utc):
            print(f"[{now_utc.isoformat(timespec='minutes')}] Market is open. Triggering hourly Top 25 refresh.")
            try:
                # Only refresh top 25, the polling service handles rate limiting.
                summary = await refresh_market_data(top_n=25)
                print(f"Hourly refresh successful: {len(summary['refreshed_symbols'])} symbols updated.")
            except Exception as e:
                print(f"ERROR: Market polling failed: {e}")
        
        # --- EOD Refresh (Long Tail) ---
        # EOD Window: The hour immediately after market close (20:00 UTC to 21:00 UTC).
        # We assume the polling service, when given a high Top N, handles all symbols.
        eod_window = now_utc.hour == MARKET_CLOSE_HOUR_UTC and now_utc.weekday() < 5
        
        if eod_window and now_utc.minute < 30: # Only run EOD once early in the hour (e.g., 20:00 - 20:29 UTC)
            print(f"[{now_utc.isoformat(timespec='minutes')}] Entering EOD window. Triggering full daily refresh.")
            try:
                # Use a large number to target the 'long tail' for daily refresh.
                summary = await refresh_market_data(top_n=1000)
                print(f"EOD refresh complete: {len(summary['refreshed_symbols'])} symbols updated.")
            except Exception as e:
                print(f"ERROR: EOD polling failed: {e}")
        
        # Sleep for exactly one hour to maintain hourly frequency.
        await asyncio.sleep(POLL_INTERVAL_SECONDS)
