import requests
import sys
import time
import math
import pygame
import random

API_URL = f"http://127.0.0.1:8000"

class Agent:
    def __init__(self):
        self.player_id = None
        self.connect()

    def connect(self):
        try:
            team_name = "Haakon"  # Oder ein anderer eindeutiger Name
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
            except requests.exceptions.RequestException as e:
                print(f"Error disconnecting from server: {e}")

    def send_action(self, action_path):
        if not self.player_id:
            return
        try:
            url = f"{API_URL}/player/{self.player_id}/{action_path}"
            requests.post(url)
        except requests.exceptions.RequestException as e:
            print(f"Error sending action '{action_path}': {e}")

    def get_scan(self):
        try:
            url = f"{API_URL}/player/{self.player_id}/scan"
            return requests.get(url).json()
        except Exception as e:
            print(f"Error getting scan: {e}")
            return {}

    def get_own_state(self):
        try:
            url = f"{API_URL}/player/{self.player_id}/state"
            return requests.get(url).json()
        except:
            return {}

    def angle_diff(self, angle1, angle2):
        """Returns the smallest difference between two angles."""
        diff = (angle2 - angle1 + math.pi) % (2 * math.pi) - math.pi
        return diff
    
    def control_rotation(self, angle_diff, angular_velocity):
        Kp = 2  # Proportional gain for rotation control
        Kd = 1.2  # Derivative gain for rotation control
        return -Kp * angle_diff - Kd * angular_velocity

    def run_autonomous(self):
        # Notify server that the player is ready
        pygame.init()
        clock = pygame.time.Clock()
        try:
            url = f"{API_URL}/player/ready/{self.player_id}"
            requests.post(url)
        except requests.exceptions.RequestException as e:
            print(f"Error sending ready signal: {e}")
        
        scan_cooldown = 0.52  # Cooldown for scan requests
        shoot_cooldown = 0.1  # Cooldown for shooting
        last_shoot_time = time.time()
        last_scan_time = time.time()
        
            
        running = True
        while running and self.player_id:
            scan, own_state = None, None
            # Can only call get_scan two times per second
            if time.time() - last_scan_time > scan_cooldown:
                last_scan_time = time.time()
                scan = self.get_scan()
                own_state = self.get_own_state()
            else:
                continue
            
            # Get the current scan and own state
            if not self.player_id:
                print("Player ID is not set. Exiting.")
                break
            
            if not scan or not own_state:
                continue
            
            my_angle = own_state.get("angle", 0) % math.pi * 2
            my_x, my_y = own_state.get("position", [0, 0])
            my_vx, my_vy = own_state.get("velocity", [0, 0])
            my_angular_velocity = own_state.get("angular_velocity", 0)
            
            if abs(my_angular_velocity) > 2:
                # If rotating too fast, slow down
                if abs(my_angular_velocity) > 3:
                    if my_angular_velocity > 0:
                        self.send_action("rotate_left")
                        self.send_action("rotate_left")
                    else:
                        self.send_action("rotate_right")
                        self.send_action("rotate_right")
                else:
                    if my_angular_velocity > 0:
                        self.send_action("rotate_left")
                    else:
                        self.send_action("rotate_right")
            
            my_speed = math.hypot(my_vx, my_vy)
            
            dot_product = my_vx * math.cos(my_angle) + my_vy * math.sin(my_angle)
            if my_speed > 50:
                # If moving too fast, slow down
                if dot_product > 0:
                    self.send_action("thrust_backward")
                elif dot_product < 0:
                    self.send_action("thrust_forward")
            elif my_speed < 5:
                # If moving too slow, speed up
                self.send_action("thrust_forward")
                self.send_action("thrust_forward")

            closest_enemy = None
            min_distance = float("inf")

            # --- Target closest enemy ---
            for obj in scan.get("nearby_objects", []):
                if obj["type"] == "other_player":
                    dist = obj["distance"]  # Use precomputed distance
                    if dist < min_distance:
                        min_distance = dist
                        closest_enemy = obj
                if obj["type"] == "border":
                    # Handle border detection
                    bx, by = obj["relative_position"]
                    angle_to_border = math.atan2(by, bx) # Adjust for game coordinate system
                    
                    distance_to_border = obj["distance"]
                    if distance_to_border < 50:
                        print(angle_to_border, distance_to_border)
                        if angle_to_border > 0:
                            self.send_action("rotate_left")
                            self.send_action("rotate_left")
                            self.send_action("rotate_left")
                        elif angle_to_border < 0:
                            self.send_action("rotate_right")
                            self.send_action("rotate_right")
                            self.send_action("rotate_right")
                        if abs(angle_to_border) > 2:
                            self.send_action("thrust_forward")
                            
                if obj["type"] == "obstacle":
                    ox, oy = obj["relative_position"]
                    obj_angle = math.atan2(ox, oy) - math.pi / 2  # Adjust for game coordinate system
                    dist = obj["distance"]  # Use precomputed distance
                    if dist < 60:  # Adjust as needed
                        if obj_angle > 0 and obj_angle < math.pi / 2:
                            self.send_action("rotate_right")
                            self.send_action("rotate_right")
                        elif obj_angle < 0 and obj_angle > -math.pi / 2:
                            self.send_action("rotate_left")
                            self.send_action("rotate_left")
                            
                        elif abs(obj_angle) > 1.5:
                            self.send_action("thrust_forward")
                            self.send_action("thrust_forward")
                

            if closest_enemy:
                # Use relative position to compute angle
                dx, dy = closest_enemy["relative_position"]
                target_angle = math.atan2(dy, dx)  # Adjust for game coordinate system
                abs_angle = abs(target_angle)
                
                if abs_angle < 0.2 and time.time() - last_shoot_time > shoot_cooldown:
                    last_shoot_time = time.time()
                    self.send_action("shoot")
                    
                # Tunable params    
                MIN_ANGLE_ERROR = 0.05  # Deadzone (stop rotating when error is small)
                MAX_ROTATION_STEPS = 5  # Max rotation steps per frame (avoid over-rotation)


                if abs_angle > MIN_ANGLE_ERROR:
                    
                    # Proportional control: More aggressive rotation when far from target
                    rotation_steps = min(MAX_ROTATION_STEPS, int(abs_angle * 1.5))  # Scale factor (tune this)
                    rotation_steps = max(1, rotation_steps)  # Ensure at least one step
                    
                    # Optional: Add braking if overshooting (predict future error)
                    if rotation_steps > 1 and abs_angle < 0.3:
                        rotation_steps = 1  # Slow down near target
                    
                    # Apply rotation
                    for _ in range(rotation_steps):
                        if target_angle > 0:
                            self.send_action("rotate_right")
                        else:
                            self.send_action("rotate_left")
                else:
                    # Aligned (deadzone), stop rotating
                    pass
                    
                    
            clock.tick(30)
        self.disconnect()
        pygame.quit()
if __name__ == "__main__":
    agent = Agent()
    agent.run_autonomous()
