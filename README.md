# UPC_PyGame Simulation

[![Python Version](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/)
[![Framework](https://img.shields.io/badge/Framework-FastAPI-green.svg)](https://fastapi.tiangolo.com/)
[![Physics](https://img.shields.io/badge/Physics-Pymunk-orange.svg)](http://www.pymunk.org/)
[![Graphics](https://img.shields.io/badge/Graphics-Pygame-red.svg)](https://www.pygame.org/)

## Overview

UPC_PyGame is a 2D multiplayer arena shooter simulation. This project integrates a robust FastAPI server to manage the game state and employs the Pymunk physics engine for realistic interactions within the game world. Players are represented by autonomous agents that connect to the server via a straightforward HTTP API, allowing them to control their unique spacecraft. A Pygame-based visualizer provides a real-time graphical representation of the arena, displaying the dynamic interactions between players, obstacles, and projectiles.

## Game Rules

The objective is to be the last surviving player in the arena.

* **Setup:** Players connect as agents to control their unique, colored triangular spacecraft. The arena is populated with static circular obstacles and is enclosed by reflective energy boundaries.
* **Game Start:** Once all connected players in the pre-game lobby have indicated their readiness to compete, the game server initiates a countdown sequence, signaling the imminent start of the match.
* **Gameplay:** Players pilot their spacecraft using directional thrust for movement and rotational commands for aiming. Skillful navigation is crucial to avoid collisions with both the static obstacles scattered throughout the arena and the dynamic boundaries that enclose the play space. Strategic positioning is key to engaging opposing players effectively.
* **Combat:** The primary form of interaction between players is through the firing of colored energy projectiles. These projectiles travel in a straight line from the firing player's spacecraft. Direct hits on an opponent's spacecraft inflict damage, gradually reducing their overall health. To ensure a fair initial engagement, a temporary period of invulnerability and shooting restriction is applied immediately after a player enters the arena (spawn protection).
* **Elimination:** When a player's spacecraft sustains enough damage to deplete their health to zero, they are considered eliminated from the current game round. Their agent will no longer be able to control their spacecraft.
* **Winning:** The victor of a game round is the final player whose spacecraft remains operational (i.e., with health greater than zero) after all other players have been eliminated.

## Features

* **Multiplayer Support:** Facilitates simultaneous participation of numerous players, each controlled by an independent agent.
* **Realistic 2D Physics:** Leverages the Pymunk library to simulate accurate and responsive movement, collisions, and ricochets for all interactive elements within the game.
* **Intuitive HTTP API:** Offers a straightforward and well-documented interface built with FastAPI, enabling agents to easily send control commands and receive comprehensive game state updates.
* **Real-time Visualizer:** Provides a dynamic Pygame-based graphical representation of the game arena, allowing for immediate observation of all in-game actions and states.
* **Distinct Player Entities:** Features uniquely colored, triangular spacecraft for each player, enhancing visual clarity and identification within the arena.
* **Projectile-Based Combat:** Implements a core combat mechanic where players can launch colored projectiles to engage and damage opponents.
* **Strategic Obstacles:** Populates the arena with static circular obstacles that serve as both tactical cover and navigational challenges.
* **Dynamic Arena Boundaries:** Defines the play area with energy field boundaries that cause spacecraft and projectiles to bounce realistically upon contact.
* **Comprehensive Relative State Information:** Equips agents with detailed sensory data about their immediate surroundings, including the position, velocity, and type of nearby entities.
* **Pre-Game Readiness System:** Ensures all participating players are prepared before a match begins through a mandatory readiness signaling mechanism.
* **Initial Spawn Protection:** Grants newly spawned players a temporary period of invulnerability and firing restriction to prevent immediate elimination.

## Architecture

The system consists of three main components:

1.  **Game Server (FastAPI + Pymunk):**
    *   Located in `src/api/` and `src/core/`.
    *   Manages the core game loop, physics simulation (`GameWorld`), and object states (`game_objects.py`).
    *   Exposes an HTTP API (`api_endpoints.py`) for agent interaction.
    *   Started via `main.py`.
2.  **Visualizer (Pygame):**
    *   Integrated within `src/core/game_world.py` (`run_visualizer` method).
    *   Reads the state directly from the `game_world_instance`.
    *   Renders the game graphically.
    *   Launched by `main.py` in the main thread after the server starts.
3.  **Agent (Client):**
    *   Example implementation: [`dummy_agent.py`](.\dummy_agent.py).
    *   Connects to the FastAPI server via HTTP requests (`requests` library).
    *   Sends control commands (thrust, rotate, shoot) to the API.
    *   Receives relative game state information from the API.
    *   Must be run as a separate process *after* `main.py` has started the server.

## Installation

1.  **Clone the Repository (if you haven't already):**
    ```bash
    git clone git@github.com:DaniFabi24/UPC_PyGame.git
    ```
2.  **Create and Activate a Virtual Environment:**
    Open your terminal in the project root (where [`requirements.txt`](.\requirements.txt) is located) and run:
    ```bash
    # Using python's built-in venv module
    python -m venv venv
    # Activate the environment
    # On Linux/macOS:
    source venv/bin/activate
    # On Windows (Command Prompt/PowerShell):
    .\venv\Scripts\activate
    ```
3.  **Install Dependencies:**
    With the virtual environment activated, install the required packages:
    ```bash
    pip install -r requirements.txt
    ```

## Running the Simulation

You have two main ways to run the simulation: all at once using the `run_game.sh` script, or step by step by manually launching the server and then the agents.

### Running the Simulation at once (with `run_game.sh`)

This script provides a convenient way to start the entire simulation, including the server, visualizer, and a specified number of agents, in one go.

1.  **Ensure the script is executable:**
    ```bash
    chmod +x run_game.sh
    ```
    (You only need to do this once.)

2.  **Run the game:**
    ```bash
    ./run_game.sh
    ```
    After launching, the script will first print "Starting game (main.py)..." and start the FastAPI server and Pygame visualizer in the background. It will then pause for 8 seconds to allow the server sufficient time to initialize.

3.  **Enter the number of agents:**
    You will be prompted with the message "How many agents do you want to start? ". Enter the desired number of agents and press Enter.

4.  **Agent startup:**
    The script will then proceed to start the specified number of `dummy_agent.py` instances in the background. Each agent will connect to the running game server.

5.  **Termination:**
    The script will wait for the `main.py` process (server and visualizer) to finish before the `run_game.sh` script itself terminates. You can typically close the visualizer window to end the entire simulation.

### Running the Simulation step by step

This method allows for more control over the startup process and is useful for debugging or when you want to start agents individually.

1.  **Start the Server and Visualizer:**
    Open a terminal in the project root (where `main.py` is located) and run the main script:
    ```bash
    python main.py
    ```
    Wait for the console output indicating the server is running and the visualizer window to appear. The server runs in a background thread initiated by `main.py`, and the visualizer runs in the main thread.

2.  **Run Agent(s):**
    *After* the server and visualizer are running, open one or more *separate* terminal windows (ensure the virtual environment is activated in each). In each terminal, navigate to the project root and run the dummy agent script:
    ```bash
    python dummy_agent.py
    ```
    Each execution of this command will connect a new agent/player to the already running game server. You can run this command multiple times to add more agents.


## Agent Control (`dummy_agent.py`)

The `dummy_agent.py` script uses a Pygame window to capture key presses and send corresponding actions to the server.

* **Spacebar:** Shoot a projectile.
* **Arrow Up:** Apply forward thrust.
* **Arrow Down:** Apply backward thrust (brake/reverse).
* **Arrow Left:** Rotate the player left.
* **Arrow Right:** Rotate the player right.
* **Enter Key:** Request and print the current relative game state from the `/player/{player_id}/scan` endpoint to the agent's console.
* **Right Shift Key:** Send a "ready" signal to the server (`/player/ready/{player_id}`).
* **Left Shift Key:** Request and print the current game state from the `/player/{player_id}/game-state` endpoint to the agent's console.
* **Left Control Key:** Request and print the player's state from the `/player/{player_id}/state` endpoint to the agent's console.

## API Overview

The FastAPI server exposes the following key endpoints for agent interaction (base URL defined in [`src/settings.py`](.\src\settings.py)):

* `POST /connect`: Connects a new agent, returns a unique `player_id`.
* `POST /disconnect/{player_id}`: Disconnects the specified player.
* `GET /player/{player_id}/state`: Retrieves the player's specific state (includes velocity, health, etc.).
* `GET /player/{player_id}/game-state`: Retrieves the overall state of the game (e.g., other players, obstacles).
* `GET /player/{player_id}/scan`: Retrieves the game state relative to the specified player (includes nearby objects, velocity, health).
* `POST /player/{player_id}/thrust_forward`: Applies forward thrust.
* `POST /player/{player_id}/thrust_backward`: Applies backward thrust.
* `POST /player/{player_id}/rotate_left`: Applies left rotation torque.
* `POST /player/{player_id}/rotate_right`: Applies right rotation torque.
* `POST /player/{player_id}/shoot`: Fires a projectile.
* `POST /player/ready/{player_id}`: Signals that a player is ready to start a game (potentially for future game modes).

*(Refer to [`src/api/api_endpoints.py`](.\src\api\api_endpoints.py) for implementation details)*

## Configuration

Key game parameters can be adjusted in [`src/settings.py`](.\src\settings.py), including:

*   API host and port.
*   Screen dimensions and FPS.
*   Physics settings (timestep).
*   Player movement forces, rotation speed, max speed, health, scan radius.
*   Projectile speed, radius, lifetime, damage.

## Competition Instructions

*   **Objective:** Be the last player surviving in the arena. This is a free-for-all deathmatch.
*   **Agent Development:** Modify [`dummy_agent.py`](.\dummy_agent.py) or create your own agent script that interacts with the game server via the defined HTTP API.
*   **Focus:** Your agent should make decisions based on the relative state information received from the `/player/{player_id}/state` endpoint.
*   **Code Standards:** Ensure your agent code is readable and connects/interacts correctly with the provided server API.
*   **Evaluation:** Agents will be evaluated based on functionality (correct interaction), performance (efficiency in processing state and reacting), survival time, and potentially strategic innovation (use of environment, aiming).
*   **Submission:** Submit your agent script (`.py` file) along with a brief description of its strategy.


## Contributing

Feel free to report issues or suggest improvements using the templates provided in the `.github` directory:

*   **Issues:** [`general_issue.md`](/.github/ISSUE_TEMPLATE/general_issue.md)
*   **Discussions:** [`general_discussion.md`](.github/DISCUSSIONS_TEMPLATE/general_discussion.md)
