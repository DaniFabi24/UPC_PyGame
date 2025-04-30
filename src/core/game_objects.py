import pygame
import math
import pymunk

class Triangle(pygame.sprite.Sprite):
    def __init__(self, position, angle=0, color=(0, 128, 255), game_world=None):
        super().__init__()
        self.color = color
        self.radius = 15
        self.game_world = game_world
        self.thrust = 0
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
        self.image = pygame.Surface((self.radius * 2, self.radius * 2), pygame.SRCALPHA)
        self.update_image()
        self.rect = self.image.get_rect(center=position)

    def update_image(self):
        self.image.fill((0, 0, 0, 0))
        points = [
            (self.radius + self.radius * math.cos(math.radians(deg)),
             self.radius - self.radius * math.sin(math.radians(deg)))
            for deg in [0, 120, 240]
        ]
        pygame.draw.polygon(self.image, self.color, points)

    def update(self, dt):
        pos = self.body.position
        self.rect.center = (int(pos.x), int(pos.y))
        self.angle = math.degrees(self.body.angle)
        rotated_image = pygame.transform.rotate(self.image, -self.angle)
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