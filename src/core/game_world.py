import pymunk
import pygame
import threading
import asyncio
import uuid
import math
import random
import time
from .game_objects import *
from ..settings import *

PLAYER_COLORS = [
    (255, 0, 0),     # Red
    (0, 191, 255),   # Deep Sky Blue (Helleres Blau)
    (50, 205, 50),   # Lime Green (Etwas dunkler, aber immer noch hell)
    (255, 255, 0),   # Yellow
    (0, 255, 255),   # Cyan
    (255, 0, 255),   # Magenta
    (255, 165, 0),   # Orange
    (238, 130, 238), # Violet (Helleres Lila)
    (255, 255, 255), # White
    (192, 192, 192)  # Silver (Helleres Grau)
]
NEXT_COLOR_INDEX = 0 # Globale Variable oder besser in GameWorld

class GameWorld:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.space = pymunk.Space()
        self.space.gravity = (0, 0)
        self.objects = [] 
        self.players = {}
        self.shot_count = 0
        self.player_collisions = 0
        self._physics_task = None
        self.is_running = False
        self.next_color_index = 0 # Index für die nächste Spielerfarbe
        self.add_borders()
        
    def add_player(self):
        """Erstellt einen neuen Spieler mit einer eindeutigen Farbe."""
        player_id = str(uuid.uuid4())
        max_attempts = 10
        safe_spawn_pos = None
        player_radius = 15

        for attempt in range(max_attempts):
            # ... (Positionsauswahl wie zuvor) ...
            if attempt == 0:
                potential_pos = pymunk.Vec2d(self.width / 2, self.height / 2)
            else:
                pad = player_radius + 10
                potential_pos = pymunk.Vec2d(
                    random.uniform(pad, self.width - pad),
                    random.uniform(pad, self.height - pad)
                )

            # ... (Erstellung von temp_body und temp_shape wie zuvor) ...
            temp_body = pymunk.Body(body_type=pymunk.Body.KINEMATIC)
            temp_body.position = potential_pos
            temp_shape = pymunk.Poly(temp_body, [
                (player_radius, 0),
                (-player_radius, player_radius),
                (-player_radius, -player_radius)
            ])
            temp_shape.collision_type = 1

            # Prüfe auf Kollisionen mit bestehenden Shapes im Space
            # *** Relevant sind Hindernisse (Typ 2) UND andere Spieler (Typ 1) ***
            query_info = self.space.shape_query(temp_shape)

            collision_found = False
            colliding_type = None
            for info in query_info:
                # Prüfe, ob die Kollision mit einem Hindernis (Typ 2) oder Spieler (Typ 1) stattfindet
                if info.shape and info.shape.collision_type in [1, 2]: # *** Prüfung auf Typ 1 und 2 ***
                     collision_found = True
                     colliding_type = info.shape.collision_type
                     print(f"Spawn attempt {attempt+1} at {potential_pos} failed: Collision with type {colliding_type}.")
                     break # Kollision gefunden, nächste Position versuchen

            if not collision_found:
                safe_spawn_pos = potential_pos
                print(f"Spawn attempt {attempt+1}: Found safe position at {safe_spawn_pos}")
                break

        if safe_spawn_pos:
            # Wähle die nächste Farbe aus der Liste
            player_color = PLAYER_COLORS[self.next_color_index % len(PLAYER_COLORS)]
            self.next_color_index += 1 # Erhöhe den Index für den nächsten Spieler

            # Übergebe die Farbe an den Triangle Konstruktor
            new_player = Triangle(safe_spawn_pos, color=player_color, game_world=self)
            new_player.player_id = player_id
            self.players[player_id] = new_player
            print(f"Player added with ID: {player_id} at {safe_spawn_pos} with color {player_color}. Spawn protection active until {new_player.spawn_protection_until:.2f}")
            print(f"Current players in dict after add: {list(self.players.keys())}")
            return player_id
        else:
            print(f"Error: Could not find a safe spawn position for player after {max_attempts} attempts.")
            return None

    def remove_player(self, player_id):
        """Entfernt einen Spieler anhand seiner ID, indem die Methode des Spielers aufgerufen wird."""
        if player_id in self.players:
            player_to_remove = self.players[player_id]
            print(f"Attempting to remove player {player_id}...")
            # Delegiere die eigentliche Entfernung an das Spielerobjekt
            player_to_remove.remove_from_world()
            # Das Löschen aus self.players geschieht jetzt in remove_from_world
            print(f"Player remove process initiated for ID: {player_id}")
        else:
            print(f"Attempted to remove non-existent player ID: {player_id}")

    def add_object(self, obj):
        if obj not in self.objects:
            self.objects.append(obj)
            # Physik-Engine hinzufügen, falls noch nicht geschehen (in Triangle.__init__)
            # if isinstance(obj, (Triangle, CircleObstacle, Projectile)):
            #    if obj.body not in self.space.bodies: self.space.add(obj.body, obj.shape)

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
        # Add obstacles to create an arena-like environment
        arena_obstacles = [
            CircleObstacle([150, 150], 40, game_world=self),
            CircleObstacle([650, 150], 40, game_world=self),
            CircleObstacle([150, 450], 40, game_world=self),
            CircleObstacle([650, 450], 40, game_world=self),
            CircleObstacle([400, 150], 30, game_world=self),
            CircleObstacle([400, 450], 30, game_world=self),
            CircleObstacle([250, 300], 50, game_world=self),
            CircleObstacle([550, 300], 50, game_world=self),
        ]
        for obstacle in arena_obstacles:
            self.add_object(obstacle)
        from .game_objects import setup_collision_handlers
        setup_collision_handlers(self.space, self)

    def positive_player_thrust(self, player_id):
        player = self.players.get(player_id)
        if player:
            radians = player.body.angle
            thrust_vector = pygame.math.Vector2(1, 0).rotate_rad(radians) * PLAYER_THRUST
            player.body.velocity += thrust_vector

    def negative_player_thrust(self, player_id):
        player = self.players.get(player_id)
        if player:
            radians = player.body.angle
            thrust_vector = pygame.math.Vector2(1, 0).rotate_rad(radians) * (-PLAYER_THRUST)
            player.body.velocity += thrust_vector

    def right_player_rotation(self, player_id):
        player = self.players.get(player_id)
        if player:
            player.body.angle += PLAYER_ROTATION

    def left_player_rotation(self, player_id):
        player = self.players.get(player_id)
        if player:
            player.body.angle -= PLAYER_ROTATION

    def shoot(self, player_id):
        player = self.players.get(player_id)
        if player:
            # *** NEU: Spawn-Schutz Prüfung ***
            if time.time() < player.spawn_protection_until:
                print(f"Player {player_id} cannot shoot during spawn protection.")
                return # Schießen verhindern

            # --- Bestehende Logik zum Schießen ---
            player_angle_rad = player.body.angle
            offset_distance = player.radius + PROJECTILE_RADIUS + 1
            start_offset_x = math.cos(player_angle_rad) * offset_distance
            start_offset_y = math.sin(player_angle_rad) * offset_distance
            start_pos = player.body.position + pymunk.Vec2d(start_offset_x, start_offset_y)

            # Übergebe die Farbe des Spielers an das Projektil
            projectile = Projectile(
                position=start_pos,
                angle_rad=player.body.angle,
                owner=player,
                color=player.color, # *** NEU: Spielerfarbe übergeben ***
                game_world=self
            )
            self.increment_shot_count()
            print(f"Shot fired by {player_id}! Total shots: {self.shot_count}")

    def increment_shot_count(self):
        self.shot_count += 1

    def update(self, dt):
        self.space.step(dt)
        for player in self.players.values():
            player.body.angular_velocity *= 1 - 0.1 * PHYSICS_DT
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
        return {
            "players": [
                {
                    "id": pid,
                    "position": [p.body.position.x, p.body.position.y],
                    "angle": math.degrees(p.body.angle),
                    "health": p.health
                } for pid, p in self.players.items()
            ],
            "objects": [obj.to_dict() for obj in self.objects if not isinstance(obj, Triangle)],
            "shots_fired": self.shot_count,
        }

    def get_relative_state_for_player(self, player_id):
        """
        Gibt den Zustand relativ zu einem bestimmten Spieler zurück,
        einschließlich der Lebenszahl und aller Objekte (inkl. anderer Spieler)
        in einem bestimmten Radius.
        """
        player = self.players.get(player_id)
        if not player:
            return None

        player_pos = player.body.position
        player_angle_rad = player.body.angle
        player_vel = player.body.velocity
        player_angular_vel = player.body.angular_velocity
        player_health = player.health
        radius = SCANNING_RADIUS # Aus settings.py

        nearby_objects_relative = []
        
        # Iteriere durch alle Objekte UND alle anderen Spieler
        # Kombiniere die Listen oder iteriere separat
        
        # 1. Iteriere durch 'objects' (Hindernisse, Projektile)
        for obj in self.objects:
            # Spieler selbst und Objekte ohne Body überspringen
            if obj is player or not hasattr(obj, 'body'):
                continue

            obj_pos = obj.body.position
            distance = player_pos.get_distance(obj_pos)

            if distance <= radius:
                delta_pos = obj_pos - player_pos
                relative_pos_rotated = delta_pos.rotated(-player_angle_rad)

                obj_vel = getattr(obj.body, 'velocity', pymunk.Vec2d(0, 0))
                delta_vel = obj_vel - player_vel
                relative_vel_rotated = delta_vel.rotated(-player_angle_rad)

                obj_type = "unknown"
                if isinstance(obj, CircleObstacle):
                    obj_type = "obstacle"
                elif isinstance(obj, Projectile):
                    obj_type = "projectile"
                # Spieler werden in der nächsten Schleife behandelt

                if obj_type != "unknown": # Nur bekannte Typen hinzufügen
                    nearby_objects_relative.append({
                        "type": obj_type,
                        "relative_position": [relative_pos_rotated.x, relative_pos_rotated.y],
                        "relative_velocity": [relative_vel_rotated.x, relative_vel_rotated.y],
                        "distance": distance,
                        # Optional: Farbe des Projektils hinzufügen
                        "color": getattr(obj, 'color', None) if obj_type == "projectile" else None
                    })

        # 2. Iteriere durch 'players' (andere Spieler)
        for other_pid, other_player in self.players.items():
            # Überspringe den Spieler selbst
            if other_pid == player_id:
                continue

            other_player_pos = other_player.body.position
            distance = player_pos.get_distance(other_player_pos)

            if distance <= radius:
                delta_pos = other_player_pos - player_pos
                relative_pos_rotated = delta_pos.rotated(-player_angle_rad)

                other_player_vel = other_player.body.velocity
                delta_vel = other_player_vel - player_vel
                relative_vel_rotated = delta_vel.rotated(-player_angle_rad)

                nearby_objects_relative.append({
                    "type": "other_player",
                    "relative_position": [relative_pos_rotated.x, relative_pos_rotated.y],
                    "relative_velocity": [relative_vel_rotated.x, relative_vel_rotated.y],
                    "distance": distance,
                    "color": other_player.color, # Farbe des anderen Spielers
                    # Optional: ID oder Health des anderen Spielers hinzufügen?
                    # "id": other_pid,
                    # "health": other_player.health # Ist Health "scannbar"?
                })


        return {
            "player_id": player_id,
            "health": player_health,
            "angular_velocity": player_angular_vel,
            "velocity": [player_vel.x, player_vel.y],
            "nearby_objects": nearby_objects_relative
        }

    def run_visualizer(self):
        pygame.init()
        screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Game Visualizer")
        clock = pygame.time.Clock()

        # Statischen Hintergrund erstellen (optional)
        background = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        background.fill((0, 0, 0)) # Schwarzer Hintergrund
        static_sprites = pygame.sprite.Group()
        for obj in self.objects:
             if isinstance(obj, CircleObstacle):
                 static_sprites.add(obj)
        static_sprites.draw(background)

        running = True
        while running:
            screen.blit(background, (0, 0)) # Zeichne Hintergrund mit statischen Elementen

            # Erstelle die Gruppe der aktuell aktiven Sprites
            current_sprites = pygame.sprite.Group()
            for player in self.players.values():
                 current_sprites.add(player)
            for obj in self.objects:
                 if isinstance(obj, Projectile):
                     current_sprites.add(obj)

            # Aktualisiere Sprites (Position, Rotation, Transparenz für Spawn-Schutz)
            dt = clock.tick(FPS) / 1000.0
            current_sprites.update(dt)

            # Zeichne alle Sprites (Spieler, Projektile etc.)
            current_sprites.draw(screen)

            # *** Gesundheitsleisten für alle Spieler zeichnen (Effizient) ***
            bar_width = 30  # Breite der Leiste
            bar_height = 5   # Höhe der Leiste
            bar_offset_y = 5 # Abstand unter dem Spieler
            health_color = (0, 255, 0) # Grün für Gesundheit
            lost_health_color = (255, 0, 0) # Rot für verlorene Gesundheit
            border_color = (255, 255, 255) # Weißer Rand

            for player in self.players.values():
                # Position unter dem Spieler-Rechteck zentriert
                # player.rect wird in player.update() aktualisiert
                bar_x = player.rect.centerx - bar_width // 2
                bar_y = player.rect.bottom + bar_offset_y

                # Berechne den Füllstand (Prozentsatz)
                health_percentage = max(0, player.health / PLAYER_START_HEALTH) # Sicherstellen >= 0

                # Zeichne Hintergrund (verlorene Gesundheit)
                background_rect = pygame.Rect(bar_x, bar_y, bar_width, bar_height)
                pygame.draw.rect(screen, lost_health_color, background_rect)

                # Zeichne Vordergrund (aktuelle Gesundheit)
                current_bar_width = int(bar_width * health_percentage)
                if current_bar_width > 0:
                    health_rect = pygame.Rect(bar_x, bar_y, current_bar_width, bar_height)
                    pygame.draw.rect(screen, health_color, health_rect)

                # Optional: Zeichne Rahmen
                pygame.draw.rect(screen, border_color, background_rect, 1) # Dicke 1

            pygame.display.flip()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

        pygame.quit()

# Erstelle globale Instanz nach Initialisierung:
game_world_instance = GameWorld(SCREEN_WIDTH, SCREEN_HEIGHT)
game_world_instance.initialize_world()