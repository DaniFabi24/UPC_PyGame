# /home/Daniel/UPC_PyGame/upc_game/test_game_world.py
import asyncio
from core.game_world import GameWorld
from core.game_objects import Triangle, CircleObstacle
from unittest.mock import MagicMock

def test_game_world_initialization():
    world = GameWorld(800, 600)
    assert world.width == 800
    assert world.height == 600
    assert world.objects == []
    assert world.player is None
    assert world._physics_task is None

def test_add_object():
    world = GameWorld(800, 600)
    player = Triangle([100, 100])
    world.add_object(player)
    assert len(world.objects) == 1
    assert world.player is player
    obstacle = CircleObstacle([200, 200], 30)
    world.add_object(obstacle)
    assert len(world.objects) == 2
    assert world.player is player # Player sollte sich nicht ändern

def test_set_player_thrust_and_rotation():
    world = GameWorld(800, 600)
    player = Triangle([100, 100])
    world.add_object(player)
    world.set_player_thrust(50)
    assert player.thrust_force == 50
    world.set_player_rotation(-2)
    assert player.rotation_speed == -2

def test_update():
    world = GameWorld(800, 600)
    obj1 = MagicMock()
    obj2 = MagicMock()
    world.add_object(obj1)
    world.add_object(obj2)
    collisions = world.update(0.1)
    obj1.update.assert_called_once_with(0.1)
    obj2.update.assert_called_once_with(0.1)
    # Hier könnten wir das Verhalten von check_collision testen,
    # aber dafür bräuchten wir eine Möglichkeit, es zu beeinflussen.
    # Für den Moment testen wir nur, dass update aufgerufen wird.
    assert isinstance(collisions, list)

def test_initialize_world():
    world = GameWorld(800, 600)
    world.initialize_world()
    assert world.player is not None
    assert isinstance(world.player, Triangle)
    assert len(world.objects) >= 3 # Spieler + mindestens 2 Hindernisse
    has_circle1 = any(isinstance(obj, CircleObstacle) and obj.position == [200, 200] and obj.radius == 30 for obj in world.objects)
    assert has_circle1
    has_circle2 = any(isinstance(obj, CircleObstacle) and obj.position == [600, 400] and obj.radius == 50 for obj in world.objects)
    assert has_circle2

async def test_physics_engine_start_stop():
    world = GameWorld(800, 600)
    world.start_physics_engine()
    assert world._physics_task is not None
    assert not world._physics_task.done()
    world.stop_physics_engine()
    await asyncio.sleep(0.1)
    assert world._physics_task is None

if __name__ == "__main__":
    test_game_world_initialization()
    print("test_game_world_initialization erfolgreich")
    test_add_object()
    print("test_add_object erfolgreich")
    test_set_player_thrust_and_rotation()
    print("test_set_player_thrust_and_rotation erfolgreich")
    test_update()
    print("test_update erfolgreich")
    test_initialize_world()
    print("test_initialize_world erfolgreich")
    asyncio.run(test_physics_engine_start_stop())
    print("test_physics_engine_start_stop erfolgreich")
    print("Alle GameWorld Tests erfolgreich!")