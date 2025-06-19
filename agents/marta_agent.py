import requests
import time
from world_model import WorldModel
import heapq
import math
import numpy as np

class SmartAgent:
    def __init__(self):
        self.player_id = None
        self.api_base = "http://127.0.0.1:8000"
        self.last_scan_time = 0
        self.start_time = time.time()
        self.scan_cooldown = 0.51  # Ainda mais rápido - quase no limite
        self.world_model = WorldModel(grid_size=200, resolution=2, agent_id=str(id(self)))
        self.path = []
        self.last_shot_time = 0
        self.shot_cooldown = 0.6  # Mais rápido - reduzido de 0.7 para 0.6
        self.last_plan_time = 0
        self.plan_interval = 2.0
        
        # NOVO: Sistema melhorado de evitamento de obstáculos
        self.obstacle_avoidance_mode = False
        self.avoidance_phase = "turn_away"
        self.avoidance_start_time = 0
        # NOVO: Distâncias de detecção ajustadas para o mapa 800x600
        self.obstacle_detection_distance = 80   # Aumentado de 60 para 80 (deteta mais longe)
        self.border_detection_distance = 110    # Aumentado de 100 para 110
        self.alignment_tolerance = 0.3  # Menos precisão = mais velocidade (era 0.25)
        
        # NOVO: Sistema de prevenção proativa
        self.prevention_active = False
        self.last_direction_check = 0
        
        # NOVO: Controle de movimento para o centro
        self.going_to_center = False
        self.center_tolerance = 25  # Reduzido de 30 para 25 (chega mais perto do centro)
        
        # NOVO: Sistema de busca ativa de inimigos
        self.search_mode = False
        self.search_pattern = "spiral"  # "spiral", "zigzag", "patrol"
        self.search_angle = 0
        self.search_radius = 50
        self.last_enemy_seen_time = 0
        self.enemy_search_timeout = 6  # Reduzido de 8 para 6s (busca mais rápido)
        
        # NOVO: Memória persistente de obstáculos
        self.known_obstacles = {}  # {(x, y): {"type": str, "size": float, "last_seen": time}}
        self.obstacle_map_resolution = 20  # Resolução do grid de obstáculos
        self.safe_paths = []  # Caminhos conhecidos entre obstáculos
        self.last_obstacle_update = 0

    def connect(self, agent_name="marta"):
        try:
            response = requests.post(
                f"{self.api_base}/connect",
                json={"agent_name": agent_name},
                timeout=2
            )
            response.raise_for_status()
            data = response.json()
            self.player_id = data.get("player_id")
            print(f"[INFO] Connected successfully. Player ID: {self.player_id}")
            return True
        except requests.exceptions.RequestException as e:
            print(f"[ERROR] Connection failed: {e}")
            return False

    def update_obstacle_memory(self, scan, position):
        """
        NOVO: Atualiza memória persistente de obstáculos e cria mapa tático
        """
        now = time.time()
        obstacles_detected = 0
        
        for obj in scan.get("nearby_objects", []):
            if obj["type"] in ["obstacle", "border"]:
                # Calcula posição absoluta do obstáculo
                rel_x, rel_y = obj["relative_position"]
                abs_x = position[0] + rel_x
                abs_y = position[1] + rel_y
                
                # Quantiza posição para criar grid
                grid_x = round(abs_x / self.obstacle_map_resolution) * self.obstacle_map_resolution
                grid_y = round(abs_y / self.obstacle_map_resolution) * self.obstacle_map_resolution
                obstacle_key = (grid_x, grid_y)
                
                # Atualiza memória
                self.known_obstacles[obstacle_key] = {
                    "type": obj["type"],
                    "size": 15 if obj["type"] == "obstacle" else 5,  # Estimativa do tamanho
                    "last_seen": now,
                    "distance": obj["distance"]
                }
                obstacles_detected += 1
        
        # Remove obstáculos muito antigos (>30s sem ver)
        old_obstacles = [k for k, v in self.known_obstacles.items() 
                        if now - v["last_seen"] > 30]
        for k in old_obstacles:
            del self.known_obstacles[k]
        
        if obstacles_detected > 0:
            self.last_obstacle_update = now
            print(f"[MEMORY] {obstacles_detected} obstáculos detectados. Total conhecido: {len(self.known_obstacles)}")

    def find_safe_corridor(self, start_pos, target_pos):
        """
        NOVO: Encontra corredor seguro entre obstáculos conhecidos
        """
        if not self.known_obstacles:
            return None
        
        # Calcula direção geral para o target
        dx = target_pos[0] - start_pos[0]
        dy = target_pos[1] - start_pos[1]
        target_angle = math.atan2(dy, dx)
        distance_to_target = math.sqrt(dx**2 + dy**2)
        
        # Procura por corredores livres em direção ao target
        best_path = None
        min_obstacle_distance = 0
        
        # Testa diferentes ângulos perto da direção do target
        for angle_offset in [-0.5, -0.25, 0, 0.25, 0.5]:  # ±30 graus
            test_angle = target_angle + angle_offset
            path_clear = True
            min_clearance = float('inf')
            
            # Testa pontos ao longo do caminho
            for step in range(5, min(int(distance_to_target), 100), 10):
                test_x = start_pos[0] + math.cos(test_angle) * step
                test_y = start_pos[1] + math.sin(test_angle) * step
                
                # Verifica distância aos obstáculos conhecidos
                for obs_pos, obs_data in self.known_obstacles.items():
                    obs_x, obs_y = obs_pos
                    dist_to_obs = math.sqrt((test_x - obs_x)**2 + (test_y - obs_y)**2)
                    clearance_needed = obs_data["size"] + 25  # Margem de segurança
                    
                    if dist_to_obs < clearance_needed:
                        path_clear = False
                        break
                    
                    min_clearance = min(min_clearance, dist_to_obs - obs_data["size"])
                
                if not path_clear:
                    break
            
            # Se encontrou caminho limpo, verifica se é o melhor
            if path_clear and min_clearance > min_obstacle_distance:
                min_obstacle_distance = min_clearance
                best_path = {
                    "angle": test_angle,
                    "clearance": min_clearance,
                    "angle_offset": angle_offset
                }
        
        return best_path

    def intelligent_obstacle_navigation(self, position, orientation, target_pos):
        """
        NOVO: Navegação inteligente usando memória de obstáculos
        """
        safe_path = self.find_safe_corridor(position, target_pos)
        
        if safe_path:
            target_angle = safe_path["angle"]
            angle_diff = (target_angle - orientation + math.pi) % (2 * math.pi) - math.pi
            
            print(f"[NAV] Corredor seguro encontrado! Ângulo: {target_angle:.2f}, Clearance: {safe_path['clearance']:.1f}")
            
            # Alinha com o corredor seguro
            if abs(angle_diff) > 0.15:
                if angle_diff > 0:
                    self.rotate_right()
                else:
                    self.rotate_left()
                return True
            else:
                # Avança pelo corredor
                self.thrust()
                return True
        else:
            print(f"[NAV] Nenhum corredor seguro encontrado - usando navegação padrão")
            return False

    def active_enemy_search(self, position, orientation):
        """
        NOVO: Sistema de busca ativa de inimigos entre obstáculos conhecidos
        """
        now = time.time()
        
        # Se viu inimigo recentemente, não precisa buscar
        if now - self.last_enemy_seen_time < self.enemy_search_timeout:
            self.search_mode = False
            return False
        
        # Ativa modo de busca
        if not self.search_mode:
            print("[SEARCH] Ativando busca ativa de inimigos!")
            self.search_mode = True
            self.search_angle = orientation  # Começa da orientação atual
        
        # NOVO: Busca inteligente entre obstáculos conhecidos
        if self.known_obstacles and self.search_pattern == "spiral":
            # Encontra espaços entre obstáculos para buscar
            target_search_pos = self.find_search_target_between_obstacles(position)
            
            if target_search_pos:
                # Tenta navegar para posição de busca entre obstáculos
                if self.intelligent_obstacle_navigation(position, orientation, target_search_pos):
                    print(f"[SEARCH] Navegando entre obstáculos para {target_search_pos}")
                    return True
        
        # Fallback para busca espiral padrão (mais rápida)
        if self.search_pattern == "spiral":
            # Padrão espiral - gira e avança mais rápido
            self.search_angle += 0.4  # Aumentado de 0.3 para 0.4 (mais rápido)
            if self.search_angle > 2 * math.pi:
                self.search_angle = 0
                self.search_radius = min(self.search_radius + 25, 150)  # Aumenta raio mais rápido
            
            # Calcula direção da busca
            angle_diff = (self.search_angle - orientation + math.pi) % (2 * math.pi) - math.pi
            
            if abs(angle_diff) > 0.15:  # Reduzido de 0.2 para 0.15 (menos precisão)
                # Roda para a direção de busca
                if angle_diff > 0:
                    self.rotate_right()
                else:
                    self.rotate_left()
                print(f"[SEARCH] Espiral - rodando rápido para {self.search_angle:.2f}")
            else:
                # Avança mais na direção atual
                future_x = position[0] + math.cos(orientation) * 20  # Aumentado de 15 para 20
                future_y = position[1] + math.sin(orientation) * 20
                boundary_status, _ = self.check_boundary_proximity([future_x, future_y])
                
                if boundary_status not in ["critical", "danger"]:
                    self.thrust()
                    print(f"[SEARCH] Espiral - avançando rápido raio {self.search_radius}")
                else:
                    # Se ia bater numa borda, muda direção
                    self.search_angle += math.pi / 3  # Vira 60 graus (mais que antes)
                    print(f"[SEARCH] Espiral - evitando borda")
        
        return True

    def find_search_target_between_obstacles(self, position):
        """
        NOVO: Encontra posição estratégica para buscar entre obstáculos
        """
        if len(self.known_obstacles) < 2:
            return None
        
        # Procura gaps entre obstáculos
        obstacle_positions = list(self.known_obstacles.keys())
        best_search_pos = None
        max_gap_size = 0
        
        for i in range(len(obstacle_positions)):
            for j in range(i + 1, len(obstacle_positions)):
                obs1_pos = obstacle_positions[i]
                obs2_pos = obstacle_positions[j]
                
                # Calcula ponto médio entre obstáculos
                mid_x = (obs1_pos[0] + obs2_pos[0]) / 2
                mid_y = (obs1_pos[1] + obs2_pos[1]) / 2
                mid_pos = [mid_x, mid_y]
                
                # Calcula tamanho do gap
                gap_size = math.sqrt((obs2_pos[0] - obs1_pos[0])**2 + (obs2_pos[1] - obs1_pos[1])**2)
                
                # Verifica se é seguro ir para lá
                if (self.world_model.is_position_safe(mid_pos, "normal") and 
                    gap_size > 40 and  # Gap mínimo
                    gap_size > max_gap_size):
                    
                    max_gap_size = gap_size
                    best_search_pos = mid_pos
        
        return best_search_pos

    def update_enemy_tracking(self, scan):
        """
        NOVO: Atualiza informações sobre quando viu inimigos pela última vez
        """
        for obj in scan.get("nearby_objects", []):
            if obj["type"] == "other_player":
                self.last_enemy_seen_time = time.time()
                self.search_mode = False  # Para busca se encontrou inimigo
                if hasattr(self, 'zigzag_direction'):
                    delattr(self, 'zigzag_direction')
                if hasattr(self, 'zigzag_steps'):
                    delattr(self, 'zigzag_steps')
                return True
        
        # Se não viu nenhum inimigo, sai do modo combate
        self.combat_mode = False
        return False

    def update_obstacle_memory(self, scan, position):
        """
        NOVO: Atualiza memória persistente de obstáculos e cria mapa tático
        """
        now = time.time()
        obstacles_detected = 0
        
        for obj in scan.get("nearby_objects", []):
            if obj["type"] in ["obstacle", "border"]:
                # Calcula posição absoluta do obstáculo
                rel_x, rel_y = obj["relative_position"]
                abs_x = position[0] + rel_x
                abs_y = position[1] + rel_y
                
                # Quantiza posição para criar grid
                grid_x = round(abs_x / self.obstacle_map_resolution) * self.obstacle_map_resolution
                grid_y = round(abs_y / self.obstacle_map_resolution) * self.obstacle_map_resolution
                obstacle_key = (grid_x, grid_y)
                
                # Atualiza memória
                self.known_obstacles[obstacle_key] = {
                    "type": obj["type"],
                    "size": 15 if obj["type"] == "obstacle" else 5,  # Estimativa do tamanho
                    "last_seen": now,
                    "distance": obj["distance"]
                }
                obstacles_detected += 1
        
        # Remove obstáculos muito antigos (>30s sem ver)
        old_obstacles = [k for k, v in self.known_obstacles.items() 
                        if now - v["last_seen"] > 30]
        for k in old_obstacles:
            del self.known_obstacles[k]
        
        if obstacles_detected > 0:
            self.last_obstacle_update = now
            print(f"[MEMORY] {obstacles_detected} obstáculos detectados. Total conhecido: {len(self.known_obstacles)}")

    def find_safe_corridor(self, start_pos, target_pos):
        """
        NOVO: Encontra corredor seguro entre obstáculos conhecidos
        """
        if not self.known_obstacles:
            return None
        
        # Calcula direção geral para o target
        dx = target_pos[0] - start_pos[0]
        dy = target_pos[1] - start_pos[1]
        target_angle = math.atan2(dy, dx)
        distance_to_target = math.sqrt(dx**2 + dy**2)
        
        # Procura por corredores livres em direção ao target
        best_path = None
        min_obstacle_distance = 0
        
        # Testa diferentes ângulos perto da direção do target
        for angle_offset in [-0.5, -0.25, 0, 0.25, 0.5]:  # ±30 graus
            test_angle = target_angle + angle_offset
            path_clear = True
            min_clearance = float('inf')
            
            # Testa pontos ao longo do caminho
            for step in range(5, min(int(distance_to_target), 100), 10):
                test_x = start_pos[0] + math.cos(test_angle) * step
                test_y = start_pos[1] + math.sin(test_angle) * step
                
                # Verifica distância aos obstáculos conhecidos
                for obs_pos, obs_data in self.known_obstacles.items():
                    obs_x, obs_y = obs_pos
                    dist_to_obs = math.sqrt((test_x - obs_x)**2 + (test_y - obs_y)**2)
                    clearance_needed = obs_data["size"] + 25  # Margem de segurança
                    
                    if dist_to_obs < clearance_needed:
                        path_clear = False
                        break
                    
                    min_clearance = min(min_clearance, dist_to_obs - obs_data["size"])
                
                if not path_clear:
                    break
            
            # Se encontrou caminho limpo, verifica se é o melhor
            if path_clear and min_clearance > min_obstacle_distance:
                min_obstacle_distance = min_clearance
                best_path = {
                    "angle": test_angle,
                    "clearance": min_clearance,
                    "angle_offset": angle_offset
                }
        
        return best_path

    def intelligent_obstacle_navigation(self, position, orientation, target_pos):
        """
        NOVO: Navegação inteligente usando memória de obstáculos
        """
        safe_path = self.find_safe_corridor(position, target_pos)
        
        if safe_path:
            target_angle = safe_path["angle"]
            angle_diff = (target_angle - orientation + math.pi) % (2 * math.pi) - math.pi
            
            print(f"[NAV] Corredor seguro encontrado! Ângulo: {target_angle:.2f}, Clearance: {safe_path['clearance']:.1f}")
            
            # Alinha com o corredor seguro
            if abs(angle_diff) > 0.15:
                if angle_diff > 0:
                    self.rotate_right()
                else:
                    self.rotate_left()
                return True
            else:
                # Avança pelo corredor
                self.thrust()
                return True
        else:
            print(f"[NAV] Nenhum corredor seguro encontrado - usando navegação padrão")
            return False
        """
        NOVO: Sistema de combate otimizado - MIRAR, ATIRAR, PERSEGUIR
        """
        rel_x, rel_y = enemy_data["relative_position"]
        distance = enemy_data["distance"] 
        angle_to_enemy = math.atan2(rel_y, rel_x)
        
        # Armazena informações do inimigo
        self.last_enemy_position = [position[0] + rel_x, position[1] + rel_y]
        self.last_enemy_angle = angle_to_enemy
        self.combat_mode = True
        
        print(f"[COMBAT] Inimigo a {distance:.1f}px, ângulo: {math.degrees(angle_to_enemy):.1f}°")
        
        # FASE 1: MIRA RÁPIDA E TIRO
        if abs(angle_to_enemy) <= self.aim_tolerance:
            # Tenta atirar se está minimamente alinhado
            now = time.time()
            if now - self.last_shot_time > self.shot_cooldown:
                print(f"[COMBAT] 🎯 DISPARAR! Ângulo: {math.degrees(angle_to_enemy):.1f}°")
                self.send_action("shoot")
                self.last_shot_time = now
                
                # MELHORIA: Continua mirando após o tiro para tiros consecutivos
                if abs(angle_to_enemy) > self.fast_aim_tolerance:
                    self.perform_fast_rotation(angle_to_enemy, orientation)
                    return "aiming"
            
            # Se já atirou recentemente, continua mirando para próximo tiro
            elif abs(angle_to_enemy) > self.fast_aim_tolerance:
                self.perform_fast_rotation(angle_to_enemy, orientation)
                return "aiming"
        
        # FASE 2: ROTAÇÃO RÁPIDA PARA MIRAR
        if abs(angle_to_enemy) > self.fast_aim_tolerance:
            self.perform_fast_rotation(angle_to_enemy, orientation)
            return "aiming"
        
        # FASE 3: PERSEGUIÇÃO AGRESSIVA (só se já está bem alinhado)
        if distance > self.pursuit_distance:
            # Verifica se é EXTREMAMENTE perigoso mover-se
            future_x = position[0] + math.cos(orientation) * 25
            future_y = position[1] + math.sin(orientation) * 25
            
            try:
                future_distance = self.world_model.get_distance_to_boundary([future_x, future_y])
                if future_distance > 30:  # Margem mínima muito reduzida para ser mais agressivo
                    self.thrust()
                    print(f"[COMBAT] ⚡ PERSEGUINDO agressivamente! Dist: {distance:.1f}")
                    return "pursuing"
                else:
                    print(f"[COMBAT] ⚠️ Perseguição perigosa - só atirando")
                    return "holding"
            except:
                # Se falhar verificação, é conservador
                print(f"[COMBAT] ⚠️ Verificação falhou - só atirando")
                return "holding"
        else:
            print(f"[COMBAT] 🎯 Inimigo próximo - foco em mirar e atirar")
            return "close_combat"

    def perform_fast_rotation(self, target_angle, current_orientation):
        """
        NOVO: Sistema de rotação ultrarrápida para combate
        """
        angle_diff = (target_angle - current_orientation + math.pi) % (2 * math.pi) - math.pi
        
        # Rotação mais agressiva em combate
        if abs(angle_diff) > 0.05:  # Muito mais preciso que antes (era 0.15)
            if angle_diff > 0:
                self.rotate_right()
                print(f"[COMBAT] ↻ Rotação rápida DIREITA - diff: {math.degrees(angle_diff):.1f}°")
            else:
                self.rotate_left()
                print(f"[COMBAT] ↺ Rotação rápida ESQUERDA - diff: {math.degrees(angle_diff):.1f}°")
            return True
        else:
            print(f"[COMBAT] ✅ Perfeitamente alinhado!")
            return False

    def predict_enemy_movement(self, current_enemy_pos, previous_enemy_pos, time_delta):
        """
        NOVO: Predição básica de movimento do inimigo para mira antecipada
        """
        if previous_enemy_pos is None or time_delta <= 0:
            return current_enemy_pos
        
        # Calcula velocidade estimada do inimigo
        velocity_x = (current_enemy_pos[0] - previous_enemy_pos[0]) / time_delta
        velocity_y = (current_enemy_pos[1] - previous_enemy_pos[1]) / time_delta
        
        # Prediz posição futura (0.2s à frente)
        prediction_time = 0.2
        predicted_x = current_enemy_pos[0] + velocity_x * prediction_time
        predicted_y = current_enemy_pos[1] + velocity_y * prediction_time
        
        return [predicted_x, predicted_y]
        """
        NOVO: Atualiza informações sobre quando viu inimigos pela última vez
        """
        for obj in scan.get("nearby_objects", []):
            if obj["type"] == "other_player":
                self.last_enemy_seen_time = time.time()
                self.search_mode = False  # Para busca se encontrou inimigo
                if hasattr(self, 'zigzag_direction'):
                    delattr(self, 'zigzag_direction')
                if hasattr(self, 'zigzag_steps'):
                    delattr(self, 'zigzag_steps')
                return True
        return False

    def ready_up(self):
        try:
            response = requests.post(
                f"{self.api_base}/player/ready/{self.player_id}",
                timeout=1
            )
            response.raise_for_status()
            print(f"[INFO] Player {self.player_id} is ready to play.")
        except requests.exceptions.RequestException as e:
            print(f"[ERROR] Failed to set ready status: {e}")

    def get_self_state(self):
        try:
            response = requests.get(
                f"{self.api_base}/player/{self.player_id}/state",
                timeout=1
            )
            if response.status_code == 404:
                print(f"[WARN] Player state not found for {self.player_id}")
                return None
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"[ERROR] Exception getting player state: {e}")
            return None

    def get_scan(self):
        now = time.time()
        if now - self.last_scan_time < self.scan_cooldown:
            time.sleep(self.scan_cooldown - (now - self.last_scan_time))

        try:
            response = requests.get(
                f"{self.api_base}/player/{self.player_id}/scan",
                timeout=1
            )
            self.last_scan_time = time.time()

            if response.status_code == 429:
                wait_time = float(response.headers.get('Retry-After', 0.6))
                time.sleep(wait_time)
                return self.get_scan()
            elif response.status_code == 200:
                return response.json()
            else:
                print(f"[WARN] Scan failed with status {response.status_code}")
                return None
        except requests.exceptions.RequestException as e:
            print(f"[ERROR] Scan exception: {e}")
            return None

    def send_action(self, action: str):
        try:
            response = requests.post(
                f"{self.api_base}/player/{self.player_id}/{action}",
                timeout=1
            )
            if response.status_code != 200:
                print(f"[WARN] Action '{action}' failed with status {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"[ERROR] Failed to send action '{action}': {e}")

    def rotate_left(self):
        self.send_action("rotate_left")

    def rotate_right(self):
        self.send_action("rotate_right")

    def thrust(self):
        self.send_action("thrust_forward")
    
    def reverse(self):
        self.send_action("thrust_backward")

    def basic_movement(self):
        self.send_action("rotate_right")
        self.send_action("thrust_forward")

    def check_boundary_proximity(self, position):
        """
        NOVO: Verifica proximidade às bordas usando limites do mapa
        """
        try:
            distance = self.world_model.get_distance_to_boundary(position)
            
            if distance < self.world_model.CRITICAL_MARGIN:
                return "critical", distance
            elif distance < self.world_model.DANGER_MARGIN:
                return "danger", distance
            elif distance < self.world_model.SAFE_ZONE_MARGIN:
                return "warning", distance
            else:
                return "safe", distance
        except:
            return "safe", 200  # Fallback se função não existe

    def detect_obstacle_or_border(self, scan, position):
        """
        Detecção melhorada de obstáculos e bordas
        """
        if not scan or "nearby_objects" not in scan:
            return False, None

        closest_threat = None
        min_distance = float('inf')

        # Verifica objetos do scan
        for obj in scan["nearby_objects"]:
            if obj["type"] in ["obstacle", "border"]:
                distance = obj["distance"]
                detection_limit = (self.border_detection_distance if obj["type"] == "border" 
                                 else self.obstacle_detection_distance)
                
                if distance < detection_limit and distance < min_distance:
                    min_distance = distance
                    closest_threat = {
                        "type": obj["type"],
                        "distance": distance,
                        "relative_position": obj["relative_position"]
                    }

        # NOVO: Verifica proximidade às bordas do mapa
        boundary_status, boundary_distance = self.check_boundary_proximity(position)
        
        if boundary_status in ["critical", "danger"] and boundary_distance < min_distance:
            closest_threat = {
                "type": "map_boundary",
                "distance": boundary_distance,
                "relative_position": None
            }

        return closest_threat is not None, closest_threat

    def proactive_boundary_prevention(self, position, orientation):
        """
        NOVO: Sistema de prevenção proativa - evita chegar às bordas
        """
        boundary_status, distance = self.check_boundary_proximity(position)
        
        if boundary_status == "critical":
            print(f"[PREVENTION] ZONA CRÍTICA! Distância: {distance:.1f} - Reorientando para centro")
            self.prevention_active = True
            
            # Calcula direção para o centro
            center = self.world_model.get_safe_center()
            dx = center[0] - position[0]
            dy = center[1] - position[1]
            angle_to_center = math.atan2(dy, dx)
            angle_diff = (angle_to_center - orientation + math.pi) % (2 * math.pi) - math.pi
            
            if abs(angle_diff) > 0.18:  # Ajuste moderado de 0.2 para 0.18
                if angle_diff > 0:
                    self.rotate_right()
                else:
                    self.rotate_left()
                return True
            else:
                self.thrust()
                return True
                
        elif boundary_status == "danger":
            # Verifica se movimento atual é perigoso
            future_x = position[0] + math.cos(orientation) * 30
            future_y = position[1] + math.sin(orientation) * 30
            future_status, _ = self.check_boundary_proximity([future_x, future_y])
            
            if future_status == "critical":
                print(f"[PREVENTION] Movimento perigoso detectado - reorientando")
                self.prevention_active = True
                
                # Encontra direção segura
                safe_direction = self.world_model.find_safe_direction(position, orientation)
                if safe_direction is not None:
                    angle_diff = (safe_direction - orientation + math.pi) % (2 * math.pi) - math.pi
                    if abs(angle_diff) > 0.3:
                        if angle_diff > 0:
                            self.rotate_right()
                        else:
                            self.rotate_left()
                        return True
                
        # Sai do modo prevenção se está seguro
        if boundary_status == "safe" and self.prevention_active:
            print(f"[PREVENTION] Saiu da zona de perigo - distância: {distance:.1f}")
            self.prevention_active = False
            
        return False

    def calculate_escape_direction(self, obstacle_info, position):
        """Calcula direção oposta ao obstáculo para escapar"""
        if obstacle_info.get('relative_position') is None:
            # Para map_boundary, calcula direção para o centro
            center = [0, 0]
            dx = center[0] - position[0]
            dy = center[1] - position[1]
            return math.atan2(dy, dx)
        
        rel_x, rel_y = obstacle_info['relative_position']
        # Direção OPOSTA ao obstáculo
        escape_angle = math.atan2(-rel_y, -rel_x)
        return escape_angle

    def calculate_angle_to_center(self, position, orientation):
        """Calcula ângulo para alinhar com o centro do mapa"""
        center = [0, 0]
        dx = center[0] - position[0]
        dy = center[1] - position[1]
        angle_to_center = math.atan2(dy, dx)
        angle_diff = (angle_to_center - orientation + math.pi) % (2 * math.pi) - math.pi
        return angle_to_center, angle_diff

    def is_aligned_with_center(self, position, orientation):
        """Verifica se está alinhado com o centro"""
        _, angle_diff = self.calculate_angle_to_center(position, orientation)
        return abs(angle_diff) < self.alignment_tolerance

    def execute_obstacle_avoidance(self, position, orientation, obstacle_info):
        """
        Executa sequência de evitamento em 4 fases
        """
        if self.avoidance_phase == "turn_away":
            print(f"[AVOIDANCE] TURN_AWAY - Virando costas ao {obstacle_info['type']} a {obstacle_info['distance']:.1f}px")
            
            escape_direction = self.calculate_escape_direction(obstacle_info, position)
            angle_diff = (escape_direction - orientation + math.pi) % (2 * math.pi) - math.pi
            
            if abs(angle_diff) < 0.14:  # Ligeiramente reduzido de 0.15 para 0.14
                print(f"[AVOIDANCE] Orientado para escapar, passando para MOVE_AWAY")
                self.avoidance_phase = "move_away"
                return
            
            if angle_diff > 0:
                self.rotate_right()
            else:
                self.rotate_left()
            
        elif self.avoidance_phase == "move_away":
            print(f"[AVOIDANCE] MOVE_AWAY - Fugindo do {obstacle_info['type']} a {obstacle_info['distance']:.1f}px")
            
            if obstacle_info['type'] == 'border' or obstacle_info['type'] == 'map_boundary':
                safe_distance = 150  # Maior distância para bordas
            else:
                safe_distance = 100
            
            if obstacle_info['distance'] > safe_distance:
                print(f"[AVOIDANCE] Distância segura alcançada, passando para ALIGN")
                self.avoidance_phase = "align"
                return
            
            # Verifica se ainda está orientado corretamente
            escape_direction = self.calculate_escape_direction(obstacle_info, position)
            angle_diff = (escape_direction - orientation + math.pi) % (2 * math.pi) - math.pi
            
            if abs(angle_diff) > 0.3:
                print(f"[AVOIDANCE] Perdeu orientação de escape, voltando para TURN_AWAY")
                self.avoidance_phase = "turn_away"
                return
            
            self.thrust()
            
        elif self.avoidance_phase == "align":
            print(f"[AVOIDANCE] ALIGN - Alinhando com centro")
            
            if self.is_aligned_with_center(position, orientation):
                print(f"[AVOIDANCE] Alinhado! Passando para MOVE_TO_CENTER")
                self.avoidance_phase = "move_to_center"
                return
            
            _, angle_diff = self.calculate_angle_to_center(position, orientation)
            
            if angle_diff > 0:
                self.rotate_right()
            else:
                self.rotate_left()
                
        elif self.avoidance_phase == "move_to_center":
            print(f"[AVOIDANCE] MOVE_TO_CENTER - Indo para centro")
            
            distance_to_center = math.sqrt(position[0]**2 + position[1]**2)
            boundary_status, _ = self.check_boundary_proximity(position)
            
            if distance_to_center < 60 or boundary_status == "safe":
                print(f"[AVOIDANCE] Chegou ao centro/zona segura! Saindo do modo evitamento")
                self.obstacle_avoidance_mode = False
                self.avoidance_phase = "turn_away"
                self.path = []
                return
            
            if not self.is_aligned_with_center(position, orientation):
                print(f"[AVOIDANCE] Perdeu alinhamento, voltando para ALIGN")
                self.avoidance_phase = "align"
                return
            
            self.thrust()

    def move_to_center(self, position, orientation):
        """
        NOVO: Função dedicada para movimento direto ao centro
        """
        center = [0, 0]
        distance_to_center = math.sqrt(position[0]**2 + position[1]**2)
        
        # Se já está próximo do centro, para
        if distance_to_center < self.center_tolerance:
            print(f"[CENTER] Chegou ao centro! Distância: {distance_to_center:.1f}")
            self.going_to_center = False
            return True
        
        # Calcula direção para o centro
        dx = center[0] - position[0]
        dy = center[1] - position[1]
        angle_to_center = math.atan2(dy, dx)
        angle_diff = (angle_to_center - orientation + math.pi) % (2 * math.pi) - math.pi
        
        # Se não está alinhado com o centro, roda
        if abs(angle_diff) > 0.12:  # Mais rápido - reduzido de 0.15 para 0.12
            print(f"[CENTER] Alinhando com centro - diferença: {angle_diff:.2f}")
            if angle_diff > 0:
                self.rotate_right()
            else:
                self.rotate_left()
        else:
            # Verifica se é seguro mover-se na direção do centro
            future_x = position[0] + math.cos(orientation) * 20
            future_y = position[1] + math.sin(orientation) * 20
            future_status, _ = self.check_boundary_proximity([future_x, future_y])
            
            if future_status not in ["critical"]:
                print(f"[CENTER] Avançando para centro - distância: {distance_to_center:.1f}")
                self.thrust()
            else:
                print(f"[CENTER] Movimento perigoso detectado, pausando")
        
        return False

    def run(self):
        if not self.connect():
            return

        self.ready_up()
        print("[INFO] Smart agent with safe strategy running...")

        try:
            while True:
                scan = self.get_scan()
                self_state = self.get_self_state()

                if not scan or "nearby_objects" not in scan or not self_state:
                    time.sleep(0.1)
                    continue

                # Atualiza o modelo do mundo
                self.world_model.update_pose(self_state)
                self.world_model.update_from_scan(scan)

                position = self_state.get("position") or self_state.get("pos") or [0, 0]
                orientation = self_state.get("orientation") or self_state.get("angle") or 0

                # NOVO: Atualiza tracking de inimigos E memória de obstáculos
                self.update_enemy_tracking(scan)
                if hasattr(self, 'known_obstacles'):
                    self.update_obstacle_memory(scan, position)

                # PRIORIDADE 1: COMBATE - Se deteta inimigo próximo, SEMPRE persegue e atira
                enemy_detected = False
                for obj in scan.get("nearby_objects", []):
                    if obj["type"] == "other_player":
                        rel_x, rel_y = obj["relative_position"]
                        distance = obj["distance"]
                        angle_to_enemy = math.atan2(rel_y, rel_x)
                        angle_diff = (angle_to_enemy - orientation + math.pi) % (2 * math.pi) - math.pi
                        
                        enemy_detected = True
                        self.going_to_center = False  # Para movimento para o centro se encontra inimigo
                        self.search_mode = False     # Para busca ativa
                        print(f"[COMBAT] Inimigo detectado a {distance:.1f}px, ângulo: {angle_to_enemy:.2f}")
                        
                        # TIRO IMEDIATO se alinhado (mais generoso)
                        if abs(angle_to_enemy) < 0.35:  # Aumentado de 0.3 para 0.35 (atira ainda mais facilmente)
                            now = time.time()
                            if now - self.last_shot_time > self.shot_cooldown:
                                print("[COMBAT] ALINHADO! DISPARAR!")
                                self.send_action("shoot")
                                self.last_shot_time = now
                        
                        # PERSEGUIÇÃO DIRETA mais rápida
                        if abs(angle_diff) > 0.12:  # Mais rápido - reduzido de 0.15 para 0.12
                            if angle_diff > 0:
                                self.rotate_right()
                            else:
                                self.rotate_left()
                            print(f"[COMBAT] Rodando rápido para inimigo - diferença: {angle_diff:.2f}")
                        else:
                            # Se inimigo está longe, aproxima-se mais agressivamente
                            if distance > 30:  # Reduzido de 35 para 30 (ainda mais agressivo)
                                # NOVO: Usa navegação inteligente se há obstáculos conhecidos
                                enemy_pos = [position[0] + rel_x, position[1] + rel_y]
                                
                                if (self.known_obstacles and 
                                    self.intelligent_obstacle_navigation(position, orientation, enemy_pos)):
                                    print(f"[COMBAT] Navegação inteligente para inimigo")
                                else:
                                    # Navegação direta tradicional
                                    future_x = position[0] + math.cos(orientation) * 20
                                    future_y = position[1] + math.sin(orientation) * 20
                                    future_distance = self.world_model.get_distance_to_boundary([future_x, future_y])
                                    
                                    if future_distance > 35:  # Reduzido de 40 para 35 (ainda mais agressivo)
                                        self.thrust()
                                        print(f"[COMBAT] Perseguindo inimigo diretamente")
                                    else:
                                        print(f"[COMBAT] Movimento muito perigoso, só atirando")
                            else:
                                print(f"[COMBAT] Inimigo próximo, mantendo posição e atirando")
                        
                        break  # Só processa o primeiro inimigo
                
                # PRIORIDADE 2: Sistema de prevenção (só se NÃO há inimigo próximo)
                if not enemy_detected and self.proactive_boundary_prevention(position, orientation):
                    time.sleep(0.02)  # Mais rápido - reduzido de 0.03 para 0.02
                    continue

                # PRIORIDADE 3: Sistema de evitamento de obstáculos (só se NÃO há inimigo próximo)
                if not enemy_detected:
                    has_obstacle, obstacle_info = self.detect_obstacle_or_border(scan, position)
                    
                    if has_obstacle or self.obstacle_avoidance_mode:
                        if not self.obstacle_avoidance_mode:
                            print(f"[AVOIDANCE] ATIVADO! Detectado: {obstacle_info}")
                            self.obstacle_avoidance_mode = True
                            self.avoidance_start_time = time.time()
                            self.avoidance_phase = "turn_away"
                            self.path = []
                            self.going_to_center = False  # Para movimento para centro
                            self.search_mode = False     # Para busca ativa
                        
                        self.execute_obstacle_avoidance(position, orientation, obstacle_info or 
                                                       {"type": "unknown", "distance": 50, "relative_position": None})
                        
                        if time.time() - self.avoidance_start_time > 4:  # Mais rápido - reduzido de 6 para 4 segundos
                            print("[AVOIDANCE] TIMEOUT! Forçando saída")
                            self.obstacle_avoidance_mode = False
                            self.avoidance_phase = "turn_away"
                            # Limpa variáveis auxiliares
                            if hasattr(self, 'turn_direction'):
                                delattr(self, 'turn_direction')
                            if hasattr(self, 'turn_count'):
                                delattr(self, 'turn_count')
                        
                        time.sleep(0.015)  # Mais rápido - reduzido de 0.02 para 0.015
                        continue

                # PRIORIDADE 4: BUSCA ATIVA DE INIMIGOS (se não viu inimigo há tempo)
                if not enemy_detected and self.active_enemy_search(position, orientation):
                    time.sleep(0.015)  # Busca ativa mais rápida
                    continue

                # PRIORIDADE 5: IR PARA O CENTRO com navegação inteligente
                if not enemy_detected and not self.search_mode:
                    # Ativa movimento para o centro se não estava ativo
                    if not self.going_to_center:
                        print("[CENTER] Nenhum inimigo detectado - indo para o centro do mapa")
                        self.going_to_center = True
                        self.path = []  # Limpa qualquer caminho anterior
                    
                    # NOVO: Tenta usar navegação inteligente para o centro
                    center_pos = [0, 0]
                    if (hasattr(self, 'known_obstacles') and self.known_obstacles and 
                        hasattr(self, 'intelligent_obstacle_navigation') and
                        self.intelligent_obstacle_navigation(position, orientation, center_pos)):
                        print("[CENTER] Navegação inteligente para centro entre obstáculos")
                        time.sleep(0.015)
                        continue
                    
                    # Executa movimento tradicional para o centro
                    if self.move_to_center(position, orientation):
                        # Se chegou ao centro, fica parado ou faz patrulhamento
                        print("[CENTER] No centro do mapa, aguardando inimigos...")
                        time.sleep(0.04)  # Mais rápido - reduzido de 0.05 para 0.04
                        continue

                time.sleep(0.015)  # Loop principal ainda mais rápido - reduzido de 0.02 para 0.015 PRIORIDADE 4: BUSCA ATIVA DE INIMIGOS (se não viu inimigo há tempo)
                if not enemy_detected and self.active_enemy_search(position, orientation):
                    time.sleep(0.02)  # Busca ativa rápida
                    continue

                # PRIORIDADE 5: IR PARA O CENTRO (só se NÃO há inimigo próximo E não está buscando)
                if not enemy_detected and not self.search_mode:
                    # Ativa movimento para o centro se não estava ativo
                    if not self.going_to_center:
                        print("[CENTER] Nenhum inimigo detectado - indo para o centro do mapa")
                        self.going_to_center = True
                        self.path = []  # Limpa qualquer caminho anterior
                    
                    # Executa movimento para o centro
                    if self.move_to_center(position, orientation):
                        # Se chegou ao centro, fica parado ou faz patrulhamento
                        print("[CENTER] No centro do mapa, aguardando inimigos...")
                        time.sleep(0.05)  # Mais rápido - reduzido de 0.08 para 0.05
                        continue

                time.sleep(0.02)  # Loop principal mais rápido - reduzido de 0.03 para 0.02

        except KeyboardInterrupt:
            print("\n[INFO] Agent stopped by user")
        except Exception as e:
            print(f"[ERROR] Unexpected error in main loop: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    agent = SmartAgent()
    agent.run()