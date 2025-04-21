# /home/Daniel/UPC_PyGame/upc_game/core/game_world.py
import asyncio
import pygame
from .game_physics import check_collision, physics_loop
from .game_objects import Triangle, CircleObstacle

class GameWorld:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.objects = pygame.sprite.Group()
        self.player = None
        self._physics_task = None
        self.is_running = False
        self.shot_count = 0  # Füge diese Zeile hinzu

    def add_object(self, obj):
        self.objects.add(obj)
        if isinstance(obj, Triangle):
            self.player = obj
            if self.player:
                self.player.game_world = self # Stelle die Rückreferenz her

    def remove_object(self, obj):
        self.objects.remove(obj)
        if obj is self.player:
            self.player = None

    def initialize_world(self):
        self.player = Triangle([self.width / 2, self.height / 2], game_world=self)
        self.add_object(self.player)
        self.add_object(CircleObstacle([200, 200], 30))
        self.add_object(CircleObstacle([600, 400], 50))

    def set_player_thrust(self, thrust):
        if self.player:
            self.player.thrust_force = thrust

    def set_player_rotation(self, rotation):
        if self.player:
            self.player.rotation_speed = rotation

    def increment_shot_count(self): # Füge diese Methode hinzu
        self.shot_count += 1

    def update(self, dt):
        collisions = []
        for obj1 in self.objects:
            obj1.update(dt)
            for obj2 in self.objects:
                if obj1 != obj2 and check_collision(obj1, obj2):
                    if (obj1, obj2) not in collisions and (obj2, obj1) not in collisions:
                        collisions.append((obj1, obj2))
        return collisions

    async def _run_physics_loop(self, dt):
        while self.is_running:
            self.update(dt)
            await asyncio.sleep(dt)

    def start_physics_engine(self, dt=1/60):
        if not self.is_running:
            self.is_running = True
            self._physics_task = asyncio.create_task(self._run_physics_loop(dt))

    def stop_physics_engine(self):
        if self.is_running:
            self.is_running = False
            if self._physics_task:
                self._physics_task.cancel()
                self._physics_task = None

    def draw(self, surface):
        self.objects.draw(surface)

    def to_dict(self):
        return {
            "objects": [obj.to_dict() for obj in self.objects],
            "shot_count": self.shot_count # Füge die Schusszahl zum Dictionary hinzu
        }