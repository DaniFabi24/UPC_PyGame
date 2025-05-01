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
            border.elasticity = 1.0  # perfekte Abprallwirkung
            border.friction = 0.0
            border.collision_type = 3  # Set collision type for borders
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
            self.player.body.angle += PLAYER_ROTATION

    def left_player_rotation(self):
        if self.player:
            self.player.body.angle -= PLAYER_ROTATION

    def shoot(self):
        if self.player:
            player_angle_rad = self.player.body.angle
            offset_distance = self.player.radius + PROJECTILE_RADIUS + 1
            start_offset_x = math.cos(player_angle_rad) * offset_distance
            start_offset_y = math.sin(player_angle_rad) * offset_distance
            start_pos = self.player.body.position + pymunk.Vec2d(start_offset_x, start_offset_y)

            projectile = Projectile(
                position=start_pos,
                angle_rad=player_angle_rad,
                owner=self.player, # *** NEU: Spieler als Owner übergeben ***
                game_world=self
            )
            self.increment_shot_count()
            print(f"Shot fired! Total shots: {self.shot_count}")

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

        all_sprites = pygame.sprite.Group() # Group to manage drawing

        # Erzeuge einen statischen Hintergrund
        background = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        background.fill((0, 0, 0))
        static_sprites = pygame.sprite.Group() # Group for static objects
        for obj in self.objects:
             # Add obstacles to static group if they don't move
             if isinstance(obj, CircleObstacle):
                 static_sprites.add(obj)

        static_sprites.draw(background) # Draw static obstacles onto background once

        running = True
        while running:
            screen.blit(background, (0, 0)) # Draw background with static elements

            # Update sprite group membership - add new projectiles, remove destroyed ones
            current_sprites = pygame.sprite.Group()
            for obj in self.objects:
                if isinstance(obj, pygame.sprite.Sprite):
                    current_sprites.add(obj)

            # Draw all current sprites (player, projectiles)
            current_sprites.draw(screen)

            pygame.display.flip()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
            
            clock.tick(FPS)

        pygame.quit()

# Erstelle globale Instanz nach Initialisierung:
game_world_instance = GameWorld(SCREEN_WIDTH, SCREEN_HEIGHT)
game_world_instance.initialize_world()

#Dummy zum Testen von git!