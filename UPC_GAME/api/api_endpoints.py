from fastapi import FastAPI, APIRouter
from pydantic import BaseModel
from ..core.game_world import GameWorld
from ..core.game_objects import Triangle
import asyncio

app = FastAPI()
router = APIRouter()

# Create a global game world instance
game_world = GameWorld(800, 600)
game_world.initialize_world() # Initialize the world with objects

# Start the physics engine asynchronously on API startup
@app.on_event("startup")
async def startup_event():
    game_world.start_physics_engine()

@app.on_event("shutdown")
async def shutdown_event():
    game_world.stop_physics_engine()

class MoveCommand(BaseModel):
    thrust: float = 0
    rotation: float = 0

class ShootCommand(BaseModel):
    pass # No parameters for shooting in this simple version

@router.post("/move")
async def move_player(command: MoveCommand):
    game_world.set_player_thrust(command.thrust)
    game_world.set_player_rotation(command.rotation)
    return {"status": "moving", "thrust": command.thrust, "rotation": command.rotation}

@router.post("/shoot")
async def shoot():
    if game_world.player:
        return {"status": "shot"} # Implement shooting logic later
    return {"status": "error", "message": "Player not found"}

@router.get("/player_status")
async def get_player_status():
    if game_world.player:
        return {
            "position": game_world.player.position,
            "angle": game_world.player.angle
        }
    return {"status": "error", "message": "Player not found"}

@router.get("/world_state")
async def get_world_state():
    objects_data = []
    for obj in game_world.objects:
        if isinstance(obj, Triangle):
            objects_data.append({"type": "triangle", "position": obj.position, "angle": obj.angle})
        elif isinstance(obj, CircleObstacle):
            objects_data.append({"type": "circle", "position": obj.position, "radius": obj.radius})
    return {"objects": objects_data}

app.include_router(router)