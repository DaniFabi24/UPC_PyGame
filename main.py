import threading
import time
import uvicorn
from upc_game.settings import API_HOST, API_PORT

def run_api_server():
    # Starte den API-Server – Dieser nutzt die Startup Events (Physik-Engine wird dort gestartet).
    uvicorn.run("upc_game.api.api_endpoints:app", host=API_HOST, port=API_PORT, log_level="info")

if __name__ == "__main__":
    # Starte den API-Server in einem separaten Thread (als Daemon)
    api_thread = threading.Thread(target=run_api_server, daemon=True)
    api_thread.start()
    
    # Gib dem API-Server etwas Zeit zum Starten
    time.sleep(5)
    
    # Importiere die globale game_world_instance und starte den Visualizer im Hauptthread
    from upc_game.core.game_world import game_world_instance
    game_world_instance.run_visualizer()