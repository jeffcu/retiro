#!/bin/bash
# This script starts the backend server for the 'trust' project.
# It will first kill any process already running on the specified port.
# This script is designed to be run from WITHIN the projects/trust directory.
echo "--- Starting Curie Trust Backend Server ---"

PORT=8000

# Find and terminate any process(es) listening on the port.
# This version uses a more robust method to handle multiple PIDs.
PIDS=$(lsof -t -i:$PORT)
if [ -n "$PIDS" ]; then
    # The tr command replaces newlines with spaces for cleaner logging.
    echo "Found existing process(es) on port $PORT with PID(s): $(echo $PIDS | tr '\n' ' '). Terminating..."
    # Pipe the PIDs to xargs to kill them all reliably.
    echo "$PIDS" | xargs kill -9
    sleep 1 # Give a moment for the OS to release the port
else
    echo "No existing process found on port $PORT. Starting fresh."
fi


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
