import asyncio

async def physics_loop(world, dt):
    while True:
        world.update(dt)
        await asyncio.sleep(dt)

def check_collision(object1, object2):
    # Simple circle collision check based on approximate radius of the triangle
    if isinstance(object1, Triangle) and isinstance(object2, CircleObstacle):
        distance_squared = (object1.position[0] - object2.position[0])**2 + (object1.position[1] - object2.position[1])**2
        radius_sum_squared = (object1.radius + object2.radius)**2
        return distance_squared < radius_sum_squared
    elif isinstance(object1, CircleObstacle) and isinstance(object2, Triangle):
        return check_collision(object2, object1)
    return False