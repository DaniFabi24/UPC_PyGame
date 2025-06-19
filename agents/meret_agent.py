import time
import math
import random
import threading
import requests
import numpy as np
import heapq  
import os
import sys

API_URL = "http://127.0.0.1:8000"
PLAYER_NAME = "dummy_meret"

class DummyMeretAgent:
    def __init__(self, player_id=None):
        """Initialize agent with optional player_id (will be set in connect() if None)"""
        self.connect() #ADDED BY COMPETITION ORGANIZERS
        # Connection and basic state
        self.player_id = player_id  # Can be None initially
        self.game_running = True
        self.error_count = 0
        self.player_name = DummyMeretAgent.__name__
        
        # Game state tracking
        self.game_state = None
        self.scan_data = None
        self.last_position = [0, 0]
        self.field_size = [800, 600]  # Default, will be updated from game state
        self.game_running = False
        
        # Thread-safe data storage
        self.scan_data = None
        self.state_data = None
        self.scan_lock = threading.Lock()
        self.state_lock = threading.Lock()
        
        # Timing controls
        self.last_scan_time = 0
        self.last_state_time = 0
        self.last_move_time = 0
        self.last_shoot_time = 0
        self.last_debug_time = 0
        self.last_forward_thrust = time.time()
        self.last_exploration_change = time.time()
        self.last_obstacle_report = 0
        self.obstacle_report_interval = 0.5  # How often to report obstacles (seconds)
        
        # Position tracking
        self.position_valid = False
        self.default_position = [400, 300]  # Middle of screen
        self.estimated_position = self.default_position.copy()
        self.last_received_position = None
        self.position_timeout = 2.0  # Time before considering position data stale
        self.last_position_update = 0
        
        # Environment parameters
        self.field_size = [800, 600]
        self.obstacle_memory = {}
        self.obstacle_memory_time = 5.0  # Remember obstacles for 5 seconds
        
        # Obstacle detection parameters
        self.front_clear_distance = 150
        self.critical_distance = 100
        self.early_warning_distance = 250
        self.front_angle_zone = 60  # Degrees (±60° in front)
        self.safety_margin = 50
        
        # Movement tracking
        self.rotation_count = 0
        self.last_position = [0, 0]
        self.stationary_time = 0
        self.last_stationary_check = time.time()
        
        # Motion control
        self.exploration_direction = "right"
        self.exploration_thrust_interval = 0.3
        self.rotation_intensity = 1.5
        self.last_turn_direction = None
        
        # Recovery and state tracking
        self.collision_counter = 0
        self.maneuver_in_progress = False
        self.maneuver_start = 0
        self.maneuver_timeout = 3.0
        
        # World representation - Occupancy Grid
        self.grid_cell_size = 20  # Grid cell size in pixels
        self.grid_width = int(self.field_size[0] / self.grid_cell_size)
        self.grid_height = int(self.field_size[1] / self.grid_cell_size)
        self.occupancy_grid = np.zeros((self.grid_width, self.grid_height))  # 0 = unknown
        self.visited_cells = set()
        
        # Status flags
        self.has_initial_data = False
        self.debug_mode = True
        self.verbose_debug = True  # Turn this on for more detailed messages
        
        # Stuck detection
        self.last_forced_escape = time.time()
        self.last_positions = []  # Position history for stuck detection
        self.forced_escape_interval = 5.0
        self.escape_count = 0
        
        # Wall avoidance
        self.boundary_contacts = [[0, 0], [0, 0], [0, 0], [0, 0]]  # [left, right, top, bottom]
        self.in_corner = False
        self.corner_detection_time = 0
        self.last_boundary_check = 0
        self.corner_escape_active = False
        self.last_corner_escape = 0
        self.wall_escape_cooldown = 2.0
        self.last_wall_escape = 0

        # Action tracking
        self.debug_counter = 0
        
        # Initialize obstacle memory
        self.detected_obstacles = []
        
        # Wall contact history
        self.wall_contact_history = []
        
        # Path planning attributes
        self.waypoints = []
        self.current_waypoint = None

        # Pathfinding variables
        self.waypoints = []
        self.current_waypoint = None
        self.path_needs_update = True  # Flag that path should be recalculated

    def connect(self, agent_name="Marta"):
        """Establish connection to the server"""
        try:
                # Teamnummer/Name hier setzen (z.B. "Team1" oder "Bot1")
                team_name = "Meret"  # Für dummy1.py

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

    def ready(self):
        """Send ready signal"""
        try:
            requests.post(f"{API_URL}/player/ready/{self.player_id}", timeout=3)
            print("Agent ready and waiting for game start")
            return True
        except Exception as e:
            print(f"Ready signal error: {e}")
            return False

    def world_to_grid(self, x, y=None):
        """Convert world coordinates to grid coordinates with bounds checking
        Accepts either separate x,y coordinates or a [x,y] position tuple"""
        # Handle both calling conventions (position tuple or separate coordinates)
        if y is None and isinstance(x, (list, tuple)) and len(x) >= 2:
            # Position was passed as a single tuple/list
            pos_x, pos_y = x[0], x[1]
        else:
            # Position was passed as separate x,y coordinates
            pos_x, pos_y = x, y
            
        # Get grid dimensions
        if not hasattr(self, 'occupancy_grid') or self.occupancy_grid is None:
            self.initialize_occupancy_grid()
            
        grid_height, grid_width = self.occupancy_grid.shape
        field_width, field_height = self.field_size
        
        # Scale coordinates
        grid_x = int((pos_x / field_width) * (grid_width - 1))
        grid_y = int((pos_y / field_height) * (grid_height - 1))
        
        # Bounds checking
        grid_x = max(0, min(grid_x, grid_width - 1))
        grid_y = max(0, min(grid_y, grid_height - 1))
        
        return grid_x, grid_y

    def grid_to_world(self, grid_pos):
        """Convert grid coordinates to world coordinates with bounds checking"""
        # Get grid dimensions
        if not hasattr(self, 'occupancy_grid') or self.occupancy_grid is None:
            self.initialize_occupancy_grid()
            
        grid_height, grid_width = self.occupancy_grid.shape
        field_width, field_height = self.field_size
        
        # Bounds checking
        x = max(0, min(grid_pos[0], grid_width - 1))
        y = max(0, min(grid_pos[1], grid_height - 1))
        
        # Scale coordinates
        world_x = (x / (grid_width - 1)) * field_width
        world_y = (y / (grid_height - 1)) * field_height
        
        return [world_x, world_y]

    def get_random_position(self):
        """Generate a random position within the game field bounds"""
        field_width, field_height = self.field_size
        # Keep away from edges
        margin = 50
        x = random.uniform(margin, field_width - margin)
        y = random.uniform(margin, field_height - margin)
        return [x, y]
    
    def initialize_occupancy_grid(self):
        """Initialize the occupancy grid with proper dimensions"""
        # Create a 30x30 grid (adjust size as needed)
        grid_width, grid_height = 30, 30
        # Initialize with 0.5 probability (unknown)
        self.occupancy_grid = np.ones((grid_height, grid_width)) * 0.5
        print(f"Initialized occupancy grid: {self.occupancy_grid.shape}")
    
    def update_occupancy_grid(self, scan_data, current_pos, current_heading):
        """Update our world model with sensor information"""
        if not scan_data or "nearby_objects" not in scan_data or not current_pos:
            return
            
        # Mark current position as free and visited
        grid_x, grid_y = self.world_to_grid(current_pos[0], current_pos[1])
        if 0 <= grid_x < self.grid_width and 0 <= grid_y < self.grid_height:
            self.occupancy_grid[grid_x, grid_y] = 0.0  # Definitely free
            self.visited_cells.add((grid_x, grid_y))
        
        # Process detected obstacles
        for obj in scan_data["nearby_objects"]:
            if obj.get("type") == "obstacle":
                # Calculate absolute position from relative
                rel_pos = obj.get("relative_position", [0, 0])
                abs_x = current_pos[0] + rel_pos[0]
                abs_y = current_pos[1] + rel_pos[1]
                
                # Store in obstacle memory
                grid_key = (int(abs_x / self.grid_cell_size), int(abs_y / self.grid_cell_size))
                self.obstacle_memory[grid_key] = time.time()
                
                # Update occupancy grid
                grid_x, grid_y = self.world_to_grid(abs_x, abs_y)
                if 0 <= grid_x < self.grid_width and 0 <= grid_y < self.grid_height:
                    # Update probability (increase confidence it's an obstacle)
                    self.occupancy_grid[grid_x, grid_y] = min(1.0, self.occupancy_grid[grid_x, grid_y] + 0.3)
                    
                    # Mark cells around the obstacle based on radius
                    radius = obj.get("radius", 20)
                    radius_cells = max(1, int(radius / self.grid_cell_size))
                    
                    # Use a circle algorithm for more accurate representation
                    for dx in range(-radius_cells, radius_cells+1):
                        for dy in range(-radius_cells, radius_cells+1):
                            # Check if the point is within the circle
                            if dx*dx + dy*dy <= radius_cells*radius_cells:
                                nx, ny = grid_x + dx, grid_y + dy
                                if 0 <= nx < self.grid_width and 0 <= ny < self.grid_height:
                                    # Higher probability in the center of the obstacle
                                    distance_from_center = math.sqrt(dx*dx + dy*dy)
                                    prob_increase = 0.3 * (1 - distance_from_center/radius_cells)
                                    self.occupancy_grid[nx, ny] = min(1.0, 
                                        max(self.occupancy_grid[nx, ny], 0) + prob_increase)
        
        # Mark free space between agent and obstacles using ray tracing
        for obj in scan_data["nearby_objects"]:
            if obj.get("type") == "obstacle":
                rel_pos = obj.get("relative_position", [0, 0])
                obstacle_dist = math.hypot(rel_pos[0], rel_pos[1])
                
                # Get points along the ray from agent to obstacle
                ray_steps = max(3, int(obstacle_dist / 20))
                for i in range(1, ray_steps):
                    # Points along ray before reaching the obstacle
                    ratio = (i / ray_steps) * 0.9  # Stop at 90% of distance to avoid marking the obstacle itself
                    ray_x = current_pos[0] + rel_pos[0] * ratio
                    ray_y = current_pos[1] + rel_pos[1] * ratio
                    
                    grid_x, grid_y = self.world_to_grid(ray_x, ray_y)
                    if 0 <= grid_x < self.grid_width and 0 <= grid_y < self.grid_height:
                        # Reduce probability (increase confidence it's free)
                        if self.occupancy_grid[grid_x, grid_y] != 1.0:  # Don't override confirmed obstacles
                            self.occupancy_grid[grid_x, grid_y] = max(-0.2, 
                                self.occupancy_grid[grid_x, grid_y] - 0.05)
    
    def detect_obstacle_gaps(self, scan_data, current_pos, current_heading):
        """Detect navigable gaps between obstacles"""
        if not scan_data or "nearby_objects" not in scan_data:
            return []
    
        obstacles = []
        for obj in scan_data["nearby_objects"]:
            if obj.get("type") == "obstacle" or obj.get("type") == "circular":
                rel_pos = obj.get("relative_position", [0, 0])
                distance = math.hypot(rel_pos[0], rel_pos[1])
                angle = math.atan2(rel_pos[1], rel_pos[0])
                radius = obj.get("radius", 20)
                # Calculate angular width based on distance and radius
                angular_width = 2 * math.asin(min(1.0, radius / max(1.0, distance)))
                
                obstacles.append({
                    "distance": distance,
                    "angle": angle,
                    "radius": radius,
                    "angular_width": angular_width
                })
    
        # Sort obstacles by angle for gap detection
        obstacles.sort(key=lambda x: x["angle"])
        
        # No gaps if fewer than 2 obstacles
        if len(obstacles) < 2:
            return []
    
        # Find gaps between obstacles
        gaps = []
        
        # Check pairs of adjacent obstacles
        for i in range(len(obstacles)):
            next_idx = (i + 1) % len(obstacles)
            
            # Calculate gap between current and next obstacle
            start_angle = obstacles[i]["angle"] + obstacles[i]["angular_width"]/2
            end_angle = obstacles[next_idx]["angle"] - obstacles[next_idx]["angular_width"]/2
            
            # Handle wraparound
            if end_angle < start_angle:
                end_angle += 2 * math.pi
                
            gap_width = end_angle - start_angle
            
            # Only consider sufficiently large gaps
            if gap_width > 0.3:  # Minimum 0.3 radians (approx 17 degrees)
                mid_angle = start_angle + gap_width/2
                mid_angle = mid_angle % (2 * math.pi)  # Normalize to [0, 2π]
                
                # Calculate gap quality (width * min distance)
                quality = gap_width * min(obstacles[i]["distance"], obstacles[next_idx]["distance"])
                
                gaps.append({
                    "angle": mid_angle,
                    "width": gap_width, 
                    "quality": quality
                })
    
        # Sort gaps by quality (higher is better)
        gaps.sort(key=lambda x: x["quality"], reverse=True)
        return gaps
    
    def navigate_through_gap(self, gap, current_heading):
        """Navigate through the best detected gap with stronger forward movement"""
        target_angle = gap["angle"]
        gap_width = gap["width"]
        
        # Calculate heading difference
        angle_diff = (target_angle - current_heading) % (2 * math.pi)
        if angle_diff > math.pi:
            angle_diff -= 2 * math.pi
        
        # Determine turning direction
        turn_direction = "right" if angle_diff > 0 else "left"
        
        # Calculate turn intensity based on angle difference - MORE PROPORTIONAL
        turn_intensity = min(3, max(1, int(abs(angle_diff) * 2)))  # Reduced multiplier
        
        print(f"🔍 Navigating through gap: width={math.degrees(gap_width):.1f}°, "
              f"turning {turn_direction}, intensity={turn_intensity}")
        
        # Execute the turn with appropriate intensity
        for _ in range(turn_intensity):
            self.safe_api_call(f"rotate_{turn_direction}")
            time.sleep(0.03)
        
        # STRONGER thrust forward through the gap
        for _ in range(3):  # Increased from 2
            self.safe_api_call("thrust_forward")
            time.sleep(0.04)
        
        return True
    
    def sensor_thread(self):
        """Thread for getting sensor data from server"""
        print("Sensor thread started")
        
        while self.game_running:
            try:
                # Get scan data
                resp = requests.get(f"{API_URL}/player/{self.player_id}/scan", timeout=0.5)
                if resp.status_code == 200:
                    scan_data = resp.json()
                    with self.scan_lock:
                        self.scan_data = scan_data
                
                # Get state data
                resp = requests.get(f"{API_URL}/player/{self.player_id}/state", timeout=0.5)
                if resp.status_code == 200:
                    state_data = resp.json()
                    with self.state_lock:
                        self.game_state = state_data
                        
                    # Store last position for movement calculations
                    if "position" in state_data:
                        self.last_position = state_data["position"]
                    
                    # Store field size if not already set
                    if "field_size" in state_data and not hasattr(self, "field_size"):
                        self.field_size = state_data["field_size"]
                    
            except Exception as e:
                print(f"Error in sensor thread: {e}")
            
            # Sleep to prevent overloading the server
            time.sleep(0.1)

    def check_game_status_thread(self):
        """Thread for checking game status"""
        print("Game status monitoring thread started")
        
        while self.game_running:
            try:
                # Check game status
                resp = requests.get(f"{API_URL}/game_status", timeout=1.0)
                if resp.status_code == 200:
                    status = resp.json()
                    game_state = status.get("state", "unknown")
                    
                    # Check if game has ended
                    if game_state == "ended":
                        print("Game has ended! Final status received.")
                        self.game_running = False
                        break
                        
            except Exception as e:
                print(f"Error checking game status: {e}")
            
            # Check less frequently
            time.sleep(2.0)

    def track_enemies(self, scan_data, current_time, current_pos):
        """Track enemy positions over time to enable motion prediction"""
        if not hasattr(self, 'known_enemies'):
            self.known_enemies = {}
            
        if not hasattr(self, 'valid_target_types'):
            self.valid_target_types = ["player", "enemy", "ship"]
            
        if not hasattr(self, 'invalid_target_types'):
            self.invalid_target_types = ["obstacle", "circular", "wall", "bullet", "border", "projectile"]
            
        for obj in scan_data["nearby_objects"]:
            # Get object type and convert to lowercase for comparison
            obj_type = obj.get("type", "unknown").lower()
            
            # Strict enemy identification
            is_enemy = False
            if obj_type in [t.lower() for t in self.valid_target_types]:
                is_enemy = True
            elif obj_type in [t.lower() for t in self.invalid_target_types]:
                is_enemy = False
            else:
                continue  # Skip unknown types
            
            # Process enemies
            if is_enemy:
                # Get position and calculate distance/angle
                rel_pos = obj.get("relative_position", [0, 0])
                abs_pos = [current_pos[0] + rel_pos[0], current_pos[1] + rel_pos[1]]
                dist = math.hypot(rel_pos[0], rel_pos[1])
                angle = math.atan2(rel_pos[1], rel_pos[0])
                
                # Generate ID or use object ID if available
                obj_id = obj.get("id", f"unknown-{dist:.1f}-{angle:.1f}")
                
                # Update existing enemy or create new entry
                if obj_id in self.known_enemies:
                    enemy = self.known_enemies[obj_id]
                    
                    # Calculate time since last observation
                    time_delta = current_time - enemy["last_seen"]
                    
                    # Calculate velocity if we have multiple observations
                    if enemy["history"] and time_delta > 0:
                        last_pos = enemy["history"][-1][0]
                        dx = abs_pos[0] - last_pos[0]
                        dy = abs_pos[1] - last_pos[1]
                        
                        # Velocity vector
                        velocity = [dx / time_delta, dy / time_delta]
                        speed = math.hypot(velocity[0], velocity[1])
                        
                        # Update enemy data
                        enemy["velocity"] = velocity
                        enemy["speed"] = speed
                        enemy["heading"] = math.atan2(velocity[1], velocity[0])
                    
                    # Update tracking data
                    enemy["position"] = abs_pos
                    enemy["relative_position"] = rel_pos
                    enemy["distance"] = dist
                    enemy["angle"] = angle
                    enemy["last_seen"] = current_time
                    
                    # Add to position history (limit to last 10 positions)
                    enemy["history"].append((abs_pos, current_time))
                    if len(enemy["history"]) > 10:
                        enemy["history"].pop(0)
                        
                else:
                    # New enemy detected
                    self.known_enemies[obj_id] = {
                        "type": obj_type,
                        "position": abs_pos,
                        "relative_position": rel_pos,
                        "distance": dist,
                        "angle": angle,
                        "first_seen": current_time,
                        "last_seen": current_time,
                        "history": [(abs_pos, current_time)],
                        "velocity": [0, 0],
                        "speed": 0,
                        "heading": 0,
                        "hit_probability": 0
                    }
                    print(f"👾 New enemy tracked: Type={obj_type}, Distance={dist:.1f}")

    def calculate_hit_probability(self, enemy_data, current_pos, current_heading, current_velocity):
        """Calculate probability of hitting enemy based on prediction"""
        # Initialize bullet speed if not already set
        if not hasattr(self, 'bullet_speed'):
            self.bullet_speed = 10.0
            
        # Extract enemy data
        enemy_pos = enemy_data["position"]
        enemy_vel = enemy_data["velocity"]
        enemy_dist = enemy_data["distance"]
        
        # For accurate prediction, we need good velocity estimates
        if enemy_data["speed"] < 0.1 and len(enemy_data["history"]) < 3:
            return 0.0, None  # Not enough data for prediction
            
        # Calculate time to intercept
        # Simple time estimate based on distance and bullet speed
        estimated_time = enemy_dist / self.bullet_speed
        
        # Predict enemy position at intercept time
        predicted_pos = [
            enemy_pos[0] + enemy_vel[0] * estimated_time,
            enemy_pos[1] + enemy_vel[1] * estimated_time
        ]
        
        # Calculate angle to predicted position
        dx = predicted_pos[0] - current_pos[0]
        dy = predicted_pos[1] - current_pos[1]
        intercept_angle = math.atan2(dy, dx)
        
        # Calculate angle difference (how much we need to turn)
        angle_diff = self.normalize_angle(intercept_angle - current_heading)
        
        # Calculate base probability based on various factors
        
        # 1. Distance factor: further = lower probability
        distance_factor = min(1.0, 200 / max(10, enemy_dist))
        
        # 2. Angle factor: larger angle difference = lower probability
        angle_factor = max(0, 1.0 - abs(angle_diff) / math.pi)
        
        # 3. Prediction uncertainty: faster enemy = lower probability
        certainty_factor = max(0.1, 1.0 - (enemy_data["speed"] * estimated_time / 200))
        
        # 4. Enemy direction change factor
        direction_change_factor = 1.0
        if len(enemy_data["history"]) >= 3:
            # Calculate how much enemy has changed direction recently
            recent_history = enemy_data["history"][-3:]
            angles = []
            
            for i in range(1, len(recent_history)):
                prev_pos = recent_history[i-1][0]
                curr_pos = recent_history[i][0]
                segment_angle = math.atan2(curr_pos[1] - prev_pos[1], 
                                        curr_pos[0] - prev_pos[0])
                angles.append(segment_angle)
            
            # Calculate max angle change
            if len(angles) > 1:
                max_angle_diff = max(abs(self.normalize_angle(angles[i] - angles[i-1])) 
                                for i in range(1, len(angles)))
                
                # Higher angle change = lower certainty
                direction_change_factor = max(0.3, 1.0 - max_angle_diff / math.pi)
        
        # Calculate final hit probability
        hit_probability = distance_factor * angle_factor * certainty_factor * direction_change_factor
        
        # Create intercept data tuple
        intercept_data = (predicted_pos, estimated_time, intercept_angle)
        
        return hit_probability, intercept_data

    def normalize_angle(self, angle):
        """Normalize angle to range [-pi, pi]"""
        while angle > math.pi:
            angle -= 2 * math.pi
        while angle < -math.pi:
            angle += 2 * math.pi
        return angle

    def combat_thread(self):
        """Advanced combat thread with predictive targeting and hit probability estimation"""
        print("Combat thread started with predictive targeting system")
        
        # Initialize combat variables
        self.last_shot_time = 0
        self.shot_cooldown = 1.0  # 1 second between shots
        self.known_enemies = {}   # Track enemies by ID and history
        self.bullet_speed = 10.0  # Estimated bullet speed units per frame
        self.hit_probability_threshold = 0.5  # Only shoot if hit probability > 50%

        # Define valid enemy types
        self.valid_target_types = ["player", "enemy", "ship"]
        self.invalid_target_types = ["obstacle", "circular", "wall", "bullet", "border", "projectile"]
        
        # Initialize PID controller for aiming
        if not hasattr(self, 'aim_pid'):
            self.aim_pid = {
                "Kp": 1.5,  # Proportional gain
                "Ki": 0.1,  # Integral gain
                "Kd": 0.3,  # Derivative gain
                "previous_error": 0,
                "integral": 0,
                "last_time": time.time()
            }
        
        # Initialize shots fired counter
        self.shots_fired = 0
        
        while self.game_running:
            try:
                # Get current state and scan data
                with self.state_lock:
                    current_state = self.game_state.copy() if self.game_state else None
                    
                with self.scan_lock:
                    current_scan = self.scan_data.copy() if self.scan_data else None
                
                # Skip if we don't have both state and scan
                if not current_state or not current_scan:
                    time.sleep(0.1)
                    continue
                
                # Get our position, heading and velocity
                current_pos = current_state.get("position", [0, 0])
                current_heading = current_state.get("angle", 0)
                current_velocity = current_state.get("velocity", [0, 0])
                current_speed = math.hypot(current_velocity[0], current_velocity[1])
                current_time = time.time()
                    
                # Process detected enemies and update tracking
                if "nearby_objects" in current_scan:
                    self.track_enemies(current_scan, current_time, current_pos)
                    
                    # Find best target with highest hit probability
                    best_target = None
                    highest_probability = 0
                    
                    for enemy_id, enemy_data in self.known_enemies.items():
                        # Skip enemies that haven't been seen enough times for prediction
                        if len(enemy_data["history"]) < 3:
                            continue
                            
                        # Calculate hit probability
                        hit_prob, intercept_data = self.calculate_hit_probability(
                            enemy_data, 
                            current_pos, 
                            current_heading,
                            current_velocity
                        )
                        
                        # Update enemy data with hit probability
                        enemy_data["hit_probability"] = hit_prob
                        
                        # Keep track of best target
                        if hit_prob > highest_probability:
                            highest_probability = hit_prob
                            best_target = (enemy_id, enemy_data, intercept_data)
                    
                    # Only shoot if we have a good target and enough time has passed
                    if (best_target and 
                        highest_probability > self.hit_probability_threshold and
                        current_time - self.last_shot_time > self.shot_cooldown):
                        
                        enemy_id, enemy_data, intercept_data = best_target
                        
                        # Get intercept details
                        intercept_pos, intercept_time, intercept_angle = intercept_data
                        
                        # Log detailed targeting information
                        print(f"🎯 TARGET LOCK: ID={enemy_id[:8]} Type={enemy_data['type']}")
                        print(f"    Distance={enemy_data['distance']:.1f}, Speed={enemy_data['speed']:.1f}")
                        print(f"    Hit probability: {highest_probability:.1%}")
                        print(f"    Intercept in: {intercept_time:.2f}s")
                        
                        # Fire!
                        self.safe_api_call("shoot")
                        self.last_shot_time = current_time
                        self.shots_fired += 1
                        print(f"📊 Combat stats: {self.shots_fired} shots fired")
                
                # Clean up old enemy records
                self.known_enemies = {k:v for k,v in self.known_enemies.items() 
                                    if current_time - v["last_seen"] < 5.0}  # 5 seconds max age
                            
            except Exception as e:
                print(f"Error in combat thread: {e}")
                import traceback
                traceback.print_exc()
            
            # Adaptive sleep based on enemy presence
            if self.known_enemies:
                time.sleep(0.1)  # Faster updates when enemies present
            else:
                time.sleep(0.2)  # Slower updates when no enemies
    
    def initialize_pid_controllers(self):
        """Initialize PID controllers with more aggressive gains"""
        # Heading PID controller parameters - MUCH more responsive
        self.heading_pid = {
            "Kp": 2.5,  # Increased from 1.2
            "Ki": 0.1,  # Increased from 0.05
            "Kd": 0.8,  # Increased from 0.3
            "previous_error": 0,
            "integral": 0,
            "last_time": time.time()
        }
        
        # Thrust PID controller parameters - MUCH more aggressive
        self.thrust_pid = {
            "Kp": 3.0,  # Increased from 1.0
            "Ki": 0.2,  # Increased from 0.02
            "Kd": 0.5,  # Increased from 0.1
            "previous_error": 0,
            "previous_error": 0,
            "integral": 0,
            "last_time": time.time()
        }
        
        # Target state variables
        self.target_heading = None
        self.target_distance = None
        self.current_waypoint = None
        self.waypoints = []

    def pid_heading_control(self, current_heading, target_heading):
        """PID controller for smooth heading/rotation control"""
        # Normalize target and current heading difference to [-π, π]
        error = (target_heading - current_heading) % (2 * math.pi)
        if error > math.pi:
            error -= 2 * math.pi
        
        # Calculate time since last update
        current_time = time.time()
        dt = current_time - self.heading_pid["last_time"]
        if dt <= 0: dt = 0.01  # Prevent division by zero
        
        # Calculate integral and derivative terms
        self.heading_pid["integral"] += error * dt
        derivative = (error - self.heading_pid["previous_error"]) / dt
        
        # Anti-windup: limit integral term
        max_integral = 2.0
        self.heading_pid["integral"] = max(-max_integral, min(self.heading_pid["integral"], max_integral))
        
        # Calculate PID output
        output = (self.heading_pid["Kp"] * error + 
                self.heading_pid["Ki"] * self.heading_pid["integral"] + 
                self.heading_pid["Kd"] * derivative)
        
        # Update state variables
        self.heading_pid["previous_error"] = error
        self.heading_pid["last_time"] = current_time
        
        # Determine rotation action based on PID output
        if abs(error) < 0.05:  # Small deadband to avoid oscillation
            return None
        elif output > 0:
            return "rotate_right"
        else:
            return "rotate_left"

    def pid_thrust_control(self, current_dist, target_dist):
        """PID controller for smooth thrust/velocity control"""
        # Error is positive if we need to move forward, negative if we need to slow down
        error = target_dist - current_dist
        
        # Calculate time since last update
        current_time = time.time()
        dt = current_time - self.thrust_pid["last_time"]
        if dt <= 0: dt = 0.01  # Prevent division by zero
        
        # Calculate integral and derivative terms
        self.thrust_pid["integral"] += error * dt
        derivative = (error - self.thrust_pid["previous_error"]) / dt
        
        # Anti-windup: limit integral term
        max_integral = 2.0
        self.thrust_pid["integral"] = max(-max_integral, min(self.thrust_pid["integral"], max_integral))
        
        # Calculate PID output
        output = (self.thrust_pid["Kp"] * error + 
                self.thrust_pid["Ki"] * self.thrust_pid["integral"] + 
                self.thrust_pid["Kd"] * derivative)
        
        # Update state variables
        self.thrust_pid["previous_error"] = error
        self.thrust_pid["last_time"] = current_time
        
        # Determine thrust action based on PID output
        if abs(error) < 5:  # Small deadband to avoid oscillation
            return None
        elif output > 0:
            return "thrust_forward"
        else:
            return "thrust_backward"
    
    def astar_path_planning(self, start, goal):
        """A* path planning algorithm with improved robustness"""
        if not hasattr(self, 'occupancy_grid') or self.occupancy_grid is None:
            self.initialize_occupancy_grid()
            
        # Convert world coordinates to grid
        start_grid = self.world_to_grid(start)
        goal_grid = self.world_to_grid(goal)
        
        print(f"Planning path from {start_grid} to {goal_grid} in grid coordinates")
        
        # A* algorithm
        open_set = []
        closed_set = set()
        came_from = {}
        
        # Cost from start to current
        g_score = {start_grid: 0}
        # Estimated cost from start to goal through current
        f_score = {start_grid: self.heuristic(start_grid, goal_grid)}
        
        heapq.heappush(open_set, (f_score[start_grid], start_grid))
        
        grid_height, grid_width = self.occupancy_grid.shape
        
        # Directions: up, right, down, left, and diagonals
        directions = [(0, 1), (1, 0), (0, -1), (-1, 0),
                    (1, 1), (1, -1), (-1, 1), (-1, -1)]
        
        max_iterations = 1000  # Limit to prevent infinite loops
        iterations = 0
        
        while open_set and iterations < max_iterations:
            iterations += 1
            _, current = heapq.heappop(open_set)
            
            if current == goal_grid:
                # Path found
                return self.reconstruct_path(came_from, current)
                
            closed_set.add(current)
            
            for dx, dy in directions:
                neighbor = (current[0] + dx, current[1] + dy)
                
                # Check if valid cell
                if (neighbor[0] < 0 or neighbor[0] >= grid_width or
                    neighbor[1] < 0 or neighbor[1] >= grid_height):
                    continue
                    
                # Check if obstacle
                try:
                    if self.occupancy_grid[neighbor[1], neighbor[0]] > 0.7:  # Likely obstacle
                        continue
                except IndexError:
                    continue
                    
                if neighbor in closed_set:
                    continue
                    
                # Cost for diagonal moves is higher
                move_cost = 1.4 if dx != 0 and dy != 0 else 1.0
                    
                tentative_g_score = g_score.get(current, float('inf')) + move_cost
                
                if (neighbor not in [i[1] for i in open_set] or 
                    tentative_g_score < g_score.get(neighbor, float('inf'))):
                    
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g_score
                    f_score[neighbor] = g_score[neighbor] + self.heuristic(neighbor, goal_grid)
                    
                    heapq.heappush(open_set, (f_score[neighbor], neighbor))
        
        print("⚠️ A* path planning failed to find path")
        return []  # No path found

    def heuristic(self, a, b):
        """Euclidean distance heuristic"""
        return math.sqrt((a[0] - b[0])**2 + (a[1] - b[1])**2)

    def plan_and_follow_path(self):
        """Use A* to plan path and follow it using PID controllers"""
        # Only plan if we need to
        if not self.waypoints or len(self.waypoints) < 2:
            # Get a new exploration target
            current_pos = self.game_state.get("position", [0, 0]) if self.game_state else [0, 0]
            target_pos = self.get_exploration_target()
            print(f"🗺️ Planning path to new target: {target_pos}")
            
            # Plan path using A*
            self.waypoints = self.astar_path_planning(current_pos, target_pos)
            if not self.waypoints:
                print("⚠️ A* could not find a path! Falling back to reactive navigation")
                return False
            
            print(f"📍 Path planned with {len(self.waypoints)} waypoints")
        
        # Follow the path
        if not self.waypoints:
            return False
            
        # Get current position and next waypoint
        current_pos = self.game_state.get("position", [0, 0]) if self.game_state else [0, 0]
        current_heading = self.game_state.get("angle", 0) if self.game_state else 0
        
        # If no current waypoint selected, take the first one
        if not self.current_waypoint and self.waypoints:
            self.current_waypoint = self.waypoints[0]
            
        # Check if we've reached the current waypoint
        dist_to_waypoint = math.hypot(current_pos[0] - self.current_waypoint[0], 
                                    current_pos[1] - self.current_waypoint[1])
        
        if dist_to_waypoint < 25:  # Waypoint reached threshold
            # Remove this waypoint
            self.waypoints.pop(0)
            # Get next waypoint if available
            if self.waypoints:
                self.current_waypoint = self.waypoints[0]
                print(f"✅ Waypoint reached, moving to next: {self.current_waypoint}")
            else:
                print("🏁 Final waypoint reached!")
                return False
        
        # Calculate heading to waypoint
        dx = self.current_waypoint[0] - current_pos[0]
        dy = self.current_waypoint[1] - current_pos[1]
        target_heading = math.atan2(dy, dx)
        
        # Use PID controller for heading
        action = self.pid_heading_control(current_heading, target_heading)
        if action:
            self.safe_api_call(action)
        
        # Always apply forward thrust when following path
        self.safe_api_call("thrust_forward")
        
        return True

    def reconstruct_path(self, came_from, current):
        """Reconstruct path from A* result"""
        path = [current]
        while current in came_from:
            current = came_from[current]
            path.append(current)
        
        # Convert grid coordinates to world coordinates
        world_path = []
        for grid_pos in reversed(path):
            world_x, world_y = self.grid_to_world(grid_pos[0], grid_pos[1])
            world_path.append([world_x, world_y])
        
        return world_path

    def get_exploration_target(self):
        """Get a target point for exploration with proper bounds checking"""
        if not hasattr(self, 'occupancy_grid') or self.occupancy_grid is None:
            # Initialize occupancy grid if it doesn't exist
            self.initialize_occupancy_grid()
            return self.get_random_position()
            
        # Get grid dimensions
        grid_height, grid_width = self.occupancy_grid.shape
        
        # Get current position
        current_pos = self.game_state.get("position", [0, 0]) if self.game_state else [0, 0]
        current_grid_x, current_grid_y = self.world_to_grid(current_pos)
        
        # Try to find unexplored areas (max 20 attempts)
        for _ in range(20):
            # Generate random candidate position in grid coordinates
            # Use safer bounds to avoid edge cases
            x = random.randint(2, grid_width - 3)
            y = random.randint(2, grid_height - 3)
            
            # Ensure indices are in bounds
            x = max(0, min(x, grid_width - 1))
            y = max(0, min(y, grid_height - 1))
            
            try:
                # Check if this cell is unexplored and not an obstacle
                if 0.4 <= self.occupancy_grid[y, x] <= 0.6:  # Unexplored area
                    # Convert back to world coordinates
                    return self.grid_to_world((x, y))
            except IndexError:
                print(f"⚠️ Index error in occupancy grid access: ({x}, {y})")
                continue
        
        # If we can't find unexplored areas, just get a random position
        return self.get_random_position()
        
    def detect_and_respond_to_collision(self, current_state):
        """Enhanced collision detection with velocity tracking"""
        if not current_state:
            return False
                
        # Track collision counter from game state
        current_collisions = current_state.get("collision_counter", 0)
        if not hasattr(self, 'collision_counter'):
            self.collision_counter = current_collisions
            
        # Get velocity for impact assessment
        velocity = current_state.get("velocity", [0, 0])
        speed = math.hypot(velocity[0], velocity[1])
            
        # Check if collision counter increased
        if current_collisions > self.collision_counter:
            impact_type = "HIGH IMPACT" if speed > 5 else "Low Impact"
            print(f"🚨 COLLISION DETECTED! {impact_type} - Counter: {self.collision_counter} → {current_collisions}")
            self.collision_counter = current_collisions
            
            # Display penalty information
            if "collision_penalty" in current_state:
                print(f"🚨 COLLISION PENALTY: {current_state['collision_penalty']}")
            if "score" in current_state:
                print(f"CURRENT SCORE: {current_state['score']}")
            
            # Execute collision recovery
            print("Executing collision recovery sequence")
            
            # 1. Brake to stop momentum
            self.safe_api_call("thrust_backward")
            self.safe_api_call("thrust_backward")
            time.sleep(0.1)
            
            # 2. Choose a significant rotation (90-180 degrees)
            rotation_amount = random.randint(4, 8)
            turn_direction = "left" if random.random() < 0.5 else "right"
            
            print(f"Rotating {turn_direction} ({rotation_amount} steps)")
            for _ in range(rotation_amount):
                self.safe_api_call(f"rotate_{turn_direction}")
                time.sleep(0.05)
                    
            # 3. Move forward
            for _ in range(3):
                self.safe_api_call("thrust_forward")
                time.sleep(0.05)
                
            return True
            
        # Also detect collisions by tracking sudden velocity changes
        if hasattr(self, 'last_velocity'):
            last_vel = self.last_velocity
            vel_change = math.hypot(velocity[0] - last_vel[0], velocity[1] - last_vel[1])
            
            # Large sudden velocity change might be undetected collision
            if vel_change > 10 and speed < 2:
                print(f"⚠️ Possible undetected collision! Velocity change: {vel_change:.1f}")
                self.perform_aggressive_escape()
                return True
                
        # Store velocity for next comparison
        self.last_velocity = velocity.copy() if velocity else [0, 0]
            
        return False

    def check_for_borders_and_walls(self, scan_data, current_pos):
        """Enhanced detection for BORDERS and walls with better distance thresholds"""
        if not scan_data or "nearby_objects" not in scan_data:
            return False, None
            
        # Add cooldown to prevent repeated wall escapes
        current_time = time.time()
        if hasattr(self, 'last_wall_escape_time') and current_time - self.last_wall_escape_time < 3.0:
            return False, None
            
        # Track borders by angle
        borders = []
        closest_border_dist = float('inf')
        closest_border_angle = None
        
        for obj in scan_data["nearby_objects"]:
            if obj.get("type") in ["BORDER", "border", "wall", "boundary"]:
                rel_pos = obj.get("relative_position", [0, 0])
                dist = math.hypot(rel_pos[0], rel_pos[1])
                angle = math.atan2(rel_pos[1], rel_pos[0])
                
                # Debug output to understand wall distances
                if dist < 150:
                    print(f"DEBUG: Found {obj.get('type')} at distance {dist:.1f}, angle {angle*180/math.pi:.1f}°")
                    
                borders.append((dist, angle, obj.get('type')))
                
                # Track closest border
                if dist < closest_border_dist:
                    closest_border_dist = dist
                    closest_border_angle = angle
        
        # ONLY detect borders that are VERY CLOSE
        # Much more conservative threshold (35 instead of 70)
        wall_detection_threshold = 45
        
        # If we have borders and any are close
        close_borders = [b for b in borders if b[0] < wall_detection_threshold]
        if close_borders:
            closest = min(close_borders, key=lambda b: b[0])
            print(f"🧱 CLOSE BORDER detected! Type: {closest[2]}, Distance: {closest[0]:.1f}, Angle: {closest[1]*180/math.pi:.1f}°")
            
            # Determine wall type based on angle
            wall_type = None
            if -math.pi/4 <= closest[1] <= math.pi/4:
                wall_type = "right"
            elif math.pi/4 <= closest[1] <= 3*math.pi/4:
                wall_type = "bottom" 
            elif -3*math.pi/4 <= closest[1] <= -math.pi/4:
                wall_type = "top"
            else:
                wall_type = "left"
                
            # Set last escape time
            self.last_wall_escape_time = current_time
            return True, wall_type
        
        # Position-based detection (only as fallback) - MUCH more conservative
        field_width, field_height = self.field_size
        x, y = current_pos
        wall_margin = 33  # Significantly reduced from 60
        
        if x < wall_margin:
            print(f"🧱 Position-based LEFT wall detection: x={x:.1f} < {wall_margin}")
            self.last_wall_escape_time = current_time
            return True, "left"
        elif x > field_width - wall_margin:
            print(f"🧱 Position-based RIGHT wall detection: x={x:.1f} > {field_width - wall_margin}")
            self.last_wall_escape_time = current_time
            return True, "right"
        elif y < wall_margin:
            print(f"🧱 Position-based TOP wall detection: y={y:.1f} < {wall_margin}")
            self.last_wall_escape_time = current_time
            return True, "top"
        elif y > field_height - wall_margin:
            print(f"🧱 Position-based BOTTOM wall detection: y={y:.1f} > {field_height - wall_margin}")
            self.last_wall_escape_time = current_time
            return True, "bottom"
        return False, None

    def detect_corner_trap(self, scan_data):
        """Detect if agent is trapped in a corner with conservative thresholds"""
        if not scan_data or "nearby_objects" not in scan_data:
            return False
        
        # Add cooldown to prevent repeated corner escapes
        current_time = time.time()
        if hasattr(self, 'last_corner_escape_time') and current_time - self.last_corner_escape_time < 4.0:
            return False
        
        # Count close borders in different directions
        borders = []
        
        for obj in scan_data["nearby_objects"]:
            if obj.get("type") in ["BORDER", "border", "wall", "boundary"]:
                rel_pos = obj.get("relative_position", [0, 0])
                dist = math.hypot(rel_pos[0], rel_pos[1])
                angle = math.atan2(rel_pos[1], rel_pos[0])
                
                # Much more conservative - only consider VERY close borders
                if dist < 40:
                    borders.append((dist, angle))
        
        # Only consider it a corner if we have multiple CLOSE borders in different directions
        if len(borders) >= 2:
            # Check if borders are in significantly different directions
            for i in range(len(borders)):
                for j in range(i+1, len(borders)):
                    angle_diff = abs(borders[i][1] - borders[j][1])
                    # Normalize angle difference to [0, π]
                    if angle_diff > math.pi:
                        angle_diff = 2*math.pi - angle_diff
                        
                    # If angles differ by more than 60 degrees (more conservative)
                    if angle_diff > math.pi/3:
                        print("🚨 CORNER DETECTED! Multiple borders at distances: " + 
                            ", ".join([f"{b[0]:.1f}" for b in borders]))
                        self.last_corner_escape_time = current_time
                        return True
        
        return False
        
    def print_debug_info(self, state, scan):
        """Print debug information about agent state"""
        print("\n===== ENVIRONMENT DEBUG =====")
        
        # Print scan data
        if scan and "nearby_objects" in scan:
            obstacles = [obj for obj in scan["nearby_objects"] 
                        if obj.get("type", "").lower() in ["obstacle", "circular"]]
            if obstacles:
                print(f"OBSTACLE ANALYSIS: {len(obstacles)} obstacles detected")
                for i, obj in enumerate(obstacles):
                    rel_pos = obj.get("relative_position", [0, 0])
                    dist = math.hypot(rel_pos[0], rel_pos[1])
                    angle = math.atan2(rel_pos[1], rel_pos[0]) * 180 / math.pi
                    print(f"  OBSTACLE #{i}: dist={dist:.1f}, angle={angle:.1f}°, type={obj.get('type', 'unknown')}")
        
        # Print position
        if state and "position" in state:
            print(f"POSITION: {state['position']}")
        
        # Add score and penalty information
        if state and "score" in state:
            print(f"SCORE: {state['score']}")
        
        if state and "collision_penalty" in state:
            print(f"🚨 COLLISION PENALTY: {state['collision_penalty']}")
        
        print("=============================\n")

    def check_for_immediate_obstacles(self, scan_data):
        """Check for obstacles that require immediate attention with improved distance thresholds"""
        if not scan_data or "nearby_objects" not in scan_data:
            return False, None
            
        closest_obstacle = None
        min_dist = float('inf')
        
        for obj in scan_data["nearby_objects"]:
            # Properly check for obstacles using lowercase comparisons
            obj_type = obj.get("type", "").lower()
            
            # Check for any type of obstacle (including circular objects)
            if obj_type in ["obstacle", "circular"]:
                rel_pos = obj.get("relative_position", [0, 0])
                dist = math.hypot(rel_pos[0], rel_pos[1])
                angle = math.atan2(rel_pos[1], rel_pos[0])
                
                # Focus on obstacles in wider forward arc (120 degrees)
                if abs(angle) < math.pi/1.5:
                    # Apply front weighting - obstacles directly ahead are more important
                    front_weight = 1.0 if abs(angle) > math.pi/4 else 0.7
                    weighted_dist = dist * front_weight
                    
                    if weighted_dist < min_dist:
                        min_dist = weighted_dist
                        closest_obstacle = (dist, angle, obj)
        
        # More sensitive detection threshold - start braking even further away
        obstacle_detection_threshold = 100  # Increased from 80
        
        if closest_obstacle and closest_obstacle[0] < obstacle_detection_threshold:
            return True, closest_obstacle
        
        return False, None

    def handle_obstacle_avoidance(self, obstacle_data):
        """Enhanced obstacle avoidance with braking response"""
        if not obstacle_data or not isinstance(obstacle_data, tuple) or len(obstacle_data) < 3:
            print("⚠️ Invalid obstacle data provided to avoidance handler")
            return False
            
        dist, angle, obj = obstacle_data
        
        # Log obstacle details
        print(f"🚧 AVOIDING OBSTACLE: Distance={dist:.1f}, Type={obj.get('type', 'unknown')}")
        
        # Determine braking intensity based on distance
        braking_intensity = 0
        if dist < 90:  # Start braking when somewhat close
            braking_intensity = 2  # Light braking
        if dist < 70:
            braking_intensity = 3  # Medium braking
        if dist < 50:
            braking_intensity = 5  # Heavy braking
        
        # Apply proportional braking
        if braking_intensity > 0:
            print(f"🛑 Applying braking thrust (intensity {braking_intensity}) before avoidance maneuver")
            for _ in range(braking_intensity):
                self.safe_api_call("thrust_backward")
                time.sleep(0.03)
        
        # Determine avoidance strategy based on distance and angle
        turn_dir = "left" if angle > 0 else "right"
        
        # Very close obstacles require stronger response
        if dist < 50:
            print("Emergency avoidance - obstacle very close!")
            for _ in range(3):
                self.safe_api_call("thrust_backward")
                time.sleep(0.04)
        
        # Proportional turn based on distance - closer means sharper turn
        turn_intensity = min(6, max(3, int(15 / (dist/10))))
        print(f"Turning {turn_dir} with intensity {turn_intensity}")
        
        # Execute the turn
        for _ in range(turn_intensity):
            self.safe_api_call(f"rotate_{turn_dir}")
            time.sleep(0.03)
            
        # If obstacle was not too close, accelerate
        # Only accelerate if we're not too close after turning
        if dist > 40:
            # Forward thrust after turning away
            for _ in range(3):
                self.safe_api_call("thrust_forward")
                time.sleep(0.04)
        
        return True

    def perform_aggressive_escape(self):
        """Execute a more powerful escape maneuver with continuous obstacle checking"""
        print("🚨🚨 EXECUTING AGGRESSIVE WALL ESCAPE MANEUVER")
        
        # First check if there are any obstacles in our path before maneuvering
        with self.scan_lock:
            current_scan = self.scan_data.copy() if self.scan_data else None
        
        if current_scan and self.check_for_immediate_obstacles(current_scan):
            print("⚠️ Obstacles detected during escape planning - handling obstacles first!")
            return self.handle_obstacle_avoidance(current_scan)
        
        # Start escape sequence - but check for obstacles after each step
        escape_dir = "left" if random.random() < 0.5 else "right"
        
        # Very strong turn (at least 90-120 degrees)
        for i in range(random.randint(6, 10)):
            # Check for obstacles after every few rotations
            if i % 3 == 0:
                with self.scan_lock:
                    current_scan = self.scan_data.copy() if self.scan_data else None
                if current_scan and self.check_for_immediate_obstacles(current_scan):
                    print("⚠️ Obstacles detected during escape rotation - interrupting!")
                    return self.handle_obstacle_avoidance(current_scan)
            
            self.safe_api_call(f"rotate_{escape_dir}")
            time.sleep(0.05)
        
        # Strong extended thrust with obstacle checking
        for i in range(10):
            # Check for obstacles more frequently during thrust
            if i % 2 == 0:
                with self.scan_lock:
                    current_scan = self.scan_data.copy() if self.scan_data else None
                if current_scan and self.check_for_immediate_obstacles(current_scan):
                    print("⚠️ Obstacles detected during escape thrust - emergency stop!")
                    return self.handle_obstacle_avoidance(current_scan)
            
            self.safe_api_call("thrust_forward")
            time.sleep(0.05)
        
        # Record successful escape attempt
        if not hasattr(self, 'escape_count'):
            self.escape_count = 0
        self.escape_count += 1
        print(f"🚀 Escape maneuver #{self.escape_count} executed with obstacle vigilance")
        return True

    def execute_wall_escape(self, wall_type):
        """Execute a wall escape maneuver based on wall type"""
        print(f"🔄 EXECUTING AGGRESSIVE WALL ESCAPE FROM {wall_type}")
        
        print("Phase 1: Creating space with stronger reverse")
        # First back up from wall
        for _ in range(5):
            self.safe_api_call("thrust_backward")
            time.sleep(0.05)
            
        # Determine turn direction based on wall
        if wall_type == "left":
            turn_dir = "right"
        elif wall_type == "right":
            turn_dir = "left"
        elif wall_type == "top":
            turn_dir = "right"  # Arbitrary choice for top wall
        else:  # bottom
            turn_dir = "left"   # Arbitrary choice for bottom wall
        
        print(f"Phase 2: Much larger rotation {turn_dir} to escape")
        # Make a significant turn (90 degrees minimum)
        for _ in range(6):
            self.safe_api_call(f"rotate_{turn_dir}")
            time.sleep(0.05)
            
        print("Phase 3: Stronger acceleration away from wall")
        # Strong acceleration away
        for _ in range(6):
            self.safe_api_call("thrust_forward")
            time.sleep(0.05)
            
        return True

    def execute_boundary_corner_escape(self):
        """Execute escape from corner by backing up and turning 180 degrees"""
        print("🚨 EXECUTING CORNER ESCAPE PROCEDURE")
        self.last_corner_escape = time.time()
        
        # First back up significantly
        print("Phase 1: Backing away from corner")
        for _ in range(8):
            self.safe_api_call("thrust_backward") 
            time.sleep(0.05)
        
        # Rotate ~180 degrees
        print("Phase 2: Rotating 180°") 
        turn_dir = "left" if random.random() < 0.5 else "right"
        for _ in range(12):  # ~180 degrees
            self.safe_api_call(f"rotate_{turn_dir}")
            time.sleep(0.05)
        
        # Move forward away from corner
        print("Phase 3: Accelerating away from corner")
        for _ in range(10):
            self.safe_api_call("thrust_forward")
            time.sleep(0.05)
            
        return True

    def execute_super_escape(self):
        """Execute a super aggressive escape for when stuck in patterns"""
        print("🔥 EXECUTING SUPER AGGRESSIVE ESCAPE SEQUENCE")
        
        # First, strong backward thrust in pulses
        print("Phase 1: Strong backward thrust")
        for _ in range(3):
            for _ in range(5):
                self.safe_api_call("thrust_backward")
                time.sleep(0.05)
            time.sleep(0.1)
        
        # Then rapid spinning with intermittent thrust
        print("Phase 2: Rotation with thrust")
        spin_dir = "left" if random.random() < 0.5 else "right"
        for _ in range(3):
            # Spin
            for _ in range(5):
                self.safe_api_call(f"rotate_{spin_dir}")
                time.sleep(0.04)
            
            # Thrust
            for _ in range(3):
                self.safe_api_call("thrust_forward")
                time.sleep(0.05)
        
        # Finally, strong forward thrust
        print("Phase 3: Strong forward thrust")
        for _ in range(8):
            self.safe_api_call("thrust_forward")
            time.sleep(0.04)
            
        return True

    def update_occupancy_grid(self, scan_data, current_position, current_heading):
        """Update occupancy grid based on scan data"""
        if not scan_data or not current_position:
            return
            
        import numpy as np
        
        # Constants for grid updating
        OCCUPIED_PROBABILITY = 0.9  # High probability for detected obstacles
        FREE_PROBABILITY = 0.1      # Low probability for free space
        DECAY_FACTOR = 0.99         # Slow decay of certainty over time
        
        # Get obstacle information from scan
        obstacles = []
        if "nearby_objects" in scan_data:
            for obj in scan_data["nearby_objects"]:
                if obj.get("type") == "obstacle" or obj.get("type") == "circular":
                    rel_pos = obj.get("relative_position", [0, 0])
                    # Calculate absolute position
                    obj_x = current_position[0] + rel_pos[0]
                    obj_y = current_position[1] + rel_pos[1]
                    # Add to obstacles list
                    obstacles.append((obj_x, obj_y))
                    
        # Apply decay to entire grid (mild forgetting to handle dynamic environments)
        self.occupancy_grid = self.occupancy_grid * DECAY_FACTOR
        
        # Mark current position as visited
        current_grid = self.world_to_grid(current_position[0], current_position[1])
        if 0 <= current_grid[0] < self.grid_width and 0 <= current_grid[1] < self.grid_height:
            self.visited_cells.add(current_grid)
        
        # Mark current position and a small area around it as free
        radius = 3  # cells
        for dx in range(-radius, radius+1):
            for dy in range(-radius, radius+1):
                grid_x = current_grid[0] + dx
                grid_y = current_grid[1] + dy
                
                if 0 <= grid_x < self.grid_width and 0 <= grid_y < self.grid_height:
                    # Update with free space probability (using Bayesian update)
                    self.occupancy_grid[grid_x, grid_y] *= (1 - FREE_PROBABILITY)
        
        # Mark detected obstacles
        for obs_x, obs_y in obstacles:
            obs_grid = self.world_to_grid(obs_x, obs_y)
            
            if 0 <= obs_grid[0] < self.grid_width and 0 <= obs_grid[1] < self.grid_height:
                # Update with occupied probability (using Bayesian update)
                self.occupancy_grid[obs_grid[0], obs_grid[1]] = max(
                    self.occupancy_grid[obs_grid[0], obs_grid[1]],
                    OCCUPIED_PROBABILITY
                )
                
                # Add some uncertainty to neighboring cells
                for dx in range(-1, 2):
                    for dy in range(-1, 2):
                        if dx == 0 and dy == 0:
                            continue  # Skip center cell (already updated)
                            
                        neighbor_x = obs_grid[0] + dx
                        neighbor_y = obs_grid[1] + dy
                        
                        if 0 <= neighbor_x < self.grid_width and 0 <= neighbor_y < self.grid_height:
                            # Lower probability for neighboring cells
                            self.occupancy_grid[neighbor_x, neighbor_y] = max(
                                self.occupancy_grid[neighbor_x, neighbor_y],
                                OCCUPIED_PROBABILITY * 0.7
                            )
    
    def enhanced_movement_thread(self):
        """Movement thread with better obstacle avoidance and wall detection"""
        print("Enhanced movement thread started")
        movement_counter = 0
        last_turn_counter = 0
        
        # Direction persistence - helps agent maintain course
        self.preferred_direction = "straight"
        self.direction_persistence = 50  # Keep direction for ~50 iterations
        
        # Initial thrust - simple but effective
        print("🚀 PERFORMING POWERFUL INITIAL THRUST")
        for _ in range(8):
            self.safe_api_call("thrust_forward")
            time.sleep(0.05)
        
        while self.game_running:
            try:
                # Get current state and scan
                with self.state_lock:
                    current_state = self.game_state.copy() if self.game_state else None
                
                with self.scan_lock:
                    current_scan = self.scan_data.copy() if self.scan_data else None
                    
                # Skip if we don't have scan data
                if not current_scan or not current_state:
                    time.sleep(0.1)
                    continue
                    
                # Get position and velocity
                current_pos = current_state.get("position", [0, 0])
                current_heading = current_state.get("angle", 0)
                velocity = current_state.get("velocity", [0, 0])
                speed = math.hypot(velocity[0], velocity[1])
                
                # Update world model with sensor data
                self.update_occupancy_grid(current_scan, current_pos, current_heading)
                
                # Debug output
                movement_counter += 1
                if movement_counter % 30 == 0:
                    print(f"DEBUG: Speed: {speed:.1f}, Position: {current_pos}")
                    # Print debug info occasionally
                    if movement_counter % 90 == 0:
                        self.print_debug_info(current_state, current_scan)
                

                # PRIORITY 1.5: Check for immediate obstacles (prevent collisions before they happen)
                obstacle_detected, obstacle_data = self.check_for_immediate_obstacles(current_scan)
                if obstacle_detected:
                    print("⚠️ OBSTACLE DETECTED - IMMEDIATE AVOIDANCE REQUIRED!")
                    self.handle_obstacle_avoidance(obstacle_data)
                    time.sleep(0.1)
                    continue
                
                # PRIORITY 1: Check for collisions first (highest importance)
                if self.detect_and_respond_to_collision(current_state):
                    time.sleep(0.2)
                    continue
                    
                # PRIORITY 2: Check if we're in a corner (highest priority after collisions)
                if self.detect_corner_trap(current_scan):
                    print("🚨 CORNER DETECTED - EXECUTING BOUNDARY CORNER ESCAPE!")
                    self.execute_boundary_corner_escape()
                    last_turn_counter = movement_counter
                    time.sleep(0.2)
                    continue
                    
                # PRIORITY 3: Check for walls/borders
                wall_detected, wall_type = self.check_for_borders_and_walls(current_scan, current_pos)
                if wall_detected:
                    print(f"🧱 Wall detected ({wall_type}) - EXECUTING WALL ESCAPE!")
                    self.execute_wall_escape(wall_type)
                    last_turn_counter = movement_counter
                    time.sleep(0.2)
                    continue
                    
                # PRIORITY 4: Add stuck detection
                if speed < 1.0:
                    if not hasattr(self, 'stuck_counter'):
                        self.stuck_counter = 0
                    else:
                        self.stuck_counter += 1
                    
                    # If stuck for too long, execute super escape
                    if self.stuck_counter > 10:  # Stuck for ~1.5 seconds
                        print("🔥 AGENT APPEARS STUCK - EXECUTING SUPER ESCAPE!")
                        self.execute_super_escape()
                        self.stuck_counter = 0
                        last_turn_counter = movement_counter
                        time.sleep(0.2)
                        continue
                else:
                    # Reset stuck counter if moving
                    if hasattr(self, 'stuck_counter'):
                        self.stuck_counter = 0
                
                # PRIORITY 5: Handle low speed - boost
                if speed < 2.5:
                    print("🔥 Boosting speed!")
                    
                    # Only turn if very slow and it's been a while since last turn
                    if speed < 1.0 and movement_counter - last_turn_counter > 20:
                        # Look for gap to navigate through
                        gaps = self.detect_obstacle_gaps(current_scan, current_pos, current_heading)
                        if gaps:
                            self.navigate_through_gap(gaps[0], current_heading)
                        else:
                            # No clear gap, make a small turn
                            turn_dir = "left" if random.random() < 0.5 else "right"
                            for _ in range(random.randint(1, 2)):
                                self.safe_api_call(f"rotate_{turn_dir}")
                                time.sleep(0.04)
                        last_turn_counter = movement_counter
                    
                    # Strong thrust to boost speed
                    for _ in range(4):
                        self.safe_api_call("thrust_forward")
                        time.sleep(0.04)
                        
                    continue
                # PRIORITY 5.5: Use A* path planning when appropriate
                # Add this after handling low speed and before normal exploration
                #if not obstacle_detected and speed > 2.0 and (
                 #   movement_counter % 50 == 0 or  # Periodically check path
                  #  not self.waypoints):           # We need a new path
        
                    # Try to plan and follow a path
                   # if self.plan_and_follow_path():
                        # Successfully planning/following a path
                    #    continue

                # PRIORITY 6: Normal exploration - MUCH LESS frequent turns
                if (movement_counter - last_turn_counter > 50 and  # Only turn every 50+ iterations
                    random.random() < 0.3):  # Only 30% chance when that happens (reduced from 40%)
                    
                    # Look for gaps to navigate through
                    gaps = self.detect_obstacle_gaps(current_scan, current_pos, current_heading)
                    
                    if gaps:
                        # Navigate through the best gap
                        print("🔍 Found navigable gap - exploring in that direction")
                        self.navigate_through_gap(gaps[0], current_heading)
                    else:
                        # No clear gap, use simple direction selection
                        if self.preferred_direction != "straight" and random.random() < 0.7:
                            turn_dir = self.preferred_direction
                        else:
                            turn_dir = "left" if random.random() < 0.5 else "right"
                        
                        print(f"🔄 Minor course adjustment: turning {turn_dir}")
                        
                        # Very small turns during normal exploration - max 1 rotation
                        for _ in range(random.randint(1, 1)):
                            self.safe_api_call(f"rotate_{turn_dir}")
                            time.sleep(0.04)
                        
                        self.preferred_direction = turn_dir
                    
                    last_turn_counter = movement_counter
                    
                # ALWAYS MOVE FORWARD during normal operation
                self.safe_api_call("thrust_forward")
                
            except Exception as e:
                print(f"Error in movement thread: {e}")
                import traceback
                traceback.print_exc()
            
            # Sleep to prevent CPU overuse
            time.sleep(0.15)

    def safe_api_call(self, action):
        """Make API calls with error handling and quit on timeout"""
        max_retries = 2  # Reduced from 3 to fail faster
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                valid_actions = ["thrust_forward", "thrust_backward", 
                            "rotate_left", "rotate_right", "shoot"]
                
                if action not in valid_actions:
                    print(f"⚠️ Invalid action: {action}")
                    return
                    
                # Make the API call
                resp = requests.post(f"{API_URL}/player/{self.player_id}/{action}", timeout=0.8)
                
                if resp.status_code == 200:
                    return  # Success
                else:
                    print(f"⚠️ API call failed: {action} returned {resp.status_code}")
                    retry_count += 1
                    
            except requests.exceptions.Timeout:
                print(f"🚨 API TIMEOUT detected in call to {action}")
                self.terminate_agent("API timeout detected")
                return
                
            except Exception as e:
                if "Connection" in str(e):  # Connection errors
                    print(f"🚨 CONNECTION ERROR: {action}")
                    self.terminate_agent("Connection error detected")
                    return
                else:
                    print(f"⚠️ Error in API call to {action}: {e}")
                    return
        
        if retry_count >= max_retries:
            print(f"❌ Failed to execute {action} after {max_retries} retries")
            self.terminate_agent("Max API retries exceeded")

    def terminate_agent(self, reason):
        """Safely terminate the agent with all threads"""
        print(f"\n\n🚨 TERMINATING AGENT: {reason} 🚨\n")
        
        # Set flag to stop all threads
        self.game_running = False
        
        # Small delay to allow threads to notice the flag
        time.sleep(0.5)
        
        # Force shutdown if needed
        try:
            print("📋 Shutting down agent...")
            os._exit(1)  # Force exit
        except:
            sys.exit(1)  # Alternative exit

    def run(self):
        """Main method to run the agent with enhanced navigation capabilities"""
        try:
            # Check if server is running
            try:
                print("Checking if game server is running...")
                resp = requests.get(f"{API_URL}/game_status", timeout=1.0)
                if resp.status_code != 200:
                    print(f"⚠️ ERROR: Game server not responding correctly. Status: {resp.status_code}")
                    return
                game_status = resp.json().get('state', 'unknown')
                print(f"✅ Game server is running. Status: {game_status}")
                if game_status == "ended":
                    print("Game has already ended. Please restart the server.")
                    return
            except Exception as e:
                print(f"⚠️ ERROR: Could not connect to game server: {e}")
                return
            
            # Connect to the server
            self.connect()
            
            # Signal that we're ready to play
            self.ready()
            
            # Initialize advanced navigation components
            print("Initializing advanced navigation systems...")
            
            # Initialize occupancy grid if not already done in __init__
            field_width, field_height = self.field_size
            self.grid_resolution = 10  # 10 cells per world unit
            self.grid_width = int(field_width // self.grid_resolution) + 1
            self.grid_height = int(field_height // self.grid_resolution) + 1
            
            # Initialize empty occupancy grid (0 = free, 1 = occupied)
            if not hasattr(self, 'occupancy_grid'):
                import numpy as np
                self.occupancy_grid = np.zeros((self.grid_width, self.grid_height))
                
            # Initialize PID controllers
            self.initialize_pid_controllers()
            
            # Initialize path planning variables
            self.waypoints = []
            self.current_waypoint = None
            self.visited_cells = set()
            
            # Game is running until explicitly set to False
            self.game_running = True
            
            # Start our threads
            print("Starting multi-threaded agent system with advanced navigation")
            
            # Create and start sensor thread
            self.sensor_thread_obj = threading.Thread(target=self.sensor_thread)
            self.sensor_thread_obj.daemon = True
            self.sensor_thread_obj.start()
            
            # Small delay to allow sensor thread to get initial data
            time.sleep(0.5)
            
            # Create and start enhanced movement thread
            self.movement_thread_obj = threading.Thread(target=self.enhanced_movement_thread)
            self.movement_thread_obj.daemon = True
            self.movement_thread_obj.start()
            
            # Create and start combat thread
            self.combat_thread_obj = threading.Thread(target=self.combat_thread)
            self.combat_thread_obj.daemon = True
            self.combat_thread_obj.start()
        
            # Create and start game status monitoring thread
            self.status_thread_obj = threading.Thread(target=self.check_game_status_thread)
            self.status_thread_obj.daemon = True
            self.status_thread_obj.start()
            
            # Keep main thread alive until game ends
            while self.game_running:
                time.sleep(0.5)
                
        except KeyboardInterrupt:
            print("Agent system terminated by user")
            self.game_running = False
        except Exception as e:
            print(f"Error in agent main loop: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.game_running = False
            print("Agent system terminated")     
        
if __name__ == "__main__":
    agent = DummyMeretAgent()
    agent.run()