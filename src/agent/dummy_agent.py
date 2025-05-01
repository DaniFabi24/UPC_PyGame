import pygame
import requests
import sys
from ..settings import API_URL # Stelle sicher, dass API_URL korrekt ist

class Agent:
    def __init__(self):
        self.player_id = None
        self.connect()

    def connect(self):
        try:
            response = requests.post(f"{API_URL}/connect")
            response.raise_for_status()
            data = response.json()
            self.player_id = data.get("player_id")
            if self.player_id:
                print(f"Connected successfully. Player ID: {self.player_id}")
            else:
                print("Error: Could not get Player ID from server.")
                sys.exit(1) # Beenden, wenn keine ID erhalten wurde
        except requests.exceptions.RequestException as e:
            print(f"Error connecting to server: {e}")
            sys.exit(1)

    def disconnect(self):
         if self.player_id:
             try:
                 print(f"Disconnecting player {self.player_id}...")
                 response = requests.post(f"{API_URL}/disconnect/{self.player_id}")
                 response.raise_for_status()
                 print("Disconnected successfully.")
             except requests.exceptions.RequestException as e:
                 print(f"Error disconnecting from server: {e}")

    def send_action(self, action_path):
        if not self.player_id:
            print("Error: No Player ID. Cannot send action.")
            return
        try:
            url = f"{API_URL}/player/{self.player_id}/{action_path}"
            response = requests.post(url)
            response.raise_for_status()
            # print(f"Action '{action_path}' sent.") # Optional: Weniger Output
        except requests.exceptions.RequestException as e:
            print(f"Error sending action '{action_path}': {e}")

    def run(self):
        pygame.init()
        screen = pygame.display.set_mode((300, 200))
        pygame.display.set_caption(f"Agent - Player {self.player_id}")
        clock = pygame.time.Clock()

        running = True
        while running:
            screen.fill((255, 255, 255))
            pygame.display.flip()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_SPACE:
                        self.send_action("shoot")

            keys = pygame.key.get_pressed()
            if keys[pygame.K_UP]:
                self.send_action("thrust_forward")
            elif keys[pygame.K_DOWN]:
                self.send_action("thrust_backward") # Annahme: Endpunkt existiert

            if keys[pygame.K_LEFT]:
                self.send_action("rotate_left")
            elif keys[pygame.K_RIGHT]:
                self.send_action("rotate_right")

            clock.tick(30)

        self.disconnect() # Beim Beenden der Schleife trennen
        pygame.quit()

if __name__ == "__main__":
    agent = Agent()
    agent.run()