#!/bin/bash
# Curie Trust Unified Development Environment Startup Script
# This script starts both the Python backend (uvicorn) and the Node.js frontend (vite)
# in the background and foreground, respectively, and ensures graceful shutdown.

# --- Configuration ---
BACKEND_PORT=8000
FRONTEND_PORT=5173
PROJECT_ROOT=$(dirname "$0")

cd "$PROJECT_ROOT/.."

# --- Cleanup Function ---
# This trap ensures that background processes started by this script are killed
# when the user presses Ctrl+C (SIGINT).
function cleanup {
    echo -e "\n--- Shutting down development environment ---"
    
    # Check if backend PID exists and kill it
    if [ ! -z "$BACKEND_PID" ]; then
        echo "Terminating Backend PID $BACKEND_PID..."
        kill $BACKEND_PID 2>/dev/null
    fi
    
    # Ensure all processes on the ports are truly killed
    PIDS=$(lsof -t -i:$BACKEND_PORT -i:$FRONTEND_PORT)
    if [ -n "$PIDS" ]; then
        echo "Terminating residual process(es) on ports $BACKEND_PORT/$FRONTEND_PORT: $(echo $PIDS | tr '\n' ' ')..."
        echo "$PIDS" | xargs kill -9 2>/dev/null
    fi

    wait $BACKEND_PID 2>/dev/null # Wait for the background process to finish if it hasn't
    echo "Cleanup complete."
    exit 0
}

trap cleanup SIGINT SIGTERM

# --- Step 1: Ensure Clean Ports ---
echo "1. Checking and clearing ports $BACKEND_PORT and $FRONTEND_PORT..."
PIDS_TO_KILL=$(lsof -t -i:$BACKEND_PORT -i:$FRONTEND_PORT)
if [ -n "$PIDS_TO_KILL" ]; then
    echo "$PIDS_TO_KILL" | xargs kill -9 2>/dev/null
    sleep 1
fi

# --- Step 2: Set up Python Environment ---
if [ -d ".venv" ]; then
    echo "2. Activating Python virtual environment: .venv"
    source .venv/bin/activate
elif [ -d "venv" ]; then
    echo "2. Activating Python virtual environment: venv"
    source venv/bin/activate
else
    echo "2. Warning: No virtual environment found. Using system Python."
fi

echo "   Synchronizing Python dependencies..."
pip install -r requirements.txt > /dev/null

# --- Step 3: Start Backend (Background) ---
echo "3. Starting backend server on http://0.0.0.0:$BACKEND_PORT..."
# Using --workers 1 to avoid complexity with concurrency/DB locks for now, and --reload for dev ease.
# Scotty: Bind to 0.0.0.0 for LAN access
uvicorn src.main:app --reload --host 0.0.0.0 --port $BACKEND_PORT &

# Capture the PID of the background process
BACKEND_PID=$!
echo "   Backend started with PID $BACKEND_PID."
sleep 3 # Give the backend a moment to spin up

# --- Step 4: Start Frontend (Foreground) ---
echo "4. Starting frontend dev server on http://0.0.0.0:$FRONTEND_PORT..."

# Always ensure dependencies are installed/updated
echo "   Updating Node dependencies via npm install..."
npm install

# Start the Vite server (this blocks the terminal)
# Scotty: Added --host to listen on LAN
npm run dev -- --host --port $FRONTEND_PORT

# Cleanup trap will handle termination after Ctrl+C
