import pygame
import math

class Triangle(pygame.sprite.Sprite):
    def __init__(self, position, angle=0, color=(0, 128, 255)):
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

    def draw(self, surface):
        # Calculate the vertices of the triangle
        p1 = (self.position[0] + self.radius * math.cos(math.radians(self.angle)),
              self.position[1] - self.radius * math.sin(math.radians(self.angle)))
        p2 = (self.position[0] + self.radius * math.cos(math.radians(self.angle + 120)),
              self.position[1] - self.radius * math.sin(math.radians(self.angle + 120)))
        p3 = (self.position[0] + self.radius * math.cos(math.radians(self.angle + 240)),
              self.position[1] - self.radius * math.sin(math.radians(self.angle + 240)))
        pygame.draw.polygon(surface, self.color, [p1, p2, p3])

class CircleObstacle(pygame.sprite.Sprite):
    def __init__(self, position, radius, color=(128, 128, 128)):
        super().__init__()
        self.position = list(position)
        self.radius = radius
        self.color = color

    def draw(self, surface):
        pygame.draw.circle(surface, self.color, (int(self.position[0]), int(self.position[1])), self.radius)