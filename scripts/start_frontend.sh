#!/bin/bash
# This script starts the front-end dev server for the 'trust' project.
# It will first kill any process already running on the specified port.
# This script is designed to be run from WITHIN the projects/trust directory.
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

# Always ensure dependencies are up to date
echo "Checking and installing dependencies..."
npm install

# Launch the Vite dev server
# The --port flag ensures it uses the port we cleared.
echo "Launching 'npm run dev' on http://localhost:$PORT..."
npm run dev -- --port $PORT

echo "--- Vite dev server process terminated. ---"