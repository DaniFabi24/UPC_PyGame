from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Body, HTTPException, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import time
from src.core.game_world import game_world_instance
from ..settings import PHYSICS_DT

app = FastAPI()

# Allow cross-origin requests (useful for client/websocket connections)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        # Allow requests from any origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Cooldown Management ---
# Einfache In-Memory-Speicherung für Cooldowns. Für Produktion ggf. Redis o.ä. verwenden.
# Struktur: { "player_id": { "endpoint_name": last_call_timestamp }}
player_cooldowns = {}

# Cooldown-Dauern in Sekunden
COOLDOWN_SCAN_ENVIRONMENT = 0.5
COOLDOWN_PLAYER_STATE = 0.5
COOLDOWN_GAME_STATE = 0.5
COOLDOWN_SHOOT = 0.1

def check_cooldown(player_id: str, endpoint_name: str, cooldown_duration: float):
    """Prüft und aktualisiert den Cooldown für einen Spieler und Endpunkt."""
    now = time.time()
    if player_id not in player_cooldowns:
        player_cooldowns[player_id] = {}

    last_call = player_cooldowns[player_id].get(endpoint_name, 0)

    if now - last_call < cooldown_duration:
        remaining_cooldown = cooldown_duration - (now - last_call)
        raise HTTPException(
            status_code=429, # Too Many Requests
            detail=f"Cooldown active: {endpoint_name}. Wait {remaining_cooldown:.2f} seconds."
        )
    player_cooldowns[player_id][endpoint_name] = now
    return True # Cooldown bestanden

@app.on_event("startup")
async def startup_event():
    """
    Startup event handler that starts the physics engine.
    
    This event runs when the FastAPI application starts. It initializes and starts the 
    physics loop (using PHYSICS_DT as the delta time) in the game world.
    """
    print("Startup event: Starting physics engine")
    game_world_instance.start_physics_engine(dt=PHYSICS_DT)
    print("Startup event: Physics engine successfully started")

@app.get("/")
def read_root():
    """
    Root endpoint.
    
    Returns a simple welcome message to indicate that the API is running.
    """
    return {"message": "Welcome to the UPC Game API with WebSockets!"}

@app.get("/player/{player_id}/scan")
async def get_scan_environment(player_id: str):
    check_cooldown(player_id, "scan_environment", COOLDOWN_SCAN_ENVIRONMENT)
    scan_data = game_world_instance.scan_environment(player_id)
    if scan_data is None:
        pass
    return scan_data

@app.get("/player/{player_id}/state")
async def get_player_own_state(player_id: str):
    check_cooldown(player_id, "state", COOLDOWN_PLAYER_STATE)
    state_data = game_world_instance.player_state(player_id)
    if state_data is None:
        raise HTTPException(status_code=404, detail=f"Player {player_id} not found or no state available.")
    return state_data

@app.get("/player/{player_id}/game-state")
async def get_overall_game_state(player_id: str):
    check_cooldown(player_id, "game_state", COOLDOWN_GAME_STATE)
    state_data = game_world_instance.game_state(player_id)
    if state_data is None:
        raise HTTPException(status_code=404, detail=f"Could not retrieve game state for player {player_id}.")
    return state_data

@app.post("/player/ready/{player_id}")
async def ready_to_play(player_id: str):
    """
    Args:
        player_id (str): The identifier of the player.
    
    Returns:
    
    Raises:
        HTTPException: If the player is not found.
    """
    if player_id not in game_world_instance.players:
        raise HTTPException(status_code=404, detail="Player not found")
    game_world_instance.player_ready(player_id)
    return {"message": f"Player {player_id} is ready to play"}

@app.post("/connect")
async def connect_player():
    """
    Connects a new player to the game.
    
    This endpoint adds a new player to the game world, assigns a unique player ID, and returns
    an initial snapshot of the game state.
    
    Returns:
        dict: Contains the new player's ID and the initial game state.
    """
    player_id = game_world_instance.add_player()
    return {"player_id": player_id}

@app.post("/disconnect/{player_id}")
async def disconnect_player(player_id: str):
    """
    Disconnects a player from the game.
    
    Removes the specified player from the game world.
    
    Args:
        player_id (str): The unique identifier of the player.
    
    Returns:
        dict: A message confirming that the player was disconnected.
    
    Raises:
        HTTPException: If the player is not found.
    """
    if player_id not in game_world_instance.players:
        raise HTTPException(status_code=404, detail="Player not found")
    game_world_instance.remove_player(player_id)
    return {"message": f"Player {player_id} disconnected"}

@app.post("/player/{player_id}/thrust_forward")
async def thrust_forward(player_id: str):
    """
    Applies forward thrust to the specified player.
    
    This will increase the player's velocity in the direction they are currently facing.
    
    Args:
        player_id (str): The identifier of the player.
    
    Returns:
        dict: A message confirming the thrust action.
    
    Raises:
        HTTPException: If the player is not found.
    """
    if player_id not in game_world_instance.players:
        raise HTTPException(status_code=404, detail="Player not found")
    game_world_instance.positive_player_thrust(player_id)
    return {"message": f"Player {player_id} thrust forward"}

@app.post("/player/{player_id}/rotate_right")
async def rotate_right(player_id: str):
    """
    Rotates the specified player to the right.
    
    Args:
        player_id (str): The identifier of the player.
    
    Returns:
        dict: A message confirming the rotation action.
    
    Raises:
        HTTPException: If the player is not found.
    """
    if player_id not in game_world_instance.players:
        raise HTTPException(status_code=404, detail="Player not found")
    game_world_instance.right_player_rotation(player_id)
    return {"message": f"Player {player_id} rotated right"}

@app.post("/player/{player_id}/shoot")
async def shoot(player_id: str):
    """
    Initiates a shooting action for the specified player.
    
    A projectile is created and added to the game world.
    
    Args:
        player_id (str): The identifier of the player who is shooting.
    
    Returns:
        dict: A message confirming that the player has shot.
    
    Raises:
        HTTPException: If the player is not found.
    """
    if player_id not in game_world_instance.players:
        raise HTTPException(status_code=404, detail="Player not found")
    check_cooldown(player_id, "shoot", COOLDOWN_SHOOT)
    game_world_instance.shoot(player_id)
    return {"message": f"Player {player_id} shot"}

@app.post("/player/{player_id}/thrust_backward")
async def thrust_backward(player_id: str):
    """
    Applies backward thrust (braking) to the specified player.
    
    Args:
        player_id (str): The identifier of the player.
    
    Returns:
        dict: A confirmation message.
    
    Raises:
        HTTPException: If the player is not found.
    """
    if player_id not in game_world_instance.players:
        raise HTTPException(status_code=404, detail="Player not found")
    game_world_instance.negative_player_thrust(player_id)
    return {"message": f"Player {player_id} thrust backward"}

@app.post("/player/{player_id}/rotate_left")
async def rotate_left(player_id: str):
    """
    Rotates the specified player to the left.
    
    Args:
        player_id (str): The identifier of the player.
    
    Returns:
        dict: A message confirming the left rotation.
    
    Raises:
        HTTPException: If the player is not found.
    """
    if player_id not in game_world_instance.players:
        raise HTTPException(status_code=404, detail="Player not found")
    game_world_instance.left_player_rotation(player_id)
    return {"message": f"Player {player_id} rotated left"}

