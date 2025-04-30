import pygame
import math
import pymunk

class Triangle(pygame.sprite.Sprite):
    def __init__(self, position, angle=0, color=(0, 128, 255), game_world=None):
        super().__init__()
        self.color = color
        self.radius = 15
        self.game_world = game_world
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

def collision_begin(arbiter, space, data):
    shape_a, shape_b = arbiter.shapes
    game_world = data.get("game_world", None)
    if game_world:
        game_world.player_collisions += 1
    return True  

def setup_collision_handlers(space, game_world):
    handler = space.add_collision_handler(1, 2)
    handler.begin = collision_begin
    handler.data["game_world"] = game_world