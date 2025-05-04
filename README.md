# UPC_PyGame Simulation

[![Python Version](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/)
[![Framework](https://img.shields.io/badge/Framework-FastAPI-green.svg)](https://fastapi.tiangolo.com/)
[![Physics](https://img.shields.io/badge/Physics-Pymunk-orange.svg)](http://www.pymunk.org/)
[![Graphics](https://img.shields.io/badge/Graphics-Pygame-red.svg)](https://www.pygame.org/)

## Overview

UPC_PyGame is a 2D multiplayer arena shooter simulation developed as part of the Python course at UPC_ETSEIB. It features a FastAPI-based server that manages the game state and physics simulation using Pymunk. Agents connect via an HTTP API to control their players, while a Pygame-based visualizer displays the real-time state of the game world.

This project serves as a demonstration platform and a basis for agent-based competitions.

## Features

*   **Multiplayer:** Supports multiple agents connecting and controlling players simultaneously.
*   **Physics Simulation:** Uses the Pymunk 2D physics library for realistic movement, collisions, and bouncing.
*   **API Control:** Agents interact with the game world through a simple HTTP API built with FastAPI.
*   **Real-time Visualization:** A Pygame window displays the current state of the arena, including players, obstacles and projectiles.
*   **Player Mechanics:**
    *   Triangle-shaped players with unique colors.
    *   Health system with damage from projectiles and obstacles (obstacle damage currently disabled in handler).
    *   Spawn protection period.
    *   Ability to shoot projectiles (colored based on the player).
*   **Game Elements:**
    *   Static circular obstacles.
    *   Arena boundaries.
*   **Relative State Information:** Agents can query the game state relative to their own position and orientation.

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
    *   Example implementation: [`dummy_agent.py`](c:\_Bibliothek\UPC_PyGame\dummy_agent.py).
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
    Open your terminal in the project root (where [`requirements.txt`](c:\_Bibliothek\UPC_PyGame\requirements.txt) is located) and run:
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

1.  **Start the Server and Visualizer:**
    Run the main script. This starts the FastAPI server in a background thread and then launches the Pygame visualizer in the main thread.
    ```bash
    python main.py
    ```
    Wait for the console output indicating the server is running and the visualizer window to appear.

2.  **Run Agent(s):**
    *After* the server and visualizer are running, open one or more *separate* terminal windows (ensure the virtual environment is activated in each). In each terminal, run the dummy agent script:
    ```bash
    python dummy_agent.py
    ```
    Each execution will connect a new agent/player to the game.

## Agent Control (`dummy_agent.py`)

Use the following keys in the Pygame window created by `dummy_agent.py` to control your player:

*   **Spacebar:** Shoot a projectile.
*   **Arrow Up:** Apply forward thrust.
*   **Arrow Down:** Apply backward thrust (brake/reverse).
*   **Arrow Left:** Rotate the player left.
*   **Arrow Right:** Rotate the player right.
*   **Enter Key:** Request and print the current relative game state to the agent's console.

## API Overview

The FastAPI server exposes the following key endpoints for agent interaction (base URL defined in [`src/settings.py`](c:\_Bibliothek\UPC_PyGame\src\settings.py)):

*   `POST /connect`: Connects a new agent, returns a unique `player_id`.
*   `POST /disconnect/{player_id}`: Disconnects the specified player.
*   `GET /player/{player_id}/state`: Retrieves the game state relative to the specified player (includes nearby objects, velocity, health).
*   `POST /player/{player_id}/thrust_forward`: Applies forward thrust.
*   `POST /player/{player_id}/thrust_backward`: Applies backward thrust.
*   `POST /player/{player_id}/rotate_left`: Applies left rotation torque.
*   `POST /player/{player_id}/rotate_right`: Applies right rotation torque.
*   `POST /player/{player_id}/shoot`: Fires a projectile.

*(Refer to [`src/api/api_endpoints.py`](c:\_Bibliothek\UPC_PyGame\src\api\api_endpoints.py) for implementation details)*

## Configuration

Key game parameters can be adjusted in [`src/settings.py`](c:\_Bibliothek\UPC_PyGame\src\settings.py), including:

*   API host and port.
*   Screen dimensions and FPS.
*   Physics settings (timestep).
*   Player movement forces, rotation speed, max speed, health, scan radius.
*   Projectile speed, radius, lifetime, damage.

## Competition Instructions

*   **Objective:** Be the last player surviving in the arena. This is a free-for-all deathmatch.
*   **Agent Development:** Modify [`dummy_agent.py`](c:\_Bibliothek\UPC_PyGame\dummy_agent.py) or create your own agent script that interacts with the game server via the defined HTTP API.
*   **Focus:** Your agent should make decisions based on the relative state information received from the `/player/{player_id}/state` endpoint.
*   **Code Standards:** Ensure your agent code is readable and connects/interacts correctly with the provided server API.
*   **Evaluation:** Agents will be evaluated based on functionality (correct interaction), performance (efficiency in processing state and reacting), survival time, and potentially strategic innovation (use of environment, aiming).
*   **Submission:** Submit your agent script (`.py` file) along with a brief description of its strategy.


## Contributing

Feel free to report issues or suggest improvements using the templates provided in the `.github` directory:

*   **Issues:** [`general_issue.md`](/.github/DISCUSSIONS_TEMPLATE/ISSUE_TEMPLATE/general_issue.md)
*   **Discussions:** [`general_discussion.md`](.github/DISCUSSIONS_TEMPLATE/general_discussion.md)