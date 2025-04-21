import asyncio
from .game_physics import check_collision, physics_loop
from .game_objects import Triangle, CircleObstacle

class GameWorld:
    def __init__(self, width, height, update_rate=60.0):
        self.width = width
        self.height = height
        self.objects = []
        self.player = None
        self.dt = 1.0 / update_rate
        self._physics_task = None

    def add_object(self, obj):
        self.objects.append(obj)
        if isinstance(obj, Triangle):
            self.player = obj

    def set_player_thrust(self, thrust):
        if self.player:
            self.player.thrust_force = thrust

    def set_player_rotation(self, rotation):
        if self.player:
            self.player.rotation_speed = rotation

    def update(self, dt):
        for obj in self.objects:
            obj.update(dt)

        # Collision detection
        collisions = []
        for i in range(len(self.objects)):
            for j in range(i + 1, len(self.objects)):
                if check_collision(self.objects[i], self.objects[j]):
                    collisions.append((self.objects[i], self.objects[j]))
        # Here you could handle collisions (e.g., destruction, status change)
        return collisions

    def start_physics_engine(self):
        if not self._physics_task:
            self._physics_task = asyncio.create_task(physics_loop(self, self.dt))

    def stop_physics_engine(self):
        if self._physics_task:
            self._physics_task.cancel()
            self._physics_task = None

    def initialize_world(self):
        # Example initialization of the world with obstacles
        self.player = Triangle(position=[self.width // 2, self.height // 2])
        self.add_object(self.player)
        self.add_object(CircleObstacle(position=[200, 200], radius=30))
        self.add_object(CircleObstacle(position=[600, 400], radius=50))