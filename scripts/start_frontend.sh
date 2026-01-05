#!/bin/bash
# This script starts the front-end dev server for the 'trust' project.
# It will first kill any process already running on the specified port.
echo "--- Starting Curie Trust Front End (Vite Dev Server) ---"

PORT=5173

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

# Check if node_modules exists, advise if not.
if [ ! -d "node_modules" ]; then
  echo "Warning: 'node_modules' directory not found. Please run 'npm install' first."
fi

# Launch the Vite dev server
# The --port flag ensures it uses the port we cleared.
echo "Launching 'npm run dev' on http://localhost:$PORT..."
npm run dev -- --port $PORT

echo "--- Vite dev server process terminated. ---"