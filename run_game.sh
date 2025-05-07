#!/bin/bash

# Start main.py in the background
echo "Starting game (main.py)..."
python3 main.py &
MAIN_PID=$!

# Small delay to give the server time to start
sleep 8

# Ask the user how many agents to start
read -p "How many agents do you want to start? " AGENT_COUNT

# Start the agents
for ((i=1; i<=AGENT_COUNT; i++)); do
    echo "Starting agent $i..."
    python3 dummy_agent.py &
done

# Wait for main.py to finish
wait $MAIN_PID
