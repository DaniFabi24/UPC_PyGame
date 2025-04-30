import pymunk
import pygame
import threading
import asyncio
from .game_objects import *
from ..settings import *

class GameWorld:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.space = pymunk.Space()
        self.space.gravity = (0, 0)
        self.objects = [] 
        self.player = None
        self.shot_count = 0
        self.player_collisions = 0
        self._physics_task = None
        self.is_running = False
        self.add_borders()
        
    def add_object(self, obj):
        self.objects.append(obj)
        if isinstance(obj, Triangle):
            self.player = obj

    def add_borders(self):
        static_body = self.space.static_body
        borders = [
            pymunk.Segment(static_body, (0, 0), (self.width, 0), 1),            # Unterer Rand
            pymunk.Segment(static_body, (0, self.height), (self.width, self.height), 1),  # Oberer Rand
            pymunk.Segment(static_body, (0, 0), (0, self.height), 1),             # Linker Rand
            pymunk.Segment(static_body, (self.width, 0), (self.width, self.height), 1)      # Rechter Rand
        ]
        for border in borders:
            border.elasticity = 0.5  # perfekte Abprallwirkung
            border.friction = 0.0
            self.space.add(border)

    def initialize_world(self):
        self.player = Triangle([self.width / 2, self.height / 2], game_world=self)
        self.add_object(self.player)
        self.add_object(CircleObstacle([200, 200], 30, game_world=self))
        self.add_object(CircleObstacle([600, 400], 50, game_world=self))
        self.add_object(CircleObstacle([600, 300], 70, game_world=self))
        from .game_objects import setup_collision_handlers
        setup_collision_handlers(self.space, self)

    def positive_player_thrust(self):
        if self.player:
            radians = self.player.body.angle
            thrust_vector = pygame.math.Vector2(1, 0).rotate_rad(radians) * PLAYER_THRUST
            self.player.body.velocity += thrust_vector

    def negative_player_thrust(self):
        if self.player:
            radians = self.player.body.angle
            thrust_vector = pygame.math.Vector2(1, 0).rotate_rad(radians) * (-PLAYER_THRUST)
            self.player.body.velocity += thrust_vector

    def right_player_rotation(self):
        if self.player:
            self.player.body.angle -= PLAYER_ROTATION

    def left_player_rotation(self):
        if self.player:
            self.player.body.angle += PLAYER_ROTATION


    def increment_shot_count(self):
        self.shot_count += 1

    def update(self, dt):
        self.space.step(dt)
        if self.player:
            self.player.body.angular_velocity *= 1 - 0.1 * PHYSICS_DT
        for shape in self.space.shapes:
            if hasattr(shape, "sprite_ref"):
                shape.sprite_ref.update(dt)

    async def _run_physics_loop(self, dt):
        while self.is_running:
            self.update(dt)
            await asyncio.sleep(dt)

    def start_physics_engine(self, dt=PHYSICS_DT):
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # Kein laufender Event Loop – erstelle einen neuen und starte ihn in einem Daemon-Thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            threading.Thread(target=loop.run_forever, daemon=True).start()
        self.is_running = True
        self._physics_task = loop.create_task(self._run_physics_loop(dt))

    def stop_physics_engine(self):
        if self.is_running:
            self.is_running = False
            if self._physics_task:
                self._physics_task.cancel()
                self._physics_task = None

    def to_dict(self):
        objects_data = []
        for obj in self.objects:
            if hasattr(obj, "body"):
                pos = list(obj.body.position)
                angle = obj.body.angle
                objects_data.append({
                    "id": id(obj),
                    "type": obj.__class__.__name__.lower(),
                    "position": pos,
                    "angle": angle,
                    "radius": getattr(obj, "radius", 15)
                })
            else:
                objects_data.append({
                    "id": id(obj),
                    "type": obj.__class__.__name__.lower()
                })
        return {
            "objects": objects_data,
            "shot_count": self.shot_count,
            "player_collisions": self.player_collisions
        }

    def run_visualizer(self):
        pygame.init()
        screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Game Visualizer")
        clock = pygame.time.Clock()

        # Erzeuge einen statischen Hintergrund, auf dem nur die statischen Objekte (z.B. Hindernisse) gezeichnet werden.
        background = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        background.fill((0, 0, 0))
        # Zeichne statische Objekte (nicht den Spieler) einmalig:
        state = self.to_dict()
        for obj in state["objects"]:
            typ = obj["type"]
            # Angenommen, der Spieler hat den Typ "triangle"
            if typ != "triangle":
                pos = obj["position"]
                if typ in ("circleobstacle", "circle"):
                    color = (128, 128, 128)
                    radius = int(obj.get("radius", 15))
                    pygame.draw.circle(background, color, (int(pos[0]), int(pos[1])), radius)
                # Hier können weitere statische Objekttypen ergänzt werden.

        running = True
        while running:
            dt = clock.tick(FPS) / 1000.0

            # Blite den statischen Hintergrund, der die Hindernisse enthält.
            screen.blit(background, (0, 0))
            
            # Aktualisiere die Anzeige des Spielers.
            if self.player:
                pos = self.player.body.position
                color = (0, 128, 255)
                pygame.draw.circle(screen, color, (int(pos.x), int(pos.y)), 15)
            
            pygame.display.flip()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

        pygame.quit()

# Erstelle globale Instanz nach Initialisierung:
game_world_instance = GameWorld(SCREEN_WIDTH, SCREEN_HEIGHT)
game_world_instance.initialize_world()