import pygame
import time
import requests
import math

# API base URL
API_BASE_URL = "http://127.0.0.1:8000"

# Game world dimensions (should match server configuration)
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
BACKGROUND_COLOR = (0, 0, 0)
FPS = 60

def fetch_world_state():
    try:
        response = requests.get(f"{API_BASE_URL}/world_state")
        response.raise_for_status()  # Raise an exception for bad status codes
        data = response.json()
        print("WORLD DATA RECEIVED:", data)
        return data
    except requests.exceptions.RequestException as e:
        print(f"Error fetching world state: {e}")
        return None

def run_visualizer():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("UPC Game Visualizer")
    clock = pygame.time.Clock()
    font = pygame.font.Font(None, 30)

    running = True
    current_thrust = 0
    current_rotation = 0
    collided = False
    collision_timer = 0
    COLLISION_DURATION = 0.5
    COLLISION_RECT_WIDTH = 50
    COLLISION_RECT_HEIGHT = 50
    COLLISION_RECT_X = SCREEN_WIDTH - COLLISION_RECT_WIDTH - 10
    COLLISION_RECT_Y = 10
    shot_count = 0
    space_bar_pressed = False
    player_collisions = 0  # Hier initialisiert
    max_health = 5
    health_bar_width = 200
    health_bar_height = 20
    health_bar_x = (SCREEN_WIDTH - health_bar_width) // 2
    health_bar_y = 10

    while running:
        dt = clock.tick(FPS) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_c:
                    collided = True
                    collision_timer = COLLISION_DURATION
                elif event.key == pygame.K_SPACE and not space_bar_pressed:
                    try:
                        requests.post(f"{API_BASE_URL}/shoot")
                        print("Shot fired (Client)!")
                        space_bar_pressed = True
                    except requests.exceptions.RequestException as e:
                        print(f"Error sending shoot command: {e}")
            elif event.type == pygame.KEYUP:
                if event.key == pygame.K_SPACE:
                    space_bar_pressed = False

        # Control via keyboard input and API calls
        thrust = 0
        rotation = 0
        keys = pygame.key.get_pressed()
        if keys[pygame.K_UP]:
            thrust = 50
        if keys[pygame.K_DOWN]:
            thrust = -20
        if keys[pygame.K_LEFT]:
            rotation = -2
        if keys[pygame.K_RIGHT]:
            rotation = 2

        try:
            requests.post(f"{API_BASE_URL}/move", json={"thrust": thrust, "rotation": rotation})
            current_thrust = thrust
            current_rotation = rotation
        except requests.exceptions.RequestException as e:
            print(f"Error sending move command: {e}")

        # Fetch the entire world state from the server
        world_data = fetch_world_state()
        if world_data:
            if "objects" in world_data:
                objects = world_data["objects"]
            if "shot_count" in world_data:
                shot_count = world_data["shot_count"]
            if "player_collisions" in world_data:
                player_collisions = world_data["player_collisions"] # HIER WIRD DER WERT VOM SERVER AKTUALISIERT
            if "collided" in world_data and world_data["collided"]:
                collided = True
                collision_timer = COLLISION_DURATION

        # Drawing
        screen.fill(BACKGROUND_COLOR)
        if world_data and "objects" in world_data:
            for obj_data in world_data["objects"]:
                if obj_data["type"] == "triangle":
                    pos = obj_data["position"]
                    angle = obj_data["angle"]
                    radius = obj_data.get("radius", 15)
                    p1 = (pos[0] + radius * math.cos(math.radians(angle)), pos[1] - radius * math.sin(math.radians(angle)))
                    p2 = (pos[0] + radius * math.cos(math.radians(angle + 120)), pos[1] - radius * math.sin(math.radians(angle + 120)))
                    p3 = (pos[0] + radius * math.cos(math.radians(angle + 240)), pos[1] - radius * math.sin(math.radians(angle + 240)))
                    pygame.draw.polygon(screen, (0, 128, 255), [p1, p2, p3])
                elif obj_data["type"] == "circle":
                    pos = obj_data["position"]
                    radius = obj_data["radius"]
                    pygame.draw.circle(screen, (128, 128, 128), (int(pos[0]), int(pos[1])), int(radius))

        # Anzeigen zeichnen (Schub, Rotation oben links)
        thrust_text = font.render(f"Thrust: {current_thrust}", True, (255, 255, 255))
        rotation_text = font.render(f"Rotation: {current_rotation}", True, (255, 255, 255))
        screen.blit(thrust_text, (10, 10))
        screen.blit(rotation_text, (10, 40))

        # Lebensanzeige (oben mittig)
        health_percentage = max(0, (max_health - player_collisions) / max_health)
        health_bar_fill_width = int(health_bar_width * health_percentage)
        health_bar_rect = pygame.Rect(health_bar_x, health_bar_y, health_bar_width, health_bar_height)
        health_fill_rect = pygame.Rect(health_bar_x, health_bar_y, health_bar_fill_width, health_bar_height)
        health_bar_color = (0, 255, 0)

        if health_percentage <= 0.4:
            health_bar_color = (255, 0, 0)
        elif health_percentage <= 0.7:
            health_bar_color = (255, 255, 0)

        pygame.draw.rect(screen, (50, 50, 50), health_bar_rect)
        pygame.draw.rect(screen, health_bar_color, health_fill_rect)

        # Kollisionszähler als Zahl (oben rechts)
        collision_counter_text = font.render(f"Collisions: {player_collisions}", True, (255, 255, 255))
        collision_counter_rect = collision_counter_text.get_rect(topright=(SCREEN_WIDTH - 10, 10))
        screen.blit(collision_counter_text, collision_counter_rect)

        # Schusszähler unten mittig
        shot_text = font.render(f"Shots: {shot_count}", True, (255, 255, 255))
        text_rect = shot_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 30))
        screen.blit(shot_text, text_rect)

        # Kollisionsanzeige (rotes Rechteck)
        if collided:
            pygame.draw.rect(screen, (255, 0, 0), (COLLISION_RECT_X, COLLISION_RECT_Y, COLLISION_RECT_WIDTH, COLLISION_RECT_HEIGHT))
            collision_timer -= dt
            if collision_timer <= 0:
                collided = False

        pygame.display.flip()

    pygame.quit()

if __name__ == '__main__':
    run_visualizer()