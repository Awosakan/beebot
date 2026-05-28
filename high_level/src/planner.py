import math
import logging
from .astar import AStarPlanner

logger = logging.getLogger("IDA_Planner")
logger.setLevel(logging.INFO)

def gps_to_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> tuple:
    """
    WGS-84 referans elipsoidi kullanılarak iki GPS koordinatı arasındaki mesafeyi (Haversine Formülü) 
    ve yönelimini (Bearing) hesaplayıp, x (Doğu) ve y (Kuzey) eksenlerindeki ayrıma (dx, dy) dönüştürür.
    Bu yöntem uzun mesafelerde ve karmaşık hesaplamalarda düz dünya (Equirectangular) yaklaşımından çok daha kesindir.
    """
    R = 6378137.0 # Dünya yarıçapı (metre)
    
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    # Haversine Formülü ile Kesin Mesafe (Great-circle distance)
    a = math.sin(dphi / 2.0)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0)**2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    dist = R * c

    # Yönelim (Forward Bearing)
    y = math.sin(dlambda) * math.cos(phi2)
    x = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(dlambda)
    bearing = math.atan2(y, x)

    # dx (Doğu yönü mesafe), dy (Kuzey yönü mesafe)
    dx = dist * math.sin(bearing)
    dy = dist * math.cos(bearing)
    
    return dx, dy

class APFPlanner:
    """
    Yapay Potansiyel Alanlar (Artificial Potential Field) rota planlayıcı.
    Hedefe doğru çekici kuvvet (attractive), engellerden zıt yönde itici kuvvet (repulsive) üretir.
    Akıntı sürüklenmesine karşı enine sapma entegral (Cross-Track Error Integral) terimini içerir (Senaryo 4).
    """
    def __init__(self, waypoint_tolerance_m: float = 2.5, 
                 nominal_speed_ms: float = 1.5, 
                 max_speed_ms: float = 2.5,
                 min_speed_ms: float = 0.5):
        
        self.waypoint_tolerance_m = waypoint_tolerance_m
        self.nominal_speed_ms = nominal_speed_ms
        self.max_speed_ms = max_speed_ms
        self.min_speed_ms = min_speed_ms
        
        # Çekici ve itici kuvvet katsayıları
        self.K_attractive = 2.0
        
        # --- Akıntı ve Rüzgar Sapma Düzeltmesi (Cross-Track Error) ---
        self.K_cte_i = 0.05       # CTE Entegral kazancı (sürüklenme düzeltmesi)
        self.cte_integrator = 0.0 # Birikmiş sürüklenme hatası
        self.max_cte_i = 1.5     # Maksimum düzeltme doyumu (windup engelleme)

        # --- Rota Yön Yumuşatma Filtresi (EMA) ---
        self.last_target_heading = None
        self.heading_ema_alpha = 0.25 # Açısal yumuşatma katsayısı (0.25 = düşük geçiren filtre)

        # --- GPS Gürültü Filtresi (Ucuz GPS sapmaları için dairesel tampon) ---
        self.gps_history_lat = []
        self.gps_history_lon = []
        self.gps_filter_size = 5

        # --- A* Global Planlayıcı (Görev 2) ---
        self.astar = AStarPlanner(resolution=0.25)

    def plan(self, current_lat: float, current_lon: float, current_yaw_deg: float, current_speed: float,
             waypoints: list, current_wp_idx: int, costmap, prev_wp_gps: list = None, dt: float = 0.04) -> tuple:
        """
        Rota ve hız planlaması yapar.
        """
        if not waypoints or current_wp_idx >= len(waypoints):
            return 0.0, current_yaw_deg, current_wp_idx, True
            
        # Ucuz GPS gürültüsünü sönümlemek için konum verisini hareketli ortalamayla filtrele
        # 15 karelik pencere (yaklaşık 0.6 sn) 2 metrelik ani sapmaları çok daha iyi emer
        if not hasattr(self, 'filtered_lat_ema'):
            self.filtered_lat_ema = current_lat
            self.filtered_lon_ema = current_lon
            self.gps_filter_size = 15
            
        self.gps_history_lat.append(current_lat)
        self.gps_history_lon.append(current_lon)
        if len(self.gps_history_lat) > self.gps_filter_size:
            self.gps_history_lat.pop(0)
            self.gps_history_lon.pop(0)
            
        avg_lat = sum(self.gps_history_lat) / len(self.gps_history_lat)
        avg_lon = sum(self.gps_history_lon) / len(self.gps_history_lon)
        
        # EMA + Hareketli Ortalama hibrit filtre (Gürültüyü çok iyi keser)
        alpha_gps = 0.3
        self.filtered_lat_ema = alpha_gps * avg_lat + (1 - alpha_gps) * self.filtered_lat_ema
        self.filtered_lon_ema = alpha_gps * avg_lon + (1 - alpha_gps) * self.filtered_lon_ema
        
        filtered_lat = self.filtered_lat_ema
        filtered_lon = self.filtered_lon_ema

        target_lat, target_lon = waypoints[current_wp_idx]
        
        # 1. Hedef noktaya olan mesafeyi ve bağıl konumu metre cinsinden hesapla
        dx_m, dy_m = gps_to_meters(filtered_lat, filtered_lon, target_lat, target_lon)
        dist_to_wp = math.sqrt(dx_m**2 + dy_m**2)

        # Rota hedefinin costmap üzerindeki hücresinin maliyetini kontrol et (Görev 108)
        # Hedefin İDA'ya göre bağıl body-frame koordinatlarını hesapla (Görev 2.6 ile uyumlu)
        yaw_rad = math.radians(current_yaw_deg)
        x_body_raw = dx_m * math.sin(yaw_rad) + dy_m * math.cos(yaw_rad)
        y_body_raw = dx_m * math.cos(yaw_rad) - dy_m * math.sin(yaw_rad)
        
        wp_row = costmap.center_idx - int(x_body_raw / costmap.resolution) if hasattr(costmap, "center_idx") else -1
        wp_col = costmap.center_idx + int(y_body_raw / costmap.resolution) if hasattr(costmap, "center_idx") else -1
        
        # --- A* Global Path Planning (Görev 2) ---
        if hasattr(costmap, "grid_obstacles") and 0 <= wp_row < costmap.grid_size and 0 <= wp_col < costmap.grid_size:
            # A* ile geçici bir havuç (carrot) hedefi belirle
            path = self.astar.plan((costmap.center_idx, costmap.center_idx), (wp_row, wp_col), costmap.grid_obstacles)
            if path and len(path) > 2:
                # Yaklaşık 2.0 metre ileriye (8 hücre) bakan bir nokta seç
                lookahead_idx = min(len(path)-1, int(2.0 / costmap.resolution))
                carrot_row, carrot_col = path[lookahead_idx]
                
                # Havuç hedefini Body-Frame koordinatlarına çevir
                carrot_x_body = (costmap.center_idx - carrot_row) * costmap.resolution
                carrot_y_body = (carrot_col - costmap.center_idx) * costmap.resolution
                
                # Hedefin (dx_m, dy_m) değerlerini havuç değerleriyle ez (Dünya koordinatlarına geri dönüştürerek)
                # Böylece APF çekici kuvveti doğrudan engelsiz rotaya yönelecek. CTE mantığı etkilenmez.
                dx_m = carrot_x_body * math.sin(yaw_rad) + carrot_y_body * math.cos(yaw_rad)
                dy_m = carrot_x_body * math.cos(yaw_rad) - carrot_y_body * math.sin(yaw_rad)
        
        active_tolerance = self.waypoint_tolerance_m
        if hasattr(costmap, "grid_obstacles") and 0 <= wp_row < costmap.grid_size and 0 <= wp_col < costmap.grid_size:
            wp_cost = costmap.grid_obstacles[wp_row, wp_col]
            if wp_cost > 45: # Hedef duba/engel üzerinde veya çok yakınında
                active_tolerance = max(active_tolerance, 2.2) # Toleransı 2.2 metreye genişlet
                logger.warning(f"Hedef yol noktası ({target_lat}, {target_lon}) sarı engel bölgesinde (maliyet={wp_cost})! Geçiş toleransı {active_tolerance:.1f}m yapıldı.")

        # Noktaya ulaşıldı mı kontrolü
        reached = False
        if dist_to_wp < 0.6:  # Güvenli yakınlık yedek kontrolü
            logger.info(f"Waypoint {current_wp_idx} çok yakın toleransla ulaşıldı! Bir sonraki noktaya geçiliyor.")
            reached = True
        elif prev_wp_gps:
            # Geçiş düzlemi kontrolü (perpendicular plane crossing):
            # İki waypoint arasındaki rota çizgisine göre hedefin geçilip geçilmediğini kontrol eder.
            # Böylece kapılardan geçişte erken dönüp kapıyı kaçırma (corner cutting) engellenir.
            line_dx, line_dy = gps_to_meters(prev_wp_gps[0], prev_wp_gps[1], target_lat, target_lon)
            line_len = math.sqrt(line_dx**2 + line_dy**2)
            if line_len > 1.0:
                u_x = line_dx / line_len
                u_y = line_dy / line_len
                boat_dx, boat_dy = gps_to_meters(prev_wp_gps[0], prev_wp_gps[1], filtered_lat, filtered_lon)
                along_track = boat_dx * u_x + boat_dy * u_y
                
                # Enine sapma mesafesi (Cross-Track Error)
                cte = boat_dx * (-u_y) + boat_dy * u_x
                
                # Kapı çizgisini / dikey düzlemi geçtik mi? 
                # Yanal sapmalarda sonsuz döngüyü önlemek için along-track kontrolü.
                # Ancak yanal sapmanın çok büyük olmaması (abs(cte) < 4.0) gerekir (Görev 7).
                if along_track >= line_len and abs(cte) < 4.0:
                    logger.info(f"Waypoint {current_wp_idx} geçiş düzlemi (along-track={along_track:.2f}m >= limit={line_len:.2f}m, yanal={cte:.2f}m) üzerinden başarıyla ulaşıldı!")
                    reached = True
                    
        # Hiçbir referans yoksa veya fallback olarak normal/aktif toleransı kullan
        if not reached and dist_to_wp < active_tolerance:
            logger.info(f"Waypoint {current_wp_idx} standart tolerans ({dist_to_wp:.2f}m < {active_tolerance:.1f}m) ile ulaşıldı!")
            reached = True
            
        if reached:
            current_wp_idx += 1
            self.cte_integrator = 0.0 # Yeni hedef noktada sürüklenme entegralini sıfırla
            self.last_target_heading = None
            return self.min_speed_ms, current_yaw_deg, current_wp_idx, (current_wp_idx >= len(waypoints))

        # 2. [Senaryo 4 Önlemi]: Enine Sapma (Cross-Track Error) Hesaplama ve Entegral Düzeltmesi
        # İki nokta arasındaki ideal rota çizgisine olan dikey sapmayı hesaplar.
        cte_offset_x = 0.0
        cte_offset_y = 0.0
        
        if prev_wp_gps:
            # Önceki WP ile hedef WP arasındaki rota hattı vektörü (Metre cinsinden)
            line_dx, line_dy = gps_to_meters(prev_wp_gps[0], prev_wp_gps[1], target_lat, target_lon)
            line_len = math.sqrt(line_dx**2 + line_dy**2)
            
            if line_len > 1.0:
                # İdeal rota hattının birim vektörü
                u_x = line_dx / line_len
                u_y = line_dy / line_len
                
                # Botun önceki WP'ye göre bağıl konumu (Metre)
                boat_dx, boat_dy = gps_to_meters(prev_wp_gps[0], prev_wp_gps[1], filtered_lat, filtered_lon)
                
                # Enine sapma mesafesi (Cross-Track Error) - Rota hattına dik olan mesafe
                # Vektörel çarpım (2D cross product): boat_vector x line_unit_vector
                cte = boat_dx * (-u_y) + boat_dy * u_x
                
                # Rota çizgisi ortasından geçişte (sign change) integral birikimini sıfırla veya sönümle 
                # (Over-shooting ve salınımı engellemek için - Görev 85 & 136)
                if (cte > 0.0 and self.cte_integrator < 0.0) or (cte < 0.0 and self.cte_integrator > 0.0):
                    self.cte_integrator *= 0.25 # Hızlı sönümleme
                
                # Enine sapma yönünde entegral düzeltme biriktir (dinamik dt kullanılır)
                self.cte_integrator += cte * dt
                # Anti-windup koruması (Limit 1.5m)
                self.cte_integrator = max(-self.max_cte_i, min(self.cte_integrator, self.max_cte_i))
                
                # İntegral düzeltme ile akıntı sürüklenmesini kararlı şekilde düzelt
                cte_correction = self.cte_integrator * self.K_cte_i
                
                # Düzeltme yönü ideal rotaya çekmek için hattın dik birim vektörüdür (Sürüklenmenin tersi)
                cte_offset_x = (u_y) * cte_correction
                cte_offset_y = (-u_x) * cte_correction

        # 3. IvP-Lite: Eylem Uzayı Fayda Koordinatörü (Behavior-Based Utility Coordinator)
        # APF kuvvetlerinin birbirini sönümlemesi ve local minima kilitlerini önler.
        yaw_rad = math.radians(current_yaw_deg)
        
        # Hedef koordinata göre yönelim ve mesafe (CTE düzeltmesi eklenmiş)
        total_dx = dx_m + cte_offset_x
        total_dy = dy_m + cte_offset_y
        
        # Hedef yönü (bearing) dünya koordinatlarında
        target_bearing_deg = math.degrees(math.atan2(total_dx, total_dy)) % 360.0
        
        # Sağ tarafın engel durumu (sancak koruması için)
        right_blocked = False
        if hasattr(costmap, "is_right_blocked"):
            right_blocked = costmap.is_right_blocked()
            
        # Potansiyel alan itme kuvvetlerini (corridor yanal düzeltmesi vb.) çek
        rep_x = 0.0
        rep_y = 0.0
        if hasattr(costmap, "get_obstacle_forces"):
            rep_x, rep_y = costmap.get_obstacle_forces()

        # Açısal eylem adayları (tekneye göre bağıl açılar: -45° ile +45° arası, 5'er derece adımlarla)
        steer_candidates = [float(a) for a in range(-45, 46, 5)]
            
        best_steer_deg = 0.0
        max_utility = -999999.0
        
        # Ön bölgede engel yoğunluğu kontrolü (COLREGs için)
        front_obstacle_detected = False
        if hasattr(costmap, "grid") and hasattr(costmap, "center_idx"):
            for dr in range(-8, 1): # İleriye doğru 2.0 metre
                for dc in range(-2, 3): # Genişlik olarak 1.0 metre
                    row = costmap.center_idx + dr
                    col = costmap.center_idx + dc
                    if 0 <= row < costmap.grid_size and 0 <= col < costmap.grid_size:
                        if costmap.grid[row, col] > 35:
                            front_obstacle_detected = True
                            break
                if front_obstacle_detected:
                    break

        for steer_deg in steer_candidates:
            steer_rad = math.radians(steer_deg)
            candidate_yaw_deg = (current_yaw_deg + steer_deg) % 360.0
            
            # --- Davranış 1: Hedefe Yönelme / Çekicilik (Waypoint Attraction) ---
            diff_wp = target_bearing_deg - candidate_yaw_deg
            while diff_wp > 180.0: diff_wp -= 360.0
            while diff_wp < -180.0: diff_wp += 360.0
            u_wp = math.cos(math.radians(diff_wp)) # [-1.0, 1.0] aralığında
            
            # --- Davranış 2: Engelden Kaçınma (Obstacle Avoidance / Ray-Casting) ---
            # Aday yönde 5.5 metreye kadar ışın gönderip maliyetleri sorgula
            max_penalty = 0.0
            hard_collision = False
            
            if hasattr(costmap, "grid") and hasattr(costmap, "center_idx"):
                # 0.5m ile 5.0m arasında 10 noktada örnekleme yap
                for d in [0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0]:
                    # Tekneye göre bağıl gövde koordinatı (x_body = ileri, y_body = sağ)
                    px = d * math.cos(steer_rad)
                    py = d * math.sin(steer_rad)
                    
                    row = costmap.center_idx - int(px / costmap.resolution)
                    col = costmap.center_idx + int(py / costmap.resolution)
                    
                    if 0 <= row < costmap.grid_size and 0 <= col < costmap.grid_size:
                        cost = costmap.grid[row, col]
                        if cost > 40:
                            # Yakın mesafedeki (<= 2.2m) yüksek maliyetler doğrudan çarpışma kabul edilir
                            if d <= 2.2:
                                hard_collision = True
                            
                            # Yakındaki engellere daha yüksek ceza puanı ver
                            penalty = (cost / 100.0) * (6.0 - d) / 5.0
                            max_penalty = max(max_penalty, penalty)
            
            if hard_collision:
                u_obs = -100.0  # Güvenlik ihlali: Bu yöne gidiş engellenir
            else:
                u_obs = 1.0 - min(1.0, max_penalty)
                
            # --- Davranış 3: Rota Pürüzsüzlüğü (Smoothness) ---
            if self.last_target_heading is not None:
                diff_smooth = candidate_yaw_deg - self.last_target_heading
                while diff_smooth > 180.0: diff_smooth -= 360.0
                while diff_smooth < -180.0: diff_smooth += 360.0
                u_smooth = math.cos(math.radians(diff_smooth))
            else:
                u_smooth = 1.0
                
            # --- Davranış 4: COLREGs Sağa Kaçış Tercihi (Sancak Geçişi) ---
            u_colregs = 0.0
            if front_obstacle_detected and not right_blocked:
                # Sancak yönüne (steer_deg > 0) dönüşe hafif bir avantaj sağla, iskeleye dönüşü cezalandır
                if steer_deg > 0.0:
                    u_colregs = 0.20 * math.sin(steer_rad)
                elif steer_deg < 0.0:
                    u_colregs = -0.20 * abs(math.sin(steer_rad))
                    
            # --- Davranış 5: Potansiyel Alan Kuvvet Alanı Uyumu (Force Field Alignment) ---
            # costmap.get_obstacle_forces() tarafından sağlanan koridor yanal düzeltmesi,
            # COLREGs bükümü vb. kuvvetleri eylem uzayına aktarır.
            u_force = 0.0
            rep_mag = math.sqrt(rep_x**2 + rep_y**2)
            if rep_mag > 0.001:
                # İtici kuvvetin büyüklüğünü [-2.5, 2.5] ile ölçeklendirerek etkiyi dengede tut
                scale = min(2.5, rep_mag) / rep_mag
                u_force = (rep_x * scale) * math.cos(steer_rad) + (rep_y * scale) * math.sin(steer_rad)
                
            # Ağırlıklandırılmış toplam fayda değeri
            # Engel önleme ağırlığı (4.0), hedef takibi ağırlığı (2.0) ve kuvvet alanı uyumu (1.0) dengelenmiştir
            utility = 2.0 * u_wp + 4.0 * u_obs + 0.5 * u_smooth + u_colregs + 1.0 * u_force
            
            if utility > max_utility:
                max_utility = utility
                best_steer_deg = steer_deg

        # Hedef yönelimi belirle
        target_heading_deg = (current_yaw_deg + best_steer_deg) % 360.0
        
        # Yönelim filtresini güncelle (EMA)
        if self.last_target_heading is None:
            self.last_target_heading = target_heading_deg
        else:
            diff = target_heading_deg - self.last_target_heading
            while diff > 180.0: diff -= 360.0
            while diff < -180.0: diff += 360.0
            self.last_target_heading = (self.last_target_heading + self.heading_ema_alpha * diff) % 360.0
            target_heading_deg = self.last_target_heading

        # Hız Planlaması (Keskin dönüşlerde savrulmayı ve akıntı etkisini önlemek için)
        best_steer_rad = math.radians(best_steer_deg)
        angle_factor = math.cos(best_steer_rad)
        
        # Geri Vites (Reverse) Kararı:
        # Eğer önümüzde (0 derece ışınında) çok yakın ve büyük bir engel varsa geriye itki uygula
        front_cost = 0
        if hasattr(costmap, "grid") and hasattr(costmap, "center_idx"):
            for d in [1.0, 1.5]:
                row = costmap.center_idx - int(d / costmap.resolution)
                col = costmap.center_idx
                if 0 <= row < costmap.grid_size and 0 <= col < costmap.grid_size:
                    front_cost = max(front_cost, costmap.grid[row, col])
                    
        if front_cost > 55:
            # Geri git (nominal hızın negatif bir yüzdesi)
            target_speed = -0.6 * self.nominal_speed_ms
        else:
            if angle_factor < 0:
                # Keskin dönüşlerde tekneyi steerage-way limitinde yavaşlat (min hızı koru)
                target_speed = max(self.min_speed_ms, 0.65)
            else:
                target_speed = self.nominal_speed_ms * (angle_factor ** 2)
                if dist_to_wp < 5.0:
                    # Hedefe yaklaşırken yavaşlama rampası
                    target_speed = min(target_speed, 0.5 + 0.2 * dist_to_wp)
                    
            # Nominal limitler arasına sıkıştır
            target_speed = max(self.min_speed_ms, min(target_speed, self.max_speed_ms))
            
            # Eğer rotada hiç engel yoksa ve hedef uzaksa tam hıza çık
            if not front_obstacle_detected and dist_to_wp > 8.0:
                target_speed = self.nominal_speed_ms * max(self.min_speed_ms / self.nominal_speed_ms, angle_factor)
                target_speed = max(self.min_speed_ms, min(target_speed, self.max_speed_ms))

        return target_speed, target_heading_deg, current_wp_idx, False
