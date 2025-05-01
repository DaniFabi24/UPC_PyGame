import pymunk
import pygame
import threading
import asyncio
import uuid
from .game_objects import *
from ..settings import *

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
        self.add_borders()
        
    def add_player(self):
        """Erstellt einen neuen Spieler, weist eine ID zu und gibt die ID zurück."""
        player_id = str(uuid.uuid4())
        start_pos = [self.width / 2, self.height / 2] # Oder zufällige Position
        new_player = Triangle(start_pos, game_world=self)
        new_player.player_id = player_id # ID am Objekt speichern (optional, aber nützlich)
        self.players[player_id] = new_player
        self.add_object(new_player) # Fügt auch zur Physik-Engine hinzu
        print(f"Player added with ID: {player_id}")
        return player_id

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
        self.add_object(CircleObstacle([200, 200], 30, game_world=self))
        self.add_object(CircleObstacle([600, 400], 50, game_world=self))
        self.add_object(CircleObstacle([600, 300], 70, game_world=self))
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
            player_angle_rad = player.body.angle
            offset_distance = player.radius + PROJECTILE_RADIUS + 1
            start_offset_x = math.cos(player_angle_rad) * offset_distance
            start_offset_y = math.sin(player_angle_rad) * offset_distance
            start_pos = player.body.position + pymunk.Vec2d(start_offset_x, start_offset_y)

            projectile = Projectile(
                position=start_pos,
                angle_rad=player_angle_rad,
                owner=player,
                game_world=self
            )
            self.increment_shot_count()
            print(f"Shot fired! Total shots: {self.shot_count}")

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

    def run_visualizer(self):
        pygame.init()
        screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Game Visualizer")
        clock = pygame.time.Clock()

        # Erzeuge einen statischen Hintergrund (optional, kann Performance verbessern)
        background = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        background.fill((0, 0, 0))
        static_sprites = pygame.sprite.Group()
        # Finde statische Objekte (z.B. Hindernisse) und zeichne sie einmal auf den Hintergrund
        # WICHTIG: Dies setzt voraus, dass Hindernisse nicht zur Laufzeit hinzugefügt/entfernt werden.
        # Wenn doch, muss der Hintergrund neu gezeichnet werden.
        for obj in self.objects:
             if isinstance(obj, CircleObstacle): # Nur statische Hindernisse
                 static_sprites.add(obj)
        static_sprites.draw(background)

        running = True
        while running:
            screen.blit(background, (0, 0)) # Zeichne Hintergrund mit statischen Elementen

            # Erstelle die Gruppe der *aktuell* aktiven Sprites für diesen Frame
            # Dies stellt sicher, dass entfernte Objekte nicht mehr gezeichnet werden.
            current_sprites = pygame.sprite.Group()
            # Füge alle Spieler hinzu, die noch im Dictionary sind
            for player in self.players.values():
                 current_sprites.add(player)
            # Füge alle anderen Objekte hinzu (z.B. Projektile)
            for obj in self.objects:
                 if isinstance(obj, Projectile): # Nur dynamische Objekte hier hinzufügen
                     current_sprites.add(obj)

            # Zeichne alle aktuellen Sprites
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