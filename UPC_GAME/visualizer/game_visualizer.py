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
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching world state: {e}")
        return None

def run_visualizer():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("UPC Game Visualizer")
    clock = pygame.time.Clock()

    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

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
                print("Shot fired!")
            except requests.exceptions.RequestException as e:
                print(f"Error sending shoot command: {e}")

        try:
            requests.post(f"{API_BASE_URL}/move", json={"thrust": thrust, "rotation": rotation})
        except requests.exceptions.RequestException as e:
            print(f"Error sending move command: {e}")

        # Fetch the entire world state from the server
        world_data = fetch_world_state()

        # Drawing
        screen.fill(BACKGROUND_COLOR)
        if world_data and "objects" in world_data:
            for obj_data in world_data["objects"]:
                if obj_data["type"] == "triangle":
                    pos = obj_data["position"]
                    angle = obj_data["angle"]
                    radius = 15
                    p1 = (pos[0] + radius * math.cos(math.radians(angle)),
                          pos[1] - radius * math.sin(math.radians(angle)))
                    p2 = (pos[0] + radius * math.cos(math.radians(angle + 120)),
                          pos[1] - radius * math.sin(math.radians(angle + 120)))
                    p3 = (pos[0] + radius * math.cos(math.radians(angle + 240)),
                          pos[1] - radius * math.sin(math.radians(angle + 240)))
                    pygame.draw.polygon(screen, (0, 128, 255), [p1, p2, p3])
                elif obj_data["type"] == "circle":
                    pos = obj_data["position"]
                    radius = obj_data["radius"]
                    pygame.draw.circle(screen, (128, 128, 128), (int(pos[0]), int(pos[1])), int(radius))

        pygame.display.flip()

    pygame.quit()

if __name__ == '__main__':
    run_visualizer()