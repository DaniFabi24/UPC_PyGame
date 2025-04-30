import sys
import os
import time
import requests
from ..settings import API_URL
import pygame

def client_loop():
    while True:
        time.sleep(1)
        pygame.init()
        screen = pygame.display.set_mode((300, 200))
        pygame.display.set_caption("Control Agent")

        running = True
        while running:
            screen.fill((255, 255, 255))  # Clear screen with white background

            pygame.display.flip()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

            # Handle key presses for continuous commands
            keys = pygame.key.get_pressed()
            if keys[pygame.K_UP]:
                response = requests.post(f"{API_URL}/thrust_forward")
                response.raise_for_status()
                print("Thrust forward executed")
                time.sleep(0.5)
            elif keys[pygame.K_DOWN]:
                response = requests.post(f"{API_URL}/thrust_backward")
                response.raise_for_status()
                print("Thrust backward executed")
                time.sleep(0.5)
            elif keys[pygame.K_LEFT]:
                response = requests.post(f"{API_URL}/rotate_left")
                response.raise_for_status()
                print("Rotate left executed")
                time.sleep(0.5)
            elif keys[pygame.K_RIGHT]:
                response = requests.post(f"{API_URL}/rotate_right")
                response.raise_for_status()
                print("Rotate right executed")
                time.sleep(0.5)

        pygame.quit()

if __name__ == "__main__":
    client_loop()
