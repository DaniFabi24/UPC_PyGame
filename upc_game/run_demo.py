import sys
import os

# Füge das Hauptprojektverzeichnis zum Python-Pfad hinzu
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import subprocess
import time

# Start the FastAPI application
#api_process = subprocess.Popen(["uvicorn", "api.api_endpoints:app", "--reload"])
#time.sleep(10) # Give the server some time to start

# Start the Pygame visualizer
visualizer_process = subprocess.Popen(["python", "visualizer/game_visualizer.py"])
'''
try:
    # Wait until one of the processes finishes (e.g., by pressing Ctrl+C)
    while api_process.poll() is None and visualizer_process.poll() is None:
        time.sleep(0.1)
except KeyboardInterrupt:
    print("Demo ended.")
finally:
    print("Terminating processes...")
    if api_process.poll() is None:
        api_process.terminate()
        api_process.wait()
    if visualizer_process.poll() is None:
        visualizer_process.terminate()
        visualizer_process.wait()
    print("All processes terminated.")
'''
visualizer_process.wait()
print("Demo ended.")