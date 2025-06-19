
import requests
import requests.exceptions
import time
import math
import signal
import sys
from src.settings import (
    API_URL,
    COOLDOWN_SCAN_ENVIRONMENT,
    COOLDOWN_PLAYER_STATE,
    COOLDOWN_GAME_STATE,
    COOLDOWN_SHOOT,
)
import random
class RuleAgent:
    def __init__(self):
        self.player_id = None
        self.game_active = False
        self.running = True
        self.last_patrol = 0
        self.patrol_interval = 1  # seconds between patrol actions
        self.last_scan = 0
        self.last_state = 0
        self.last_game_state = 0
        self.last_shot = 0
        self.last_ready_sent = 0
        self.connect()
    def connect(self):
        try:
            self.player_id = requests.post(f"{API_URL}/connect").json()["player_id"]
            print(f"🆕 Connected as {self.player_id}")
            self.send_ready(force=True)
        except Exception as e:
            print("❌ Could not connect to server:", e)
            sys.exit(1)
    def send_ready(self, force=False):
        now = time.time()
        # Avoid spamming ready, but allow forced send (e.g. after restart)
        if force or (now - self.last_ready_sent > 1.0):
            try:
                requests.post(f"{API_URL}/player/ready/{self.player_id}")
                print("✅ Ready sent")
                self.last_ready_sent = now
            except Exception as e:
                print("⚠️ Error sending ready:", e)
    def get_game_state(self):
        now = time.time()
        if now - self.last_game_state < COOLDOWN_GAME_STATE:
            time.sleep(COOLDOWN_GAME_STATE - (now - self.last_game_state))
        try:
            res = requests.get(f"{API_URL}/player/{self.player_id}/game-state")
            self.last_game_state = time.time()
            if res.status_code == 429:
                print("⚠️ Too many requests to game-state")
                return {}
            return res.json()
        except Exception as e:
            print("⚠️ Error fetching game-state:", e)
            return {}
    def get_state(self):
        now = time.time()
        # Fetch player state
        if now - self.last_state < COOLDOWN_PLAYER_STATE:
            time.sleep(COOLDOWN_PLAYER_STATE - (now - self.last_state))
        try:
            state = requests.get(f"{API_URL}/player/{self.player_id}/state").json()
            self.last_state = time.time()
        except Exception as e:
            print("⚠️ Error fetching player state:", e)
            state = {}
        # Fetch scan
        now = time.time()
        if now - self.last_scan < COOLDOWN_SCAN_ENVIRONMENT:
            time.sleep(COOLDOWN_SCAN_ENVIRONMENT - (now - self.last_scan))
        try:
            scan = requests.get(f"{API_URL}/player/{self.player_id}/scan").json()
            self.last_scan = time.time()
            objects = scan.get("nearby_objects", [])
        except Exception as e:
            print("⚠️ Error fetching scan:", e)
            objects = []
        return state, objects
    def disconnect(self):
        if self.player_id:
            try:
                requests.post(f"{API_URL}/disconnect/{self.player_id}")
                print("👋 Disconnected from server.")
            except Exception:
                pass
    def act(self, state, objects):
        if not self.game_active:
            return
        threats = [o for o in objects if o["type"] == "projectile" and o["distance"] < 120]
        enemies = [o for o in objects if o["type"] == "other_player"]
        borders = [o for o in objects if o["type"] == "border"]
        obstacles = [o for o in objects if o["type"] == "obstacle"]
        # 1. Avoid getting stuck at the border (improved logic)
        if borders:
            closest_border = min(borders, key=lambda b: b["distance"])
            border_threshold = 40  # react earlier
            if closest_border["distance"] < border_threshold:
                print("🧱 Too close to border – turning away")
                bx, by = closest_border["relative_position"]
                border_angle = math.atan2(by, bx)
                # Rotate away from border direction
                if border_angle > 0:
                    requests.post(f"{API_URL}/player/{self.player_id}/rotate_left")
                else:
                    requests.post(f"{API_URL}/player/{self.player_id}/rotate_right")
                requests.post(f"{API_URL}/player/{self.player_id}/thrust_forward")
                return
        # 2. Avoid projectiles based on their approach angle
        if threats:
            print("🚨 Incoming projectile – evading")
            projectile = threats[0]
            vx, vy = projectile.get("relative_velocity", [0, 0])
            angle = math.degrees(math.atan2(vy, vx))
            if -90 < angle < 90:
                requests.post(f"{API_URL}/player/{self.player_id}/rotate_left")
            else:
                requests.post(f"{API_URL}/player/{self.player_id}/rotate_right")
            requests.post(f"{API_URL}/player/{self.player_id}/thrust_forward")
            return
        # 3. Engage enemy
        if enemies:
            target = min(enemies, key=lambda e: abs(e.get("relative_position", [999, 999])[0]))
            rel_angle = math.atan2(target["relative_position"][1], target["relative_position"][0])
            abs_deg = abs(math.degrees(rel_angle))
            def is_visible(enemy):
                for obs in obstacles:
                    obs_x, obs_y = obs["relative_position"]
                    enemy_x, enemy_y = enemy["relative_position"]
                    obs_dist = math.hypot(obs_x, obs_y)
                    enemy_dist = math.hypot(enemy_x, enemy_y)
                    if obs_dist < enemy_dist and abs(obs_x - enemy_x) < 40 and abs(obs_y - enemy_y) < 40:
                        return False
                return True
            if abs_deg < 10 and is_visible(target):
                now = time.time()
                if now - self.last_shot >= COOLDOWN_SHOOT:
                    print("🎯 Enemy in sight – firing")
                    requests.post(f"{API_URL}/player/{self.player_id}/shoot")
                    self.last_shot = now
            if rel_angle > 0.1:
                requests.post(f"{API_URL}/player/{self.player_id}/rotate_left")
            elif rel_angle < -0.1:
                requests.post(f"{API_URL}/player/{self.player_id}/rotate_right")
            if target["distance"] > 150:
                requests.post(f"{API_URL}/player/{self.player_id}/thrust_forward")
            return
        # 4. Patrol (rate-limited)
        now = time.time()
        if now - self.last_patrol > self.patrol_interval:
            print(f"🔄 Patrolling...")
            requests.post(f"{API_URL}/player/{self.player_id}/rotate_left")
            requests.post(f"{API_URL}/player/{self.player_id}/thrust_forward")
            self.last_patrol = now
    def run(self):
        def handle_exit(signum, frame):
            print("\n🛑 Exiting agent...")
            self.running = False
            self.disconnect()
            sys.exit(0)
        # Register signal handlers for clean exit
        signal.signal(signal.SIGINT, handle_exit)
        signal.signal(signal.SIGTERM, handle_exit)
        last_ready_state = False
        game_state_check_interval = max(COOLDOWN_GAME_STATE, 1.0)
        last_game_state_check = time.time() - game_state_check_interval
        while self.running:
            try:
                # Check if visualizer is still running (exit if not)
                if not self.is_visualizer_alive():
                    print("🖼️ Visualizer closed or parent process gone. Exiting agent.")
                    self.running = False
                    break
                now = time.time()
                if now - last_game_state_check >= game_state_check_interval:
                    game_state = self.get_game_state()
                    last_game_state_check = now
                    self.game_active = game_state.get("game_started", False)
                    # Fix: Always send ready if not ready
                    if not self.game_active:
                        if not game_state.get("ready", False):
                            self.send_ready(force=True)
                            last_ready_state = True
                        print("⏳ Waiting for game to start...")
                        time.sleep(2)
                        continue
                if self.game_active:
                    state, objects = self.get_state()
                    if state:
                        self.act(state, objects)
                        last_ready_state = False
                # Sleep at least as long as the shortest cooldown to avoid spamming
                time.sleep(min(COOLDOWN_SCAN_ENVIRONMENT, COOLDOWN_PLAYER_STATE, 0.1))
            except requests.exceptions.ConnectionError:
                print("🚫 Lost connection to game server. Exiting.")
                self.running = False
                break
            except SystemExit:
                break
            except Exception as e:
                print("⚠️ Unexpected error:", e)
                time.sleep(0.5)
        self.disconnect()
    def is_visualizer_alive(self):
        """
        Returns False if the parent process (usually the visualizer or terminal) is gone.
        On Linux, if the parent PID is 1 (init), the parent is gone.
        """
        try:
            import os
            ppid = os.getppid()
            if ppid == 1:
                return False
            return True
        except Exception:
            return True
if __name__ == "__main__":
    RuleAgent().run()
