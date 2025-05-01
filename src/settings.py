API_HOST = "127.0.0.1"
API_PORT = 8000
API_URL = f"http://{API_HOST}:{API_PORT}"

# Weitere Konfigurationen für den Visualizer:
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
FPS = 60

# Bewegungsparameter für den Spieler
PLAYER_THRUST   =   5          # festgelegter Thrust-Wert
PLAYER_ROTATION =   0.05     # festgelegter Rotationswert
PLAYER_MAX_SPEED =  50      # maximale Geschwindigkeit
PHYSICS_DT = 1/FPS          # Zeitintervall für Physik-Updates
PROJECTILE_SPEED = 300
PROJECTILE_RADIUS = 4
PROJECTILE_COLOR = (255, 255, 0)  # Yellow
PROJECTILE_LIFETIME_SECONDS = 3.0  # Remove after 3 seconds

# Player Settings
PLAYER_START_HEALTH = 5 # *** Geändert auf 5 Leben ***
OBSTACLE_DAMAGE = 1 # Schaden pro Kollision mit einem Hindernis (ggf. anpassen)

# Projectile Settings
PROJECTILE_DAMAGE = 1 # *** NEU: Schaden pro Projektiltreffer ***
ALLOW_FRIENDLY_FIRE = False # *** NEU: Eigenbeschuss erlauben? ***