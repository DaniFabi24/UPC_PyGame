# --- API Server Configuration ---
API_HOST = "127.0.0.1"  # Host address for the FastAPI server
API_PORT = 8000         # Port number for the FastAPI server
API_URL = f"http://{API_HOST}:{API_PORT}" # Full base URL for API requests (used by agent)

# --- Visualizer / Screen Configuration ---
SCREEN_WIDTH = 800      # Width of the Pygame window in pixels
SCREEN_HEIGHT = 600     # Height of the Pygame window in pixels
FPS = 60                # Target frames per second for the visualizer and physics updates

# --- Physics Engine Configuration ---
PHYSICS_DT = 1/FPS      # Time step for each physics simulation update (delta time)

# --- Player Movement Parameters ---
PLAYER_THRUST = 5       # Force applied when the player accelerates forward
PLAYER_ROTATION = 0.05  # Angular velocity applied when the player rotates (in radians per update)
PLAYER_MAX_SPEED = 40   # Maximum linear velocity the player can reach

# --- Player Attributes ---
PLAYER_START_HEALTH = 5 # Initial health points for each player
SCANNING_RADIUS = 150   # Radius within which a player can detect other objects (in pixels)

# --- Projectile Configuration ---
PROJECTILE_SPEED = 200          # Initial speed of a fired projectile
PROJECTILE_RADIUS = 4           # Radius of the projectile's physics shape and visual representation
# PROJECTILE_COLOR is now determined by the player's color, this line is obsolete:
# PROJECTILE_COLOR = (255, 255, 0)  # Yellow
PROJECTILE_LIFETIME_SECONDS = 3.0 # Duration in seconds before a projectile is automatically removed
PROJECTILE_DAMAGE = 1           # Amount of health points deducted when a projectile hits a player
ALLOW_FRIENDLY_FIRE = False     # If True, projectiles can damage the player who fired them (currently not implemented based on color/ID)

# --- Obstacle Configuration ---
OBSTACLE_DAMAGE = 1             # Amount of health points deducted when a player collides with an obstacle (currently disabled in collision handler)

# --- Countdown Configuration ---
COUNTDOWN_DURATION = 3.0  # Dauer des Countdowns in Sekunden, bevor das Spiel startet