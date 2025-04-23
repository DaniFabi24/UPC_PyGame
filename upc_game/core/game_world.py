import asyncio
import pygame
from .game_physics import check_collision, physics_loop
from .game_objects import Triangle, CircleObstacle
import time

class GameWorld:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.objects = pygame.sprite.Group()
        self.player = None
        self._physics_task = None
        self.is_running = False
        self.shot_count = 0
        self.player_collisions = 0
        self.max_collisions = 5
        self.last_collision_time = 0.0  # Zeitpunkt der letzten Kollision
        self.collision_cooldown = 0.5  # Totzeit in Sekunden

    def add_object(self, obj):
        self.objects.add(obj)
        if isinstance(obj, Triangle):
            self.player = obj
            if self.player:
                self.player.game_world = self

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

    def increment_shot_count(self):
        self.shot_count += 1

    def increment_player_collisions(self):
        if self.player_collisions < self.max_collisions:
            self.player_collisions += 1

    def handle_collision(self, obj1, obj2):
        normal = pygame.math.Vector2(obj2.rect.center) - pygame.math.Vector2(obj1.rect.center)
        if normal.length_squared() > 0:
            normal = normal.normalize()
            relative_velocity = pygame.math.Vector2(obj1.velocity)
            impulse = -2 * relative_velocity.dot(normal) * normal
            obj1.velocity += impulse * 1.5  # Erhöhter Faktor für stärkeren Abprall
            self.last_collision_time = time.time() # Zeitpunkt der Kollision speichern

    def update(self, dt):
        collisions = []
        collided_with_circle = False
        player_collided_with_border = False # Flagge für Kollision mit der Grenze

        if self.player:
            # Überprüfe Kollision mit den Bildschirmgrenzen
            if self.player.position[0] < 0 or self.player.position[0] > self.width or \
               self.player.position[1] < 0 or self.player.position[1] > self.height:
                current_time = time.time()
                if current_time - self.last_collision_time > self.collision_cooldown:
                    self.increment_player_collisions()
                    self.last_collision_time = current_time
                    player_collided_with_border = True
                    # Einfaches Zurücksetzen innerhalb der Grenzen mit optionalem Abprall
                    if self.player.position[0] < 0:
                        self.player.position[0] = 0
                        self.player.velocity[0] *= -0.5
                    elif self.player.position[0] > self.width:
                        self.player.position[0] = self.width
                        self.player.velocity[0] *= -0.5
                    if self.player.position[1] < 0:
                        self.player.position[1] = 0
                        self.player.velocity[1] *= -0.5
                    elif self.player.position[1] > self.height:
                        self.player.position[1] = self.height
                        self.player.velocity[1] *= -0.5

        for obj1 in self.objects:
            obj1.update(dt)
            for obj2 in self.objects:
                if obj1 != obj2 and check_collision(obj1, obj2):
                    if (obj1, obj2) not in collisions and (obj2, obj1) not in collisions:
                        collisions.append((obj1, obj2))
                        if self.player:
                            if (obj1 is self.player and isinstance(obj2, CircleObstacle)) or \
                               (obj2 is self.player and isinstance(obj1, CircleObstacle)):
                                current_time = time.time()
                                if current_time - self.last_collision_time > self.collision_cooldown:
                                    self.increment_player_collisions()
                                    self.handle_collision(self.player, obj1 if obj2 is self.player else obj2)
                                    collided_with_circle = True
                            elif obj1 is self.player or obj2 is self.player:
                                pass
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
            "shot_count": self.shot_count,
            "player_collisions": self.player_collisions
        }