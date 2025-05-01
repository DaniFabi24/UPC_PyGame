from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Body, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import asyncio
from src.core.game_world import game_world_instance
from ..settings import PHYSICS_DT

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    print("Startup event: Starte Physik-Engine")
    game_world_instance.start_physics_engine(dt=PHYSICS_DT)
    print("Startup event: Physik-Engine wurd eerfolgreich gestartet")

@app.get("/")
def read_root():
    return {"message": "Welcome to the UPC Game API with WebSockets!"}

@app.get("/world_state")
def get_world_state():
    try:
        state = game_world_instance.to_dict()
        return state
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": str(e)})

@app.post("/connect")
async def connect_player():
    """Connects a new player and returns their ID."""
    player_id = game_world_instance.add_player()
    # Optional: Initialen Spielzustand mitsenden
    initial_state = game_world_instance.to_dict()
    return {"player_id": player_id, "initial_state": initial_state}

@app.post("/disconnect/{player_id}")
async def disconnect_player(player_id: str):
    """Disconnects a player."""
    if player_id not in game_world_instance.players:
         raise HTTPException(status_code=404, detail="Player not found")
    game_world_instance.remove_player(player_id)
    return {"message": f"Player {player_id} disconnected"}

@app.post("/player/{player_id}/thrust_forward")
async def thrust_forward(player_id: str):
    if player_id not in game_world_instance.players:
         raise HTTPException(status_code=404, detail="Player not found")
    game_world_instance.positive_player_thrust(player_id)
    return {"message": f"Player {player_id} thrust forward"}

@app.post("/player/{player_id}/rotate_right")
async def rotate_right(player_id: str):
    if player_id not in game_world_instance.players:
         raise HTTPException(status_code=404, detail="Player not found")
    game_world_instance.right_player_rotation(player_id)
    return {"message": f"Player {player_id} rotated right"}

@app.post("/player/{player_id}/shoot")
async def shoot(player_id: str):
    if player_id not in game_world_instance.players:
         raise HTTPException(status_code=404, detail="Player not found")
    game_world_instance.shoot(player_id)
    return {"message": f"Player {player_id} shot"}

@app.post("/player/{player_id}/thrust_backward")
async def thrust_backward(player_id: str):
    if player_id not in game_world_instance.players:
         raise HTTPException(status_code=404, detail="Player not found")
    game_world_instance.negative_player_thrust(player_id)
    return {"message": f"Player {player_id} thrust backward"}

@app.post("/player/{player_id}/rotate_left")
async def rotate_left(player_id: str):
    if player_id not in game_world_instance.players:
         raise HTTPException(status_code=404, detail="Player not found")
    game_world_instance.left_player_rotation(player_id)
    return {"message": f"Player {player_id} rotated left"}

