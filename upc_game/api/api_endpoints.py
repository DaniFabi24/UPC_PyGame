from fastapi import FastAPI, APIRouter, HTTPException
from pydantic import BaseModel
import asyncio

game_world = None

try:
    from core.game_world import GameWorld
    from core.game_objects import Triangle, CircleObstacle
    game_world = GameWorld(800, 600)
    game_world.initialize_world()
    game_world.start_physics_engine()
except ImportError as e:
    print(f"ImportError: {e}")
    # Hier könntest du eine entsprechende Fehlerbehandlung implementieren

app = FastAPI()
router = APIRouter()

class MoveCommand(BaseModel):
    thrust: float = 0
    rotation: float = 0

class ShootCommand(BaseModel):
    pass

@router.get("/import_status")
async def check_imports():
    status = {
        "game_world_initialized": game_world is not None,
    }
    if game_world:
        status["world_object_count"] = len(game_world.objects)
    return status

@router.post("/move")
async def move_player(command: MoveCommand):
    if game_world:
        game_world.set_player_thrust(command.thrust)
        game_world.set_player_rotation(command.rotation)
        return {"status": "moving", "thrust": command.thrust, "rotation": command.rotation}
    raise HTTPException(status_code=503, detail="Game world not initialized")

@router.post("/shoot")
async def shoot():
    if game_world and game_world.player:
        game_world.increment_shot_count() # Stelle sicher, dass du die Schusszählung beibehalten willst
        return {"status": "shot"}
    raise HTTPException(status_code=503, detail="Player not found or game world not initialized")

@router.get("/player_status")
async def get_player_status():
    if game_world and game_world.player:
        return {
            "position": game_world.player.position,
            "angle": game_world.player.angle
        }
    raise HTTPException(status_code=503, detail="Player not found or game world not initialized")

@router.get("/world_state")
async def get_world_state():
    if game_world:
        objects_data = []
        for obj in game_world.objects:
            if isinstance(obj, Triangle):
                objects_data.append({"type": "triangle", "position": list(obj.position), "angle": obj.angle})
            elif isinstance(obj, CircleObstacle):
                objects_data.append({"type": "circle", "position": list(obj.position), "radius": obj.radius})
        print("WORLD STATE:", {"objects": objects_data, "shot_count": game_world.shot_count if hasattr(game_world, 'shot_count') else 0}) # Füge shot_count hinzu
        return {"objects": objects_data, "shot_count": game_world.shot_count if hasattr(game_world, 'shot_count') else 0} # Füge shot_count hinzu
    raise HTTPException(status_code=503, detail="Game world not initialized")

app.include_router(router)