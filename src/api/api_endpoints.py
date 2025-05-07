from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Body, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import asyncio
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

@app.get("/player/{player_id}/state")
def get_world_state(player_id: str):
    """
    Returns the game state relative to a specific player's perspective.
    
    It fetches a view of the game world (including nearby objects, player state, etc.)
    that is relative to the specified player.
    
    Args:
        player_id (str): The identifier of the player.
    
    Returns:
        dict: Relative game state or error if the player is not found.
    
    Raises:
        HTTPException: If the player is not found.
    """
    if player_id not in game_world_instance.players:
        raise HTTPException(status_code=404, detail="Player not found")
    try:
        state = game_world_instance.get_relative_state_for_player(player_id)
        return state
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": str(e)})

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
    initial_state = game_world_instance.to_dict()
    return {"player_id": player_id, "initial_state": initial_state}

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

