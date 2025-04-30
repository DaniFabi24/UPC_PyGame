API_HOST = "127.0.0.1"
API_PORT = 8000
API_URL = f"http://{API_HOST}:{API_PORT}"

# Weitere Konfigurationen für den Visualizer:
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
FPS = 30

# Bewegungsparameter für den Spieler
PLAYER_THRUST   =   20          # festgelegter Thrust-Wert
PLAYER_ROTATION =   1     # festgelegter Rotationswert
PLAYER_MAX_SPEED =  100      # maximale Geschwindigkeit
PHYSICS_DT = 1/FPS          # Zeitintervall für Physik-Updates