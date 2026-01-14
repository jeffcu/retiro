import asyncio
from datetime import datetime, time, timezone, timedelta
from src.market_data.polling_service import refresh_market_data

# Target times in US Eastern Time
MID_DAY_REFRESH_EST = time(12, 0, 0)
AFTER_MARKET_REFRESH_EST = time(16, 0, 0)

def get_seconds_until(target_time_est: time) -> float:
    """
    Calculates seconds until the next occurrence of a target time in EST.
    Handles timezone conversion from UTC.
    """
    # EST is UTC-5, EDT is UTC-4. We'll approximate with UTC-4 for modern relevance.
    est = timezone(timedelta(hours=-4), 'EDT')
    now_est = datetime.now(est)
    
    target_today = now_est.replace(hour=target_time_est.hour, minute=target_time_est.minute, second=0, microsecond=0)
    
    # If the target time has already passed today, schedule for tomorrow.
    if target_today < now_est:
        target_tomorrow = target_today + timedelta(days=1)
        # Handle weekends: if tomorrow is Sat, schedule for Mon. If Sun, schedule for Mon.
        if target_tomorrow.weekday() == 5: # Saturday
            target_tomorrow += timedelta(days=2)
        elif target_tomorrow.weekday() == 6: # Sunday
            target_tomorrow += timedelta(days=1)
        return (target_tomorrow - now_est).total_seconds()
    
    # Handle weekends for today's schedule
    if now_est.weekday() >= 5: # It's currently Sat or Sun
        # Find next Monday
        next_monday = now_est + timedelta(days=(7 - now_est.weekday()))
        next_run_time = next_monday.replace(hour=target_time_est.hour, minute=target_time_est.minute, second=0, microsecond=0)
        return (next_run_time - now_est).total_seconds()

    return (target_today - now_est).total_seconds()

async def background_market_poller():
    """
    Background worker that triggers data refreshes at scheduled times.
    - 12:00 PM EST: Top 25 holdings
    - 04:00 PM EST: All holdings
    """
    print("Market Polling Scheduler: Background task initialized.")
    await asyncio.sleep(5) # Initial wait for app startup
    
    while True:
        seconds_to_mid_day = get_seconds_until(MID_DAY_REFRESH_EST)
        seconds_to_after_market = get_seconds_until(AFTER_MARKET_REFRESH_EST)

        if seconds_to_mid_day < seconds_to_after_market:
            sleep_duration = seconds_to_mid_day
            task_name = "Mid-Day Top 25"
            top_n = 25
        else:
            sleep_duration = seconds_to_after_market
            task_name = "After-Market Full Refresh"
            top_n = 0 # 0 means all holdings

        print(f"Scheduler: Next run is '{task_name}' in {timedelta(seconds=sleep_duration)}.")
        await asyncio.sleep(sleep_duration + 5) # Add 5s buffer

        now = datetime.now(timezone(timedelta(hours=-4), 'EDT'))
        print(f"[{now.isoformat()}] Waking up for scheduled task: '{task_name}'.")
        try:
            summary = await refresh_market_data(top_n=top_n)
            print(f"Scheduled refresh successful: {len(summary['refreshed_symbols'])} symbols updated.")
        except Exception as e:
            print(f"ERROR: Scheduled market polling failed: {e}")
