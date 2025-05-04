import pygame
import math
import pymunk
import time
from ..settings import *

class Triangle(pygame.sprite.Sprite):
    def __init__(self, position, angle=0, color=(0, 128, 255), game_world=None):
        super().__init__()
        self.color = color
        self.radius = 15
        self.game_world = game_world
        self.health = PLAYER_START_HEALTH # *** NEU: Leben hinzufügen ***
        self.player_id = None # Wird von GameWorld gesetzt
        # *** NEU: Spawn-Schutz Timer ***
        self.spawn_protection_duration = 3.0 # Sekunden
        self.spawn_protection_until = time.time() + self.spawn_protection_duration
        mass = 1
        moment = pymunk.moment_for_poly(mass, [
            (self.radius, 0),
            (-self.radius, self.radius),
            (-self.radius, -self.radius)])
        self.body = pymunk.Body(mass, moment)
        self.body.position = position
        self.body.angle = math.radians(angle)
        self.body.damping = 0.99
        self.shape = pymunk.Poly(self.body, [
            (self.radius, 0),
            (-self.radius, self.radius),
            (-self.radius, -self.radius)
        ])
        self.shape.collision_type = 1
        self.shape.sprite_ref = self
        if game_world:
            game_world.space.add(self.body, self.shape)
        # Erstelle das ursprüngliche Bild und speichere es:
        self.original_image = pygame.Surface((self.radius * 2, self.radius * 2), pygame.SRCALPHA)
        self._create_base_image()
        self.image = self.original_image.copy()
        self.rect = self.image.get_rect(center=position)

    def _create_base_image(self):
        self.original_image.fill((0, 0, 0, 0))  # Transparenter Hintergrund
        # Berechne die Punkte des Dreiecks relativ zum Mittelpunkt der Surface
        center_x, center_y = self.radius, self.radius
        points = [
            (center_x + self.radius * math.cos(math.radians(deg)),
             center_y - self.radius * math.sin(math.radians(deg)))
            for deg in [0, 120, 240]
        ]
        pygame.draw.polygon(self.original_image, self.color, points)

        # Füge einen Indikator an der Spitze hinzu (bei 0 Grad)
        tip_x = center_x + self.radius * math.cos(math.radians(0))
        tip_y = center_y - self.radius * math.sin(math.radians(0))
        indicator_color = (255, 0, 0)  # Rot als Indikatorfarbe
        indicator_radius = 3
        pygame.draw.circle(self.original_image, indicator_color, (int(tip_x), int(tip_y)), indicator_radius)

    def update(self, dt):
        pos = self.body.position
        self.rect.center = (int(pos.x), int(pos.y))
        self.angle = math.degrees(self.body.angle)
        # Berechne Rotation ausgehend vom Originalbild
        rotated_image = pygame.transform.rotate(self.original_image, -self.angle)
        self.rect = rotated_image.get_rect(center=self.rect.center)
        self.image = rotated_image
        # *** Optional: Visuelles Feedback für Spawn-Schutz ***
        if time.time() < self.spawn_protection_until:
            # Lässt das Sprite leicht transparent erscheinen
            alpha = 128 # 0=transparent, 255=opak
            self.image.set_alpha(alpha)
        else:
            # Normale Deckkraft wiederherstellen
            self.image.set_alpha(255)

    def take_damage(self, amount):
        """Reduziert die Lebenspunkte des Spielers."""
        # *** NEU: Spawn-Schutz Prüfung ***
        if time.time() < self.spawn_protection_until:
            print(f"Player {self.player_id} is spawn protected. Damage ignored.")
            return # Keinen Schaden nehmen

        self.health -= amount
        print(f"Player {self.player_id} took {amount} damage. Current health: {self.health}")
        if self.health <= 0:
            print(f"Player {self.player_id} destroyed!")
            self.remove_from_world() # Spieler entfernen

    def remove_from_world(self):
        """Entfernt den Spieler aus der Spielwelt und allen relevanten Sammlungen."""
        if self.game_world:
            # Aus Physik-Engine entfernen
            if self.body in self.game_world.space.bodies:
                self.game_world.space.remove(self.body)
            if self.shape in self.game_world.space.shapes:
                self.game_world.space.remove(self.shape)
            
            # Aus Objektliste entfernen
            if self in self.game_world.objects:
                self.game_world.objects.remove(self)
                
            # Aus Spieler-Dictionary entfernen (anhand der ID)
            player_id_to_remove = None
            for pid, player_obj in self.game_world.players.items():
                if player_obj is self:
                    player_id_to_remove = pid
                    break
            if player_id_to_remove in self.game_world.players:
                del self.game_world.players[player_id_to_remove]
                print(f"Player {player_id_to_remove} removed from players dictionary.")

        self.kill() # Aus Pygame Sprite-Gruppen entfernen
        print(f"Player sprite killed.")

class CircleObstacle(pygame.sprite.Sprite):
    def __init__(self, position, radius, color=(128, 128, 128), game_world=None):
        super().__init__()
        self.color = color
        self.radius = radius
        self.game_world = game_world
        mass = 1
        moment = pymunk.moment_for_circle(mass, 0, radius)
        self.body = pymunk.Body(body_type=pymunk.Body.STATIC)
        self.body.position = position
        self.shape = pymunk.Circle(self.body, radius)
        self.shape.collision_type = 2
        self.shape.sprite_ref = self
        # Set physical properties for bouncing interaction
        self.shape.elasticity = 0.9 # Make obstacles bouncy too
        self.shape.friction = 0.5   # Some friction

        if game_world:
            game_world.space.add(self.body, self.shape)
        self.image = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(self.image, color, (radius, radius), radius)
        self.rect = self.image.get_rect(center=position)

    def update(self, dt):
        pos = self.body.position
        self.rect.center = (int(pos.x), int(pos.y))

    def to_dict(self):
        return {
            "type": "circle",
            "position": [self.body.position.x, self.body.position.y],
            "radius": self.radius
        }

class Projectile(pygame.sprite.Sprite):
    def __init__(self, position, angle_rad, owner, color=PROJECTILE_COLOR, radius=PROJECTILE_RADIUS, speed=PROJECTILE_SPEED, game_world=None):
        super().__init__()
        self.color = color
        self.radius = radius
        self.game_world = game_world
        self.lifetime = PROJECTILE_LIFETIME_SECONDS # Seconds until the projectile is removed
        self.owner = owner # *** NEU: Besitzer des Projektils speichern ***

        mass = 0.1 # Projectiles should be light
        moment = pymunk.moment_for_circle(mass, 0, radius)
        self.body = pymunk.Body(mass, moment)
        self.body.position = position
        self.body.angle = angle_rad # Set initial angle if needed, though velocity is key
        
        # Calculate initial velocity based on angle and speed
        velocity_x = math.cos(angle_rad) * speed
        velocity_y = math.sin(angle_rad) * speed
        self.body.velocity = (velocity_x, velocity_y)

        self.shape = pymunk.Circle(self.body, radius)
        self.shape.collision_type = 4 # Assign a new collision type for projectiles
        self.shape.sensor = False # Make sure it collides
        self.shape.sprite_ref = self # Reference for updates/drawing
        self.shape.elasticity = 0.6 # Make obstacles bouncy too
        self.shape.friction = 0.1   # Some friction
        # *** WICHTIG: Filter anpassen, damit Projektil NICHT mit dem Schützen kollidiert ***
        # Gruppe 1 für Spieler, Gruppe 2 für Projektile (Beispiel)
        # Projektile (Gruppe 2) kollidieren nicht mit Spieler (Gruppe 1)
        # Sie kollidieren aber mit Hindernissen und Rändern (die keine Gruppe haben oder Gruppe 0)
        # Und sie kollidieren mit anderen Spielern (falls Multiplayer, die auch Gruppe 1 haben könnten)
        # Für Einzelspieler reicht es oft, die Kollision mit dem *eigenen* Spieler zu verhindern.
        # Wir verwenden hier den Owner-Check im Handler statt Filter für mehr Flexibilität.
        # self.shape.filter = pymunk.ShapeFilter(group=1) # Vorerst auskommentiert, da wir Owner-Check machen

        if game_world:
            game_world.space.add(self.body, self.shape)
            game_world.add_object(self) # Add to the game world's object list

        # Create the visual representation
        self.image = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(self.image, color, (radius, radius), radius)
        self.rect = self.image.get_rect(center=position)

    def update(self, dt):
        # Update position for drawing
        pos = self.body.position
        self.rect.center = (int(pos.x), int(pos.y))
        
        # Decrease lifetime and remove if expired
        self.lifetime -= dt
        if self.lifetime <= 0:
            self.remove_from_world()

    def remove_from_world(self):
         if self.game_world:
            if self.body in self.game_world.space.bodies:
                self.game_world.space.remove(self.body)
            if self.shape in self.game_world.space.shapes:
                self.game_world.space.remove(self.shape)
            if self in self.game_world.objects:
                self.game_world.objects.remove(self)
            self.kill() # Remove from any sprite groups

    def to_dict(self):
         # Optional: For serialization if needed
         return {
             "type": "projectile",
             "position": [self.body.position.x, self.body.position.y],
             "radius": self.radius
         }

def collision_begin(arbiter, space, data):
    shape_a, shape_b = arbiter.shapes
    game_world = data.get("game_world", None)
    if game_world:
        game_world.player_collisions += 1
    return True  

def player_hit_obstacle(arbiter, space, data):
    """Handles collision between player (1) and obstacle (2)."""
    player_shape, obstacle_shape = arbiter.shapes
    game_world = data.get("game_world", None)

    # Sicherstellen, dass es sich um den Spieler handelt und er Schaden nehmen kann
    if game_world and hasattr(player_shape, 'sprite_ref') and isinstance(player_shape.sprite_ref, Triangle):
        player_sprite = player_shape.sprite_ref
        player_sprite.take_damage(OBSTACLE_DAMAGE) # Schaden zufügen
        game_world.player_collisions += 1 # Kollisionen weiter zählen
        print(f"Player collided with obstacle. Health: {player_sprite.health}")
    else:
         # Fallback, falls die Shapes vertauscht sind
         player_shape, obstacle_shape = obstacle_shape, player_shape
         if game_world and hasattr(player_shape, 'sprite_ref') and isinstance(player_shape.sprite_ref, Triangle):
             player_sprite = player_shape.sprite_ref
             player_sprite.take_damage(OBSTACLE_DAMAGE)
             game_world.player_collisions += 1
             print(f"Player collided with obstacle (reversed shapes). Health: {player_sprite.health}")

    # True zurückgeben, damit Pymunk die Kollision physikalisch auflöst (Abprallen etc.)
    return True

def projectile_hit_player(arbiter, space, data):
    """Handles collision between projectile (4) and player (1)."""
    projectile_shape, player_shape = arbiter.shapes
    game_world = data.get("game_world", None)

    projectile = getattr(projectile_shape, 'sprite_ref', None)
    player = getattr(player_shape, 'sprite_ref', None)

    # Sicherstellen, dass beide Objekte existieren und vom richtigen Typ sind
    if not isinstance(projectile, Projectile) or not isinstance(player, Triangle):
        # Vertauschte Reihenfolge prüfen (falls Pymunk sie anders übergibt)
        projectile_shape, player_shape = player_shape, projectile_shape
        projectile = getattr(projectile_shape, 'sprite_ref', None)
        player = getattr(player_shape, 'sprite_ref', None)
        if not isinstance(projectile, Projectile) or not isinstance(player, Triangle):
             print("Collision 4-1: Invalid shapes found.")
             return False # Kollision ignorieren, wenn Objekte nicht passen

    # Eigenbeschuss prüfen
    if not ALLOW_FRIENDLY_FIRE and projectile.owner is player:
        print("Friendly fire disabled, ignoring hit.")
        # Projektil NICHT entfernen, damit es weiterfliegt
        return False # Kollision ignorieren (kein Schaden, kein Abprall)

    # Schaden anwenden
    print(f"Player hit by projectile! Applying {PROJECTILE_DAMAGE} damage.")
    player.take_damage(PROJECTILE_DAMAGE)

    # Projektil nach Treffer entfernen
    projectile.remove_from_world()

    # True zurückgeben, damit Pymunk die Kollision physikalisch kurz auflöst
    # (obwohl das Projektil entfernt wird, kann es einen kleinen Impuls geben)
    # False wäre auch möglich, wenn der Impuls unerwünscht ist.
    return True

def setup_collision_handlers(space, game_world):
    # Handler für Spieler (1) vs Hindernis (2)
    handler_player_obstacle = space.add_collision_handler(1, 2)
    # *** NEU: Den spezifischen Handler verwenden ***
    handler_player_obstacle.begin = player_hit_obstacle
    handler_player_obstacle.data["game_world"] = game_world

    # Handler für Projektil (4) vs Hindernis (2)
    handler_projectile_obstacle = space.add_collision_handler(4, 2)
    handler_projectile_obstacle.begin = projectile_hit_obstacle
    handler_projectile_obstacle.data["game_world"] = game_world

    # Handler für Projektil (4) vs Rand (3)
    handler_projectile_border = space.add_collision_handler(4, 3)
    handler_projectile_border.begin = projectile_hit_border
    handler_projectile_border.data["game_world"] = game_world

    # *** NEU: Handler für Projektil (4) vs Spieler (1) ***
    handler_projectile_player = space.add_collision_handler(4, 1)
    handler_projectile_player.begin = projectile_hit_player
    handler_projectile_player.data["game_world"] = game_world

    # Optional: Handler für Spieler (1) vs Rand (3)
    # ...

def projectile_hit_obstacle(arbiter, space, data):
    """Handles collision between projectile (4) and obstacle (2)."""
    projectile_shape, obstacle_shape = arbiter.shapes
    
    # --- Entferne oder kommentiere diese Zeilen aus, um das Projektil NICHT zu entfernen ---
    # if hasattr(projectile_shape, 'sprite_ref') and isinstance(projectile_shape.sprite_ref, Projectile):
    #     projectile_shape.sprite_ref.remove_from_world()
         
    # Optional: Füge hier Logik hinzu, wenn das Hindernis Schaden nehmen soll etc.
    # Zum Beispiel:
    # if hasattr(obstacle_shape, 'sprite_ref') and hasattr(obstacle_shape.sprite_ref, 'take_damage'):
    #      obstacle_shape.sprite_ref.take_damage(10) # Beispiel: 10 Schaden

    print("Projectile hit obstacle - bouncing off.") # Debug-Ausgabe

    # Gib True zurück, damit Pymunk die Kollision physikalisch auflöst (Abprallen)
    # basierend auf den elasticity/friction Werten der Shapes.
    return True 

def projectile_hit_border(arbiter, space, data):
    # Projektile werden weiterhin am Rand entfernt
    projectile_shape, border_shape = arbiter.shapes
    if hasattr(projectile_shape, 'sprite_ref') and isinstance(projectile_shape.sprite_ref, Projectile):
         projectile_shape.sprite_ref.remove_from_world()
    return True