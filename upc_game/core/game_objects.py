import pygame
import math

class Triangle(pygame.sprite.Sprite):
    def __init__(self, position, angle=0, color=(0, 128, 255), game_world=None):
        super().__init__()
        self.position = list(position)
        self.angle = angle  # Angle in degrees
        self.color = color
        self.thrust_force = 0  # Current thrust force
        self.rotation_speed = 0 # Current rotation speed (degrees/second)
        self.mass = 1.0
        self.drag_coefficient = 0.01 # Simple air resistance coefficient
        self.velocity = [0.0, 0.0] # [vx, vy]
        self.angular_velocity = 0.0 # Angular velocity (degrees/second)
        self.radius = 15  # Approximate radius for collisions
        self.game_world = game_world
        # Erstelle ein Pygame Surface für das Dreieck
        self.image = pygame.Surface((self.radius * 2, self.radius * 2), pygame.SRCALPHA)
        pygame.draw.polygon(self.image, self.color, [
            (self.radius * math.cos(math.radians(0)), -self.radius * math.sin(math.radians(0))),
            (self.radius * math.cos(math.radians(120)), -self.radius * math.sin(math.radians(120))),
            (self.radius * math.cos(math.radians(240)), -self.radius * math.sin(math.radians(240)))
        ])
        self.rect = self.image.get_rect(center=self.position)

    def apply_force(self, force):
        acceleration_x = force[0] / self.mass
        acceleration_y = force[1] / self.mass
        return [acceleration_x, acceleration_y]

    def update(self, dt):
        # Convert angle to radians for math functions
        rad_angle = math.radians(self.angle)

        # Convert thrust to force (simple model)
        thrust_vector = [self.thrust_force * math.cos(rad_angle),
                         -self.thrust_force * math.sin(rad_angle)] # Pygame Y is downwards

        # Acceleration due to thrust
        acceleration = self.apply_force(thrust_vector)
        self.velocity[0] += acceleration[0] * dt
        self.velocity[1] += acceleration[1] * dt

        # Air resistance (proportional to velocity, opposite direction)
        drag_force_x = -self.drag_coefficient * self.velocity[0]
        drag_force_y = -self.drag_coefficient * self.velocity[1]
        drag_acceleration = self.apply_force([drag_force_x, drag_force_y])
        self.velocity[0] += drag_acceleration[0] * dt
        self.velocity[1] += drag_acceleration[1] * dt

        # Update position
        self.position[0] += self.velocity[0] * dt
        self.position[1] += self.velocity[1] * dt

        # Update angle
        self.angular_velocity += self.rotation_speed * dt
        self.angle += self.angular_velocity * dt

        # Limit angle to 0-360 degrees (optional)
        self.angle %= 360

        self.rect.center = [int(self.position[0]), int(self.position[1])] # Aktualisiere die Rect-Position

    def draw(self, surface):
        rotated_image = pygame.transform.rotate(self.image, -self.angle)
        rotated_rect = rotated_image.get_rect(center=self.rect.center)
        surface.blit(rotated_image, rotated_rect)

    def to_dict(self):
        return {
            "type": "triangle",
            "position": self.position,
            "angle": self.angle,
            "radius": self.radius
        }

class CircleObstacle(pygame.sprite.Sprite):
    def __init__(self, position, radius, color=(128, 128, 128)):
        super().__init__()
        self.position = list(position)
        self.radius = radius
        self.color = color
        self.image = pygame.Surface((self.radius * 2, self.radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(self.image, self.color, (self.radius, self.radius), self.radius)
        self.rect = self.image.get_rect(center=self.position)

    def draw(self, surface):
        surface.blit(self.image, self.rect)

    def to_dict(self):
        return {
            "type": "circle",
            "position": self.position,
            "radius": self.radius
        }