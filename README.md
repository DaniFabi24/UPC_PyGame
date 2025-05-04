# UPC_PyGame

UPC_PyGame is a 2D game simulation developed as part of the Python course at UPC_ETSEIB. It combines a FastAPI server managing the physics engine and game logic with a Pygame visualizer and a dummy agent for testing. Although the project may not be super polished, it is a complete system for demonstration and competition purposes.

## Demo Launch

To launch the entire system, follow these steps:
1. **Start the API Server and Physics Engine:**  
   Run the `main.py` file. This will start the FastAPI server (using Uvicorn) in a background thread. The physics engine is initialized via FastAPI's startup event.
2. **Run the Dummy Agent:**  
   A dummy agent is provided in `dummy_agent.py`. It connects to the server, sends control actions (such as moving, rotating, or shooting), and polls for the game state.
3. **Open the Visualizer:**  
   The Pygame visualizer (managed by the game world instance in `src/core/game_world.py`) shows the current state of the arena, including players and obstacles. The visualizer launches after the API server has initialized.

You can launch the demo by running:
```bash
python main.py
```
This will concurrently start the API server, the game world and the visualizer.

After launching the demo with `python main.py`, open multiple different terminals and run:
```bash
python dummy_agent.py
```
This will automatically connect the agent to the server and creates a player who is ready to play by pressing the keys:

Spacebar: Shoot
Arrow Up/Down: Thrust forward/backward
Arrow Left/Right: Rotate the player left/right
Enter Key: Poll and display the current relative game state in the console

## Installation

1. **Create and Activate a Virtual Environment:**  
   Open your terminal in the project root (where `requirements.txt` is located) and run:
   ```bash
   python3 -m venv venv
   source venv/bin/activate   # On Linux/macOS
   # On Windows, use: venv\Scripts\activate
   ```
2. **Install Dependencies:**  
   With the virtual environment activated, install the required packages:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

1. **Launch the System:**  
   Start the demo by executing:
   ```bash
   python main.py
   ```
   This will start the API server, launch the dummy agent, and open the Pygame visualizer.
2. **Control the Dummy Agent:**  
   - **Spacebar:** Shoot  
   - **Arrow Keys:**  
     - Up and Down for thrust forward or backward  
     - Left and Right to rotate the player  
   - **Enter Key:** Poll and display the current relative game state in the console.
3. **Observing the Visualizer:**  
   The visualizer window displays the game arena with players, obstacles and projectiles. Health bars and other visual feedback help track the game state.

## Competition Instructions

For competition purposes:
- **Agent Submission:**  
  Participants can develop their own agent by modifying or creating new versions of `dummy_agent.py`. Make sure your agent connects to the existing API endpoints and follows the control commands (thrust, rotate, shoot) protocol.
- **Game Type:**  
  This is a multiplayer, every-against-everyone shooter. The objective is to be the last survivor in the arena.
- **Code Standards:**  
  Keep your code modular and focused on API communication using FastAPI. Your agent should operate independently and be thoroughly tested with the provided game server.
- **Evaluation Criteria:**  
  - **Functionality:** Your agent must successfully connect, control, and retrieve game state information.  
  - **Performance:** Agents that efficiently process game state and respond to control commands will be favored.  
  - **Innovation:** Creative strategies for navigating the arena, collecting power-ups, and engaging opponents can earn bonus recognition.
- **Submission:**  
  Submit your modified agent code along with a brief explanation of your strategy and any improvements made over the dummy agent implementation.

Happy coding, and may the best agent win!
Happy coding, and may the best agent win!
