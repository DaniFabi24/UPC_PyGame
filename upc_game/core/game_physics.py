from .game_objects import Triangle, CircleObstacle
import asyncio
import pygame

async def physics_loop(world, dt):
    while True:
        world.update(dt)
        await asyncio.sleep(dt)

def check_collision(obj1, obj2):
    if isinstance(obj1, pygame.sprite.Sprite) and isinstance(obj2, pygame.sprite.Sprite):
        print(f"Prüfe Kollision zwischen: {type(obj1)} und {type(obj2)}")
        pos1 = pygame.math.Vector2(obj1.rect.center)
        pos2 = pygame.math.Vector2(obj2.rect.center)
        distance = pos1.distance_to(pos2)

        radius1 = getattr(obj1, 'radius', obj1.rect.width / 2)
        radius2 = getattr(obj2, 'radius', obj2.rect.height / 2)

        collided = distance < radius1 + radius2
        print(f"Abstand: {distance}, Summe Radien: {radius1 + radius2}, Kollision: {collided}")
        return collided
    return False