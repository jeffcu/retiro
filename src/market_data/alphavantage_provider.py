import os
import httpx
from dotenv import load_dotenv
from typing import Dict, Any
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type

# This module implements the client for the Alphavantage API.
# (MDS Section 5.2)
API_BASE_URL = "https://www.alphavantage.co/query"

load_dotenv()
API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")

RETRY_DECORATOR = retry(
    stop=stop_after_attempt(3),
    wait=wait_fixed(5),
    retry=retry_if_exception_type((httpx.RequestError, httpx.HTTPStatusError)),
    reraise=True
)

@RETRY_DECORATOR
def get_eod_single(symbol: str) -> Dict[str, Any]:
    """
    Fetches the latest quote for a single symbol from the Alphavantage API.
    This is designed for mutual funds and other assets not covered by the primary provider.
    """
    if not API_KEY or len(API_KEY) < 10 or "YOUR_API_KEY_HERE" in API_KEY:
        print(f"[Alphavantage Provider] CRITICAL: API key is not configured for symbol {symbol}.")
        return {"error": "ALPHA_VANTAGE_API_KEY is not set correctly."}

    params = {
        "function": "GLOBAL_QUOTE",
        "symbol": symbol.upper(),
        "apikey": API_KEY
    }

    try:
        with httpx.Client() as client:
            print(f"[Alphavantage Provider] Connecting to endpoint for {symbol}...")
            response = client.get(API_BASE_URL, params=params, timeout=15.0)
            response.raise_for_status()
            data = response.json()

        # Alphavantage has several response formats for errors/rate limits.
        if "Global Quote" in data and data["Global Quote"] and "05. price" in data["Global Quote"]:
            return {
                "symbol": data["Global Quote"].get('01. symbol', symbol),
                "price": float(data["Global Quote"]['05. price']),
                "source": "Alphavantage API"
            }
        elif "Note" in data:
             # This is their rate limit message
             print(f"[Alphavantage Provider] API Error for {symbol}: {data['Note']}")
             return {"error": data['Note']}
        elif "Information" in data:
             # This is often an invalid key or call format message
             print(f"[Alphavantage Provider] API Error for {symbol}: {data['Information']}")
             return {"error": data['Information']}
        else:
            error_message = "Invalid or empty response from API."
            print(f"[Alphavantage Provider] API Error for {symbol}: {error_message}")
            return {"error": error_message, "data": data}

    except httpx.HTTPStatusError as e:
        error_text = e.response.text
        print(f"[Alphavantage Provider] HTTP Error for {symbol}: {e.response.status_code} - {error_text}")
        return {"error": f"API returned status {e.response.status_code}"}
    except httpx.RequestError as e:
        print(f"[Alphavantage Provider] Network Error for {symbol}: {e}")
        return {"error": "A network error occurred."}
    except Exception as e:
        print(f"[Alphavantage Provider] An unexpected error occurred for {symbol}: {e}")
        return {"error": "An unexpected error occurred."}
