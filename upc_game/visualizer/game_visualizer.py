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
    shot_count = 0 # Entferne die lokale shot_count-Variable

    while running:
        dt = clock.tick(FPS) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_c:
                collided = True
                collision_timer = COLLISION_DURATION

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
        if keys[pygame.K_SPACE]:
            try:
                requests.post(f"{API_BASE_URL}/shoot")
                print("Shot fired (Client)!")
            except requests.exceptions.RequestException as e:
                print(f"Error sending shoot command: {e}")

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
                # Zeichnen der Objekte bleibt gleich
            if "shot_count" in world_data:
                shot_count = world_data["shot_count"] # Aktualisiere die Schusszahl vom Server
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
                    radius = obj_data.get("radius", 15) # Sichere Zugriff auf Radius
                    p1 = (pos[0] + radius * math.cos(math.radians(angle)), pos[1] - radius * math.sin(math.radians(angle)))
                    p2 = (pos[0] + radius * math.cos(math.radians(angle + 120)), pos[1] - radius * math.sin(math.radians(angle + 120)))
                    p3 = (pos[0] + radius * math.cos(math.radians(angle + 240)), pos[1] - radius * math.sin(math.radians(angle + 240)))
                    pygame.draw.polygon(screen, (0, 128, 255), [p1, p2, p3])
                elif obj_data["type"] == "circle":
                    pos = obj_data["position"]
                    radius = obj_data["radius"]
                    pygame.draw.circle(screen, (128, 128, 128), (int(pos[0]), int(pos[1])), int(radius))

        # Anzeigen zeichnen (Schuss, Schub, Rotation)
        shot_text = font.render(f"Shots: {shot_count}", True, (255, 255, 255))
        thrust_text = font.render(f"Thrust: {current_thrust}", True, (255, 255, 255))
        rotation_text = font.render(f"Rotation: {current_rotation}", True, (255, 255, 255))
        screen.blit(shot_text, (10, 10))
        screen.blit(thrust_text, (10, 40))
        screen.blit(rotation_text, (10, 70))

        # Kollisionsanzeige
        if collided:
            pygame.draw.rect(screen, (255, 0, 0), (COLLISION_RECT_X, COLLISION_RECT_Y, COLLISION_RECT_WIDTH, COLLISION_RECT_HEIGHT))
            collision_timer -= dt
            if collision_timer <= 0:
                collided = False

        pygame.display.flip()

    pygame.quit()

if __name__ == '__main__':
    run_visualizer()