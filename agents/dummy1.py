"""
Dummy Agent for UPC_PyGame

This agent connects to the game server, sends actions based on key presses,
and retrieves the game state relative to the agent's player perspective.

Dependencies:
- pygame: For handling graphics and key input.
- requests: For making HTTP requests to the game API.
"""

import pygame  # Used for creating a window, handling display and key events.
import requests  # Used for making HTTP requests to the game server.
import sys  # Used for exit() on critical errors.
import json  # Used for pretty-printing JSON responses.
from src.settings import API_URL  # API base URL for communicating with the server.

class Agent:
    """
    Represents a dummy game agent that connects to the game server,
    sends control actions, and prints the relative game state.
    """


    def __init__(self):
        """
        Initializes the agent and connects to the server to obtain a player ID.
        """
        self.player_id = None
        self.connect()

    def connect(self):
        """
        Connects to the game server by calling the '/connect' endpoint.
        On success, stores the player's ID.
        Terminates the program if unsuccessful.
        """
        try:
            response = requests.post(f"{API_URL}/connect")
            response.raise_for_status()  # Raises an exception for HTTP errors.
            data = response.json()
            self.player_id = data.get("player_id")
            if self.player_id:
                print(f"Connected successfully. Player ID: {self.player_id}")
            else:
                print("Error: Could not get Player ID from server.")
                sys.exit(1)  # Exit if no player ID is returned.
        except requests.exceptions.RequestException as e:
            print(f"Error connecting to server: {e}")
            sys.exit(1)

    def disconnect(self):
        """
        Disconnects the player from the game server by calling the '/disconnect/{player_id}' endpoint.
        Prints a success or error message based on the result.
        """
        if self.player_id:
            try:
                print(f"Disconnecting player {self.player_id}...")
                # Correct endpoint for disconnecting.
                response = requests.post(f"{API_URL}/disconnect/{self.player_id}")
                response.raise_for_status()
                print("Disconnected successfully.")
                sys.exit(1)
            except requests.exceptions.RequestException as e:
                print(f"Error disconnecting from server: {e}")

    def send_action(self, action_path):
        """
        Sends an action command to the server for the current player.

        The action_path should match one of the API endpoints (e.g. "shoot", "thrust_forward").

        Args:
            action_path (str): The action to perform.
        """
        if not self.player_id:
            print("Error: No Player ID. Cannot send action.")
            return
        try:
            url = f"{API_URL}/player/{self.player_id}/{action_path}"
            response = requests.post(url)

            # Handle 404 errors (player not found)
            if response.status_code == 404:
                print(
                    f"Error: Player ID '{self.player_id}' not found on server. "
                    "Stopping actions."
                )
                self.player_id = None  # Reset the player ID.
                return
            response.raise_for_status()  # Will raise an exception for other HTTP error codes.
            # Optional quiet output: print(f"Action '{action_path}' sent.")
        except requests.exceptions.RequestException as e:
            print(f"Error sending action '{action_path}': {e}")

    def get_state(self):
        """
        Retrieves the current game state relative to the agent's player.

        Calls the '/player/{player_id}/state' endpoint using a GET request to obtain the state.
        Pretty prints the JSON response.

        Returns:
            dict or None: The game state if successful; otherwise, None.
        """
        if not self.player_id:
            print("Error: No Player ID. Cannot get state.")
            return None
        try:
            url = f"{API_URL}/player/{self.player_id}/scan"  # Correct endpoint for relative state.
            state_data = response.json()
            print("-" * 20)
            print("Current Relative State:")
            # Pretty print the JSON state data.
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
        """
        Runs the agent's main loop.

        Initializes a small pygame window. Uses key events to send control actions to the server.
        SPACE sends a shoot action, arrow keys control movement and rotation, and ENTER polls for state.
        The loop continues until the window is closed or the player ID is lost.
        """
        pygame.init()
        screen = pygame.display.set_mode((300, 200))
        pygame.display.set_caption(f"Agent - Player {self.player_id}")
        clock = pygame.time.Clock()

        running = True
        while running and self.player_id:  # Loop ends if the window is closed or player_id becomes None.
            screen.fill((255, 255, 255))
            pygame.display.flip()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                if event.type == pygame.KEYDOWN:
                    # SPACE sends the 'shoot' action.
                    if event.key == pygame.K_SPACE:
                        self.send_action("shoot")
                    # ENTER key polls for the current game state.
                    elif event.key == pygame.K_RETURN:
                        response = requests.get(f"{API_URL}/player/{self.player_id}/scan")
                        print(f"Game-State: {response.json()}")
                    elif event.key == pygame.K_RSHIFT:
                        response = requests.post(f"{API_URL}/player/ready/{self.player_id}")
                        print(f"Player {self.player_id} is ready to play.")
                    elif event.key == pygame.K_LSHIFT:
                        response = requests.get(f"{API_URL}/player/{self.player_id}/game-state")
                        print(f"Game-State: {response.json()}")
                    elif event.key == pygame.K_LCTRL:
                        response = requests.get(f"{API_URL}/player/{self.player_id}/state")
                        print(f"Player-State: {response.json()}")
                    elif event.key == pygame.K_ESCAPE:
                        response = requests.post(f"{API_URL}/game/restart")
                    elif event.key == pygame.K_1:
                        response = requests.post(f"{API_URL}/disconnect/{self.player_id}")

            # Continuous action sending based on key hold status.
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

            clock.tick(30)  # Limits the loop to 30 frames per second.

        # When finished, disconnect from the server and quit pygame.
        self.disconnect()
        pygame.quit()


if __name__ == "__main__":
    agent = Agent()
    agent.run()
