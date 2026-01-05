#!/bin/bash
# This script starts the backend server for the 'trust' project.
# It will first kill any process already running on the specified port.
echo "--- Starting Curie Trust Backend Server ---"

PORT=8000

# Find the process ID (PID) listening on the port
PID=$(lsof -t -i:$PORT)

# If a PID is found, terminate the process
if [ -n "$PID" ]; then
    echo "Found existing process on port $PORT with PID $PID. Terminating..."
    kill -9 $PID
    sleep 1 # Give a moment for the OS to release the port
else
    echo "No existing process found on port $PORT. Starting fresh."
fi

# This assumes the script is run from the repository root.
cd projects/trust

# Check for a virtual environment and activate it
if [ -d ".venv" ]; then
    echo "Activating virtual environment: .venv"
    source .venv/bin/activate
elif [ -d "venv" ]; then
    echo "Activating virtual environment: venv"
    source venv/bin/activate
else
    echo "Warning: No virtual environment found (.venv or venv). Using system Python."
fi

# Launch the uvicorn server with hot-reloading
echo "Launching uvicorn with --reload on http://127.0.0.1:$PORT..."
uvicorn src.main:app --reload --host 127.0.0.1 --port $PORT

echo "--- Backend server process terminated. ---"