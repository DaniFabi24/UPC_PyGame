from fastapi import FastAPI, APIRouter
from pydantic import BaseModel
import asyncio

game_world = None
game_world_imported = False
game_world_import_error = None
game_world_initialized = False

game_objects_imported = False
game_objects_import_error = None

try:
    from UPC_GAME.core.game_world import GameWorld
    game_world_imported = True
    game_world = GameWorld(800, 600)
    game_world.initialize_world()
    game_world_initialized = True
except ImportError as e:
    game_world_imported = False
    game_world_import_error = str(e)

try:
    from UPC_GAME.core.game_objects import Triangle, CircleObstacle
    game_objects_imported = True
except ImportError as e:
    game_objects_imported = False
    game_objects_import_error = str(e)

app = FastAPI()
router = APIRouter()

class MoveCommand(BaseModel):
    thrust: float = 0
    rotation: float = 0

class ShootCommand(BaseModel):
    pass # No parameters for shooting in this simple version

@router.get("/import_status")
async def check_imports():
    status = {
        "game_world_imported": game_world_imported,
        "game_objects_imported": game_objects_imported,
        "game_world_initialized": game_world_initialized,
    }
    if not game_world_imported:
        status["game_world_import_error"] = game_world_import_error
    if not game_objects_imported:
        status["game_objects_import_error"] = game_objects_import_error
    if game_world_imported and game_world_initialized:
        status["world_object_count"] = len(game_world.objects) if hasattr(game_world, 'objects') else 0
    return status

@router.post("/move")
async def move_player(command: MoveCommand):
    if game_world:
        game_world.set_player_thrust(command.thrust)
        game_world.set_player_rotation(command.rotation)
        return {"status": "moving", "thrust": command.thrust, "rotation": command.rotation}
    return {"status": "error", "message": "Game world not initialized"}

@router.post("/shoot")
async def shoot():
    if game_world and game_world.player:
        return {"status": "shot"} # Implement shooting logic later
    return {"status": "error", "message": "Player not found or game world not initialized"}

@router.get("/player_status")
async def get_player_status():
    if game_world and game_world.player:
        return {
            "position": game_world.player.position,
            "angle": game_world.player.angle
        }
    return {"status": "error", "message": "Player not found or game world not initialized"}

@router.get("/world_state")
async def get_world_state():
    if game_world:
        objects_data = []
        for obj in game_world.objects:
            if isinstance(obj, Triangle):
                objects_data.append({"type": "triangle", "position": obj.position, "angle": obj.angle})
            elif isinstance(obj, CircleObstacle):
                objects_data.append({"type": "circle", "position": obj.position, "radius": obj.radius})
        print("WORLD STATE:", {"objects": objects_data})
        return {"objects": objects_data}
    return {"status": "error", "message": "Game world not initialized"}

app.include_router(router)