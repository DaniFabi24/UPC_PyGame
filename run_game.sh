#!/bin/bash

# This script starts the UPC_PyGame simulation by launching the server and agents.

# Set PYTHONPATH to include the project root
export PYTHONPATH=$(pwd)

# Start main.py in the background
echo "Starting game (main.py)..."
python3 main.py &
MAIN_PID=$!

# Wait briefly for the server to start
sleep 8

# List available agents in the "agents" folder
AGENTS_DIR="./agents"
echo "Available agents in $AGENTS_DIR:"
AGENT_FILES=$(ls $AGENTS_DIR/agent*.py)
echo "$AGENT_FILES"

# Ask the user to select agents
read -p "Enter the names of the agents to start (separated by spaces, e.g., agent1.py agent2.py): " SELECTED_AGENTS

# Start the selected agents
for AGENT in $SELECTED_AGENTS; do
    AGENT_PATH="$AGENTS_DIR/$AGENT"
    if [[ -f $AGENT_PATH ]]; then
        echo "Starting $AGENT..."
        python3 $AGENT_PATH &
    else
        echo "Error: $AGENT not found in $AGENTS_DIR!"
    fi
done

# Wait for main.py to finish
wait $MAIN_PID