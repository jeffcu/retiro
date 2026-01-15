import os
import httpx
from dotenv import load_dotenv
from typing import List, Dict, Any
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type
from datetime import date, timedelta

# This module implements the live Massive API client.
# It handles network requests, authentication, and error handling.
API_BASE_URL = "https://api.massive.com" # Base URL, path will be constructed per-function.

# Load the API key from the .env file
load_dotenv()
API_KEY = os.getenv("MASSIVE_API_KEY")

# Define retry strategy for API calls: 3 attempts, 5 seconds apart.
RETRY_DECORATOR = retry(
    stop=stop_after_attempt(3),
    wait=wait_fixed(5),
    retry=retry_if_exception_type((httpx.RequestError, httpx.HTTPStatusError)),
    reraise=True
)

@RETRY_DECORATOR
def get_eod_single(symbol: str) -> Dict[str, Any]:
    """
    Fetches the previous day's closing price for a single symbol from the LIVE API.
    This now uses the documented v1 endpoint.
    (MDS Section 5.2)
    """
    if not API_KEY or len(API_KEY) < 10 or "YOUR_API_KEY_HERE" in API_KEY:
        print(f"[Massive Provider] CRITICAL: API key is not configured for symbol {symbol}.")
        return {"error": "MASSIVE_API_KEY is not set correctly."}

    # The API requires a date for the previous day's close.
    # This logic robustly finds the last market day (e.g., Friday for a Monday request).
    request_date = date.today()
    offset = 1  # Default to yesterday
    if request_date.weekday() == 0:  # Monday
        offset = 3
    elif request_date.weekday() == 6:  # Sunday
        offset = 2
    # Saturday's offset remains 1, correctly pointing to Friday.
    last_market_day = request_date - timedelta(days=offset)
    date_str = last_market_day.strftime('%Y-%m-%d')

    # CORRECTED: Using the documented endpoint structure from their client library.
    # e.g., /v1/open-close/AAPL/2024-07-29
    endpoint = f"{API_BASE_URL}/v1/open-close/{symbol.upper()}/{date_str}"
    params = {"apiKey": API_KEY}

    try:
        with httpx.Client() as client:
            print(f"[Massive Provider] Connecting to LIVE endpoint: {endpoint}")
            response = client.get(endpoint, params=params, timeout=10.0)
            response.raise_for_status()
            data = response.json()

            # Validate the response structure from the v1 endpoint
            if data.get('status') == 'OK' and 'close' in data:
                return {
                    "symbol": data.get('symbol', symbol),
                    "price": float(data['close']),
                    "source": "Massive API (Live EOD)"
                }
            else:
                error_message = data.get('error', 'Invalid or unexpected JSON response.')
                print(f"[Massive Provider] API Error for {symbol}: {error_message}")
                return {"error": error_message, "data": data}

    except httpx.HTTPStatusError as e:
        error_text = e.response.text
        print(f"[Massive Provider] HTTP Error for {symbol}: {e.response.status_code} - {error_text}")
        # Try to parse error from JSON response if possible
        try:
            error_json = e.response.json()
            return {"error": error_json.get('error', f"API returned status {e.response.status_code}")}
        except Exception:
            return {"error": f"API returned status {e.response.status_code}"}
    except httpx.RequestError as e:
        print(f"[Massive Provider] Network Error for {symbol}: {e}")
        return {"error": "A network error occurred."}
    except Exception as e:
        print(f"[Massive Provider] An unexpected error occurred for {symbol}: {e}")
        return {"error": "An unexpected error occurred."}


def get_quotes_sync(symbols: List[str]) -> Dict[str, Dict[str, Any]]:
    """
    Fetches the latest price for a list of symbols by calling the EOD function.
    """
    results = {}
    for symbol in symbols:
        quote = get_eod_single(symbol)
        results[symbol] = quote
    return results
