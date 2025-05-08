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

# Predefined player colors used cyclically when creating new players.
PLAYER_COLORS = [
    (255, 0, 0),     # Red
    (0, 191, 255),   # Deep Sky Blue
    (50, 205, 50),   # Lime Green
    (255, 255, 0),   # Yellow
    (0, 255, 255),   # Cyan
    (255, 0, 255),   # Magenta
    (255, 165, 0),   # Orange
    (238, 130, 238), # Violet
    (255, 255, 255), # White
    (192, 192, 192)  # Silver
]

class GameWorld:
    """
    The GameWorld class encapsulates the entire state of the game.
    
    It manages the physics simulation (using pymunk), rendering (using pygame), 
    players, obstacles, projectiles, and power-ups. It also provides methods to 
    add/remove players/objects, update the simulation, and run the visualizer.
    """
    def __init__(self, width, height):
        """
        Initializes the GameWorld instance.
        
        Args:
            width (int): Width of the game world (and visualization screen).
            height (int): Height of the game world.
        """
        self.width = width
        self.height = height
        self.space = pymunk.Space()
        self.space.gravity = (0, 0)
        self.objects = []    # List of non-player objects (obstacles, projectiles, power-ups, etc.)
        self.players = {}    # Dictionary mapping player IDs to player objects
        self.shot_count = 0  # Total number of shots fired
        self.player_collisions = 0  # Counter for collisions involving players
        self._physics_task = None   # Holds the asyncio task for the physics loop
        self.is_running = False     # Flag indicating whether the physics loop is active
        self.next_color_index = 0   # Index to select the next player color from PLAYER_COLORS
        self.game_started = False # Flag indicating whether the game has started
        self.waiting_for_players = True # Flag indicating whether the game is waiting for players to join
        # NEU: Countdown-Zustandsvariablen
        self.countdown_active = False
        self.countdown_seconds_remaining = 0.0

        self.add_borders()  # Create and add border segments to the physics space
        self.initialize_world_objects() # *** HINDERNISSE SOFORT INITIALISIEREN ***
        self.initialize_collision_handlers() # Kollisionshandler auch früh initialisieren

    def add_player(self):
        """
        Creates and adds a new player to the game.
        
        It attempts to find a safe spawn position (without collisions with existing players/obstacles)
        and assigns a unique ID and a pre-defined color to the player.
        
        Returns:
            str or None: The player's unique ID if spawn is successful; otherwise, None.
        """
        if self.game_started:
            print("Game has already started. No new players can join.")
            return None
        # Spieler können während des Countdowns beitreten. Sie starten als 'nicht bereit'.
        # Die finale Prüfung am Ende des Countdowns wird dies berücksichtigen.

        player_id = str(uuid.uuid4())
        max_attempts = 10
        safe_spawn_pos = None
        player_radius = 15

        for attempt in range(max_attempts):
            # For the first attempt, use the center of the screen; afterwards, random positions.
            if attempt == 0:
                potential_pos = pymunk.Vec2d(self.width / 2, self.height / 2)
            else:
                pad = player_radius + 10
                potential_pos = pymunk.Vec2d(
                    random.uniform(pad, self.width - pad),
                    random.uniform(pad, self.height - pad)
                )

            # Create a temporary body/shape to test for collisions.
            temp_body = pymunk.Body(body_type=pymunk.Body.KINEMATIC)
            temp_body.position = potential_pos
            temp_shape = pymunk.Poly(temp_body, [
                (player_radius, 0),
                (-player_radius, player_radius),
                (-player_radius, -player_radius)
            ])
            temp_shape.collision_type = 1

            # Check for collisions with obstacles (type 2) or existing players (type 1)
            query_info = self.space.shape_query(temp_shape)
            collision_found = False
            colliding_type = None
            for info in query_info:
                if info.shape and info.shape.collision_type in [1, 2]:
                    collision_found = True
                    colliding_type = info.shape.collision_type
                    print(f"Spawn attempt {attempt+1} at {potential_pos} failed: Collision with type {colliding_type}.")
                    break

            if not collision_found:
                safe_spawn_pos = potential_pos
                print(f"Spawn attempt {attempt+1}: Found safe position at {safe_spawn_pos}")
                break

        if safe_spawn_pos:
            # Choose the next available color for the new player.
            player_color = PLAYER_COLORS[self.next_color_index % len(PLAYER_COLORS)]
            self.next_color_index += 1

            # Create a new Triangle (player) with chosen color and safe spawn position.
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
        """
        Removes a player from the game using its ID.
        
        Delegates the removal process to the player's own remove_from_world method.
        
        Args:
            player_id (str): The unique identifier of the player to remove.
        """
        if player_id in self.players:
            player_to_remove = self.players[player_id]
            print(f"Attempting to remove player {player_id}...")
            player_to_remove.remove_from_world()
            print(f"Player remove process initiated for ID: {player_id}")
        else:
            print(f"Attempted to remove non-existent player ID: {player_id}")

    def add_object(self, obj):
        """
        Adds a game object (obstacle, projectile, power-up, etc.) to the world.
        
        Args:
            obj: The game object to add.
        """
        if obj not in self.objects:
            self.objects.append(obj)

    def add_borders(self):
        """
        Creates border segments around the game world and adds them to the physics space.
        
        The borders are used to contain the game objects inside the visible area.
        """
        static_body = self.space.static_body
        borders = [
            pymunk.Segment(static_body, (0, 0), (self.width, 0), 1),              # Bottom border
            pymunk.Segment(static_body, (0, self.height), (self.width, self.height), 1),  # Top border
            pymunk.Segment(static_body, (0, 0), (0, self.height), 1),               # Left border
            pymunk.Segment(static_body, (self.width, 0), (self.width, self.height), 1)      # Right border
        ]
        for border in borders:
            border.elasticity = 1.0  # Perfect bounce
            border.friction = 0.0
            border.collision_type = 3  # Collision type for borders
            self.space.add(border)

    def initialize_world_objects(self):
        """Initializes obstacles. Called early.""" # Geändert: Wird jetzt früh aufgerufen
        # Sicherstellen, dass Objekte nur einmal hinzugefügt werden, falls diese Methode
        # aus irgendeinem Grund mehrmals aufgerufen werden könnte.
        # Da es jetzt im __init__ ist, ist die "if not self.objects" Bedingung
        # für Hindernisse nicht mehr so kritisch, aber schadet nicht.
        existing_obstacle_count = sum(1 for obj in self.objects if isinstance(obj, CircleObstacle))
        if existing_obstacle_count == 0:
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
            print("Game world objects (obstacles) initialized.")
        else:
            print("Obstacles already initialized.")

    def initialize_collision_handlers(self):
        """Initializes collision handlers. Can be called early."""
        from .game_objects import setup_collision_handlers
        setup_collision_handlers(self.space, self)
        print("Collision handlers initialized.")

    def check_if_all_players_ready(self):
        """
        Prüft, ob alle verbundenen Spieler bereit sind.
        Wenn ja und noch kein Countdown läuft, wird der Countdown gestartet.
        Diese Methode blockiert NICHT mehr mit time.sleep.
        """
        if not self.players: # Keine Spieler, also nicht bereit und kein Countdown
            self.waiting_for_players = True
            self.game_started = False
            self.countdown_active = False
            return False

        all_currently_ready = all(player.ready for player in self.players.values())

        if all_currently_ready and self.waiting_for_players and not self.countdown_active:
            # Alle Bedingungen erfüllt, um den Countdown zu STARTEN
            print("All players ready! Starting countdown...")
            self.countdown_active = True
            self.countdown_seconds_remaining = COUNTDOWN_DURATION
            self.waiting_for_players = False # Wechsel in den Countdown-Modus
            for player in self.players.values():
                player.spawn_protection_until = time.time() + player.spawn_protection_duration + COUNTDOWN_DURATION
        elif not all_currently_ready and self.countdown_active:
            # Jemand wurde während des Countdowns unready (z.B. Disconnect)
            print("Not all players ready during countdown. Resetting to waiting state.")
            self.countdown_active = False
            self.waiting_for_players = True
            # game_started bleibt False
        elif not all_currently_ready and not self.game_started:
            # Allgemeiner Fall: Nicht alle bereit, kein Countdown, Spiel nicht gestartet -> Wartezustand sicherstellen
            self.waiting_for_players = True
            self.game_started = False # Sicherstellen, dass Spiel nicht als gestartet markiert ist

        return all_currently_ready

    def player_ready(self, player_id):
        player = self.players.get(player_id)
        if player:
            if self.game_started:
                print(f"Player {player_id} tried to set ready, but game has already started.")
                return

            if not player.ready:
                player.ready = True
                print(f"Player {player_id} is now ready.")
                self.check_if_all_players_ready() # Prüfen, ob Countdown gestartet werden kann
            else:
                print(f"Player {player_id} was already ready.")
        else:
            print(f"Player_ready called for non-existent player {player_id}")

    def positive_player_thrust(self, player_id):
        """
        Applies a forward thrust to the specified player.
        
        Args:
            player_id (str): The identifier of the player.
        """
        if not self.game_started: return # Spiel noch nicht gestartet
        player = self.players.get(player_id)
        if player:
            radians = player.body.angle
            thrust_vector = pygame.math.Vector2(1, 0).rotate_rad(radians) * PLAYER_THRUST
            player.body.velocity += thrust_vector

    def negative_player_thrust(self, player_id):
        """
        Applies a reverse thrust (braking) to the specified player.
        
        Args:
            player_id (str): The identifier of the player.
        """
        if not self.game_started: return
        player = self.players.get(player_id)
        if player:
            radians = player.body.angle
            thrust_vector = pygame.math.Vector2(1, 0).rotate_rad(radians) * (-PLAYER_THRUST)
            player.body.velocity += thrust_vector

    def right_player_rotation(self, player_id):
        """
        Rotates a player to the right.
        
        Args:
            player_id (str): The identifier of the player.
        """
        if not self.game_started: return
        player = self.players.get(player_id)
        if player:
            player.body.angular_velocity += PLAYER_ROTATION

    def left_player_rotation(self, player_id):
        """
        Rotates a player to the left.
        
        Args:
            player_id (str): The identifier of the player.
        """
        if not self.game_started: return
        player = self.players.get(player_id)
        if player:
            player.body.angular_velocity -= PLAYER_ROTATION

    def shoot(self, player_id):
        """
        Initiates a shooting action for the specified player.
        
        Checks for spawn protection; if allowed, spawns a projectile in front of the player.
        
        Args:
            player_id (str): The identifier of the player who is firing.
        """
        if not self.game_started:
            print(f"Player {player_id} tried to shoot, but game has not started.")
            return
        player = self.players.get(player_id)
        if player:
            # Prevent shooting when spawn protection is active.
            if time.time() < player.spawn_protection_until:
                print(f"Player {player_id} cannot shoot during spawn protection.")
                return

            player_angle_rad = player.body.angle
            offset_distance = player.radius + PROJECTILE_RADIUS + 1
            start_offset_x = math.cos(player_angle_rad) * offset_distance
            start_offset_y = math.sin(player_angle_rad) * offset_distance
            start_pos = player.body.position + pymunk.Vec2d(start_offset_x, start_offset_y)

            # Use the player's color for the projectile.
            projectile = Projectile(
                position=start_pos,
                angle_rad=player.body.angle,
                owner=player,
                color=player.color,
                game_world=self
            )
            self.increment_shot_count()
            print(f"Shot fired by {player_id}! Total shots: {self.shot_count}")

    def increment_shot_count(self):
        """
        Increments the shot counter, tracking the number of projectiles fired.
        """
        self.shot_count += 1

    def update(self, dt):
        """
        Updates the physics simulation and game objects.
        
        Steps the physics engine, updates angular velocities, and calls each object's update method.
        
        Args:
            dt (float): Delta time since the last update.
        """
        self.space.step(dt)
        for player in self.players.values():
            player.body.angular_velocity *= 1 - 0.1 * PHYSICS_DT
        for shape in self.space.shapes:
            if hasattr(shape, "sprite_ref"):
                shape.sprite_ref.update(dt)

        # Countdown-Logik
        if self.countdown_active:
            self.countdown_seconds_remaining -= dt
            if self.countdown_seconds_remaining <= 0:
                self.countdown_seconds_remaining = 0 # Verhindere negative Werte
                print("Countdown timer reached zero. Final check for player readiness...")
                # Finale Prüfung: Sind ALLE aktuell verbundenen Spieler bereit?
                if self.players and all(p.ready for p in self.players.values()):
                    self.waiting_for_players = False
                    self.game_started = True
                    self.countdown_active = False
                else:
                    print("Not all players ready after countdown (or no players left). Resetting to waiting state.")
                    self.countdown_active = False
                    self.waiting_for_players = True # Zurück zum Wartezustand
                    # game_started bleibt False
            # Der Visualizer zeigt countdown_seconds_remaining an

        # Spielspezifische Updates (Projektile, Power-Ups etc.) nur, wenn das Spiel gestartet ist
        if self.game_started:
            for shape in self.space.shapes:
                # Spieler wurden bereits oben aktualisiert
                if hasattr(shape, "sprite_ref") and not isinstance(shape.sprite_ref, Triangle):
                    shape.sprite_ref.update(dt) # Projektile, PowerUps etc.
        # Wenn game_started False ist (d.h. waiting_for_players oder countdown_active),
        # werden diese spielspezifischen Updates übersprungen.

    async def _run_physics_loop(self, dt):
        """
        Runs the continuous physics simulation loop asynchronously.
        
        This method is intended to be run as an asyncio task. It repeatedly calls update()
        and then sleeps for the given delta time.
        
        Args:
            dt (float): Delta time between physics updates.
        """
        while self.is_running:
            self.update(dt)
            await asyncio.sleep(dt)

    def start_physics_engine(self, dt=PHYSICS_DT):
        """
        Starts the physics engine in an asynchronous loop.
        
        Attempts to retrieve the current event loop or creates a new one if necessary 
        (running it in a separate daemon thread). Schedules the physics loop as a task.
        
        Args:
            dt (float, optional): Delta time between physics updates. Defaults to PHYSICS_DT.
        """
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # No running event loop; create a new one and run it in a daemon thread.
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            threading.Thread(target=loop.run_forever, daemon=True).start()
        self.is_running = True
        self._physics_task = loop.create_task(self._run_physics_loop(dt))

    def stop_physics_engine(self):
        """
        Stops the physics engine loop and cancels the associated asyncio task.
        """
        if self.is_running:
            self.is_running = False
            if self._physics_task:
                self._physics_task.cancel()
                self._physics_task = None

    def to_dict(self):
        """
        Serializes the current game state to a dictionary.
        
        Returns:
            dict: Contains player states, object states (excluding players), and shot count.
        """
        return {
            "game_started": self.game_started,
            "waiting_for_players": self.waiting_for_players,
            "countdown_active": self.countdown_active,
            "countdown_seconds_remaining": math.ceil(self.countdown_seconds_remaining) if self.countdown_active else 0,
            "players": [
                {
                    "id": pid,
                    "position": [p.body.position.x, p.body.position.y],
                    "angle": math.degrees(p.body.angle),
                    "health": p.health,
                    "ready": p.ready # Spieler-Bereitschaftsstatus hinzufügen
                } for pid, p in self.players.items()
            ],
            "objects": [obj.to_dict() for obj in self.objects if not isinstance(obj, Triangle)],
            "shots_fired": self.shot_count,
        }
    
    def get_relative_state_for_player(self, player_id):
        """
        Returns a relative view of the game state from a player's perspective.
        
        The returned state includes the player's health, velocity, angular velocity, and nearby objects 
        (players, obstacles, projectiles, and borders) within a specified scanning radius.
        
        Args:
            player_id (str): The identifier of the player.
        
        Returns:
            dict or None: The relative game state or None if the player is not found.
        """
        if not self.game_started: 
            return
        player = self.players.get(player_id)
        if not player:
            return None

        player_pos = player.body.position
        player_angle_rad = player.body.angle
        player_vel = player.body.velocity
        player_angular_vel = player.body.angular_velocity
        player_health = player.health
        radius = SCANNING_RADIUS

        nearby_objects_relative = []
        
        # Process non-player objects (obstacles, projectiles).
        for obj in self.objects:
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

                if obj_type != "unknown":
                    nearby_objects_relative.append({
                        "type": obj_type,
                        "relative_position": [relative_pos_rotated.x, relative_pos_rotated.y],
                        "relative_velocity": [relative_vel_rotated.x, relative_vel_rotated.y],
                        "distance": distance,
                        "color": getattr(obj, 'color', None) if obj_type == "projectile" else None
                    })

        # Process other players.
        for other_pid, other_player in self.players.items():
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
                    "color": other_player.color,
                })

        # Process borders
        for shape in self.space.shapes:
            if isinstance(shape, pymunk.Segment) and shape.collision_type == 3:  # Border collision type
                # Calculate the shortest distance from the player to the border segment
                query_info = shape.point_query(player_pos)
                distance = query_info.distance

                if distance <= radius:
                    # Calculate the relative position of the closest point on the border
                    closest_point = query_info.point
                    delta_pos = closest_point - player_pos
                    relative_pos_rotated = delta_pos.rotated(-player_angle_rad)

                    nearby_objects_relative.append({
                        "type": "border",
                        "relative_position": [relative_pos_rotated.x, relative_pos_rotated.y],
                        "distance": distance
                    })

        return {
            "game_started": self.game_started,
            "waiting_for_players": self.waiting_for_players,
            "countdown_active": self.countdown_active,
            "countdown_seconds_remaining": math.ceil(self.countdown_seconds_remaining) if self.countdown_active else 0,
            "player_id": player_id,
            "health": player_health,
            "angular_velocity": player_angular_vel,
            "velocity": [player_vel.x, player_vel.y],
            "ready": player.ready,  # Player's readiness status
            "nearby_objects": nearby_objects_relative
        }

    def run_visualizer(self):
        """
        Runs the Pygame visualizer which is used for debugging and visualization.
        
        This function initializes Pygame, creates the window, processes events, updates 
        all sprites, draws static elements (like obstacles), displays health bars, and updates the screen.
        The loop runs until the window is closed.
        """
        pygame.init()
        screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Game Visualizer")
        clock = pygame.time.Clock()
        all_game_sprites = pygame.sprite.Group()
        running = True
        font = pygame.font.SysFont(None, 36) # Slightly larger font

        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

            screen.fill((0, 0, 0)) # Always fill background black

            all_game_sprites.empty()

            # Always add players to the sprite group
            for player in self.players.values():
                all_game_sprites.add(player)

            # Add obstacles and other objects (projectiles, power-ups)
            for obj in self.objects:
                if isinstance(obj, pygame.sprite.Sprite):
                    all_game_sprites.add(obj)
            
            dt_visual = clock.tick(FPS) / 1000.0
            all_game_sprites.update(dt_visual) # Sprite updates (position, alpha, etc.)
            all_game_sprites.draw(screen) # Draw all sprites

            # Display health bars
            bar_width = 30; bar_height = 5; bar_offset_y = 5
            health_color = (0, 255, 0); lost_health_color = (255, 0, 0); border_color = (255, 255, 255)
            for player in self.players.values():
                bar_x = player.rect.centerx - bar_width // 2
                bar_y = player.rect.bottom + bar_offset_y
                health_percentage = max(0, player.health / PLAYER_START_HEALTH)
                background_rect = pygame.Rect(bar_x, bar_y, bar_width, bar_height)
                pygame.draw.rect(screen, lost_health_color, background_rect)
                current_bar_width = int(bar_width * health_percentage)
                if current_bar_width > 0:
                    health_rect = pygame.Rect(bar_x, bar_y, current_bar_width, bar_height)
                    pygame.draw.rect(screen, health_color, health_rect)
                pygame.draw.rect(screen, border_color, background_rect, 1)

            # Text display based on game state
            display_text = ""
            text_color = (255, 255, 0) # Default Yellow

            if self.waiting_for_players:
                display_text = "Waiting for players..."
            elif self.game_started and self.countdown_active: 
                display_text = ""
                text_color = (0, 0, 0)
            elif self.countdown_active:
                display_text = f"Game starting in {math.ceil(self.countdown_seconds_remaining)}..."
                text_color = (0, 255, 255) # Cyan for countdown
            
            if display_text: # Only render and blit if there's text to display
                text_surface = font.render(display_text, True, text_color)
                text_rect = text_surface.get_rect(center=(self.width // 2, 30))
                screen.blit(text_surface, text_rect)

            pygame.display.flip()

        pygame.quit()

# Create global instance after initialization:
game_world_instance = GameWorld(SCREEN_WIDTH, SCREEN_HEIGHT)
# game_world_instance.initialize_world() # Wird jetzt durch check_if_all_players_ready() bzw. start_physics_engine() gehandhabt