import pygame
import requests
import sys
import json
import time
from src.settings import API_URL

class Agent:
    def __init__(self):
        self.player_id = None
        self.connect()

    def connect(self):
        try:
            team_name = "FoFo"
            response = requests.post(
                f"{API_URL}/connect",
                json={"agent_name": team_name}
            )
            response.raise_for_status()
            data = response.json()
            self.player_id = data.get("player_id")
            if self.player_id:
                print(f"Connected successfully. Player ID: {self.player_id}")
            else:
                print("Error: Could not get Player ID from server.")
                sys.exit(1)
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
                sys.exit(1)
            except requests.exceptions.RequestException as e:
                print(f"Error disconnecting from server: {e}")

    def send_action(self, action_path):
        if not self.player_id:
            print("Error: No Player ID. Cannot send action.")
            return
        try:
            url = f"{API_URL}/player/{self.player_id}/{action_path}"
            response = requests.post(url)
            if response.status_code == 404:
                print(
                    f"Error: Player ID '{self.player_id}' not found on server. "
                    "Stopping actions."
                )
                self.player_id = None
                return
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"Error sending action '{action_path}': {e}")

    def get_state(self):
        if not self.player_id:
            print("Error: No Player ID. Cannot get state.")
            return None
        try:
            url = f"{API_URL}/player/{self.player_id}/scan"
            response = requests.get(url)
            response.raise_for_status()
            state_data = response.json()
            print("-" * 20)
            print("Current Relative State:")
            print(json.dumps(state_data, indent=2))
            print("-" * 20)
            return state_data
        except requests.exceptions.RequestException as e:
            print(f"Error getting state: {e}")
            return None
        except json.JSONDecodeError:
            print("Error decoding state JSON from server.")
            return None

    def run(self):
        pygame.init()
        screen = pygame.display.set_mode((300, 200))
        pygame.display.set_caption(f"Agent - Player {self.player_id}")
        clock = pygame.time.Clock()

        running = True
        while running and self.player_id:
            screen.fill((255, 255, 255))
            pygame.display.flip()

            now = time.time()

            try:
                response = requests.get(f"{API_URL}/player/{self.player_id}/scan")
                response.raise_for_status()
                scan = response.json()
                if scan.get("time", 1) == 0:
                    continue
            except requests.exceptions.RequestException as e:
                print(f"Error checking time: {e}")

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_SPACE:
                        self.send_action("shoot")
                    elif event.key == pygame.K_RETURN:
                        try:
                            response = requests.get(f"{API_URL}/player/{self.player_id}/scan")
                            response.raise_for_status()
                            print(f"Game State: {response.json()}")
                        except requests.exceptions.RequestException as e:
                            print(f"Error polling game state: {e}")
                    elif event.key == pygame.K_RSHIFT:
                        try:
                            response = requests.post(f"{API_URL}/player/ready/{self.player_id}")
                            response.raise_for_status()
                            print(f"Player {self.player_id} is ready to play.")
                        except requests.exceptions.RequestException as e:
                            print(f"Error setting player ready: {e}")
                    elif event.key == pygame.K_LSHIFT:
                        try:
                            response = requests.get(f"{API_URL}/player/{self.player_id}/game-state")
                            response.raise_for_status()
                            print(f"Game State: {response.json()}")
                        except requests.exceptions.RequestException as e:
                            print(f"Error retrieving game state: {e}")
                    elif event.key == pygame.K_LCTRL:
                        try:
                            response = requests.get(f"{API_URL}/player/{self.player_id}/state")
                            response.raise_for_status()
                            print(f"Player State: {response.json()}")
                        except requests.exceptions.RequestException as e:
                            print(f"Error retrieving player state: {e}")
                    elif event.key == pygame.K_ESCAPE:
                        try:
                            response = requests.post(f"{API_URL}/game/restart")
                            response.raise_for_status()
                        except requests.exceptions.RequestException as e:
                            print(f"Error sending restart command: {e}")
                    elif event.key == pygame.K_1:
                        self.send_action("disconnect")

            # Auto-rotate and shoot continuously
            self.send_action("rotate_right")
            self.send_action("shoot")

            keys = pygame.key.get_pressed()
            if self.player_id:
                if keys[pygame.K_UP]:
                    self.send_action("thrust_forward")
                elif keys[pygame.K_DOWN]:
                    self.send_action("thrust_backward")
                if keys[pygame.K_LEFT]:
                    self.send_action("rotate_left")
                elif keys[pygame.K_RIGHT]:
                    self.send_action("rotate_right")

            clock.tick(30)

        self.disconnect()
        pygame.quit()


if __name__ == "__main__":
    agent = Agent()
    agent.run()
