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

@app.post("/thrust_forward")
def thrust_player_positive():
    try:
        game_world_instance.positive_player_thrust()
        return {"message": "Spieler wurde in Blickrichtung beschleunigt"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": str(e)})

@app.post("/thrust_backward")
def thrust_player_negative():
    try:
        game_world_instance.negative_player_thrust()
        return {"message": "Spieler wurde gegen Blickrichtung beschleunigt"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": str(e)})
    
@app.post("/rotate_right")
def rotate_player_right():
    try:
        game_world_instance.right_player_rotation()
        return {"message": "Spieler wurde nach rechts gedreht"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": str(e)})
    
@app.post("/rotate_left")
def rotate_player_left():
    try:
        game_world_instance.left_player_rotation()
        return {"message": "Spieler wurde nach links gedreht"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": str(e)})

@app.post("/shoot")
async def shoot():
    """Triggers the player to shoot a projectile."""
    if game_world_instance.player:
        game_world_instance.shoot()
        return {"message": "Shoot command received"}
    else:
        raise HTTPException(status_code=404, detail="Player not found")

