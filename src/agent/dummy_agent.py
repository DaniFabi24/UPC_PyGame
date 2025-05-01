import sys
import os
import time
import requests
from ..settings import API_URL
import pygame

def client_loop():
    pygame.init() # Init pygame once
    screen = pygame.display.set_mode((300, 200))
    pygame.display.set_caption("Control Agent")
    clock = pygame.time.Clock() # Use clock for consistent timing

    running = True
    while running:
        screen.fill((255, 255, 255))
        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            # Handle single key presses for actions like shooting
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    try:
                        response = requests.post(f"{API_URL}/shoot")
                        response.raise_for_status()
                        print("Shoot command executed")
                    except requests.exceptions.RequestException as e:
                        print(f"Error sending shoot command: {e}")


        # Handle continuous key presses for movement/rotation
        keys = pygame.key.get_pressed()
        action_taken = False # Flag to prevent multiple actions per frame if needed
        if keys[pygame.K_UP]:
            response = requests.post(f"{API_URL}/thrust_forward")
            # response.raise_for_status() # Consider removing for performance if errors are rare
            print("Thrust forward executed")
            action_taken = True
        elif keys[pygame.K_DOWN]: # Use elif if only one action per frame is desired
            response = requests.post(f"{API_URL}/thrust_backward")
            # response.raise_for_status()
            print("Thrust backward executed")
            action_taken = True
        
        if keys[pygame.K_LEFT]: # Separate check for rotation
             response = requests.post(f"{API_URL}/rotate_left")
             # response.raise_for_status()
             print("Rotate left executed")
        elif keys[pygame.K_RIGHT]:
             response = requests.post(f"{API_URL}/rotate_right")
             # response.raise_for_status()
             print("Rotate right executed")

        clock.tick(30) # Limit loop speed slightly

    pygame.quit()

if __name__ == "__main__":
    client_loop()