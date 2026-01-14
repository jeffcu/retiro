#!/bin/bash
# This script triggers a bulk refresh of all portfolio holdings using
# yesterday's closing price from the EOD data provider.

echo "--- Sending command to refresh portfolio with End-of-Day prices... ---"

# The API endpoint for the EOD refresh
URL="http://127.0.0.1:8000/api/market-data/refresh-eod"

# Use curl to send a POST request. The API handles this as a background task.
RESPONSE=$(curl -s -X POST "$URL" -H "accept: application/json")

# Check if the response contains 'message', which indicates success
if echo "$RESPONSE" | grep -q '"message"'; then
    echo "SUCCESS: Backend has accepted the request."
    echo "Response from server: $RESPONSE"
    echo "You can monitor the backend logs for progress."
else
    echo "ERROR: Failed to trigger EOD refresh."
    echo "The backend might not be running or the endpoint is wrong."
    echo "Response from server: $RESPONSE"
    exit 1
fi

echo "--- Command sent. ---"
