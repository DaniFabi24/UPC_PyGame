import pygame
import requests
import sys
import json # Importiere json zum hübschen Drucken
from src.settings import API_URL # Stelle sicher, dass API_URL korrekt ist

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
                 # *** Korrigierter Endpunkt für disconnect ***
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
            
            # Fehlerbehandlung für 404 (Spieler nicht gefunden)
            if response.status_code == 404:
                print(f"Error: Player ID '{self.player_id}' not found on server. Stopping actions.")
                self.player_id = None # ID zurücksetzen
                # Hier könnte man die run-Schleife beenden oder reconnect versuchen
                return 

            response.raise_for_status() # Löst Fehler für andere HTTP-Fehlercodes aus
            # print(f"Action '{action_path}' sent.") # Optional: Weniger Output
        except requests.exceptions.RequestException as e:
            print(f"Error sending action '{action_path}': {e}")

    # *** NEUE METHODE zum Abfragen des Zustands ***
    def get_state(self):
        if not self.player_id:
            print("Error: No Player ID. Cannot get state.")
            return None
        try:
            # *** Korrekter Endpunkt für relativen Zustand ***
            url = f"{API_URL}/player/{self.player_id}/state" 
            response = requests.get(url) # GET-Request verwenden
            
            if response.status_code == 404:
                print(f"Error: Player ID '{self.player_id}' not found on server when getting state.")
                self.player_id = None
                return None

            response.raise_for_status()
            state_data = response.json()
            print("-" * 20)
            print("Current Relative State:")
            # Hübsche Ausgabe des JSON
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
        while running and self.player_id: # Schleife beenden, wenn player_id verloren geht
            screen.fill((255, 255, 255))
            pygame.display.flip()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_SPACE:
                        self.send_action("shoot")
                    # *** NEU: Zustand bei Enter abfragen ***
                    elif event.key == pygame.K_RETURN: 
                        self.get_state() 

            # Aktionen nur senden, wenn eine ID vorhanden ist
            if self.player_id:
                keys = pygame.key.get_pressed()
                if keys[pygame.K_UP]:
                    self.send_action("thrust_forward")
                elif keys[pygame.K_DOWN]:
                    self.send_action("thrust_backward") 

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