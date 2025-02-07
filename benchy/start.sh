#!/bin/bash

# Start the dev server in the background
bun run dev &

# Change directory and start Python server
cd server && uv run python server.py

# Wait for both processes
wait
