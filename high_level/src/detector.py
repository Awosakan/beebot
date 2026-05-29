import cv2
import numpy as np
import logging
import math

logger = logging.getLogger("IDA_Detector")
logger.setLevel(logging.INFO)

class BuoyDetector:
    """
    Duba algılama ve konum kestirim sınıfı.
    YOLO ONNX ve HSV Renk Eşikleme olmak üzere çift kanallı yedekli çalışır (F-35 Failsafe standardı).
    """
    def __init__(self, model_path: str = None, 
                 config_path: str = None,
                 image_width: int = 640, 
                 image_height: int = 480,
                 hfov: float = 80.0,  # Derece cinsinden Yatay Görüş Açısı (Horizontal Field of View)
                 conf_threshold: float = 0.35,
                 nms_threshold: float = 0.6,
                 classes_dict: dict = None,
                 roi_ymin_ratio: float = 0.3,
                 roi_ymax_ratio: float = 0.8,
                 hsv_min_pixel_ratio: float = 0.05):
        
        self.image_width = image_width
        self.image_height = image_height
        self.conf_threshold = conf_threshold
        self.nms_threshold = nms_threshold
        self.roi_ymin_ratio = roi_ymin_ratio
        self.roi_ymax_ratio = roi_ymax_ratio
        self.hsv_min_pixel_ratio = hsv_min_pixel_ratio
        
        # Kamera Parametreleri (Odak Uzaklığı - Focal Length Hesaplama)
        self.hfov_rad = math.radians(hfov)
        self.focal_length_px = (self.image_width / 2.0) / math.tan(self.hfov_rad / 2.0)
        
        # Fiziksel Duba Boyutları (Şartnameye göre çapı 30 cm = 0.3 metre)
        self.BUOY_REAL_WIDTH_M = 0.30 
        
        # Sınıflar (YOLO ve Renk Filtrelemede Ortak)
        self.classes = {
            0: "orange_gate",      # Şartname Turuncu Duba (RAL 2003)
            1: "yellow_obstacle",  # Şartname Sarı Duba (RAL 1026)
            2: "target_red",       # Parkur 3 Kamikaze Hedef Kırmızı
            3: "target_green",     # Parkur 3 Kamikaze Hedef Yeşil
            4: "target_blue"       # Parkur 3 Kamikaze Hedef Mavi
        }
        if classes_dict:
            try:
                self.classes = {int(k): v for k, v in classes_dict.items()}
            except Exception as e:
                logger.error(f"Sınıf eşlemeleri yüklenirken hata: {e}")
        
        # Model Yükleme
        self.net = None
        self.use_fallback = True
        
        if model_path:
            try:
                # Dosyaları ikili modda okuyarak bellekten yükle (Windows Türkçe karakter/Şahakan yol hatası çözümü)
                with open(model_path, "rb") as f:
                    model_bytes = f.read()
                model_buffer = np.frombuffer(model_bytes, dtype=np.uint8)
                
                if config_path and config_path.endswith(".pbtxt"):
                    with open(config_path, "rb") as f:
                        config_bytes = f.read()
                    config_buffer = np.frombuffer(config_bytes, dtype=np.uint8)
                    self.net = cv2.dnn.readNetFromTensorflow(model_buffer, config_buffer)
                else:
                    try:
                        self.net = cv2.dnn.readNetFromONNX(model_buffer)
                    except Exception:
                        self.net = cv2.dnn.readNet(model_path)
                
                self.net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
                
                # [GPU Hızlandırma Optimizasyonu]: Adreno 630 GPU üzerinde OpenCL veya Vulkan ile çalıştır
                try:
                    self.net.setPreferableTarget(cv2.dnn.DNN_TARGET_OPENCL)
                    logger.info("Performans Optimizasyonu: MobileNet-SSD Çıkarımı GPU (OpenCL) üzerine yönlendirildi.")
                except Exception:
                    try:
                        self.net.setPreferableTarget(cv2.dnn.DNN_TARGET_VULKAN)
                        logger.info("Performans Optimizasyonu: MobileNet-SSD Çıkarımı GPU (Vulkan) üzerine yönlendirildi.")
                    except Exception:
                        self.net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
                        logger.info("Performans Optimizasyonu: GPU hedef atanamadı, çıkarım CPU (ARM NEON) üzerinde yapılacak.")
                
                self.use_fallback = False
                logger.info(f"MobileNet-SSD modeli bellekten başarıyla yüklendi: {model_path}")
            except Exception as e:
                logger.error(f"MobileNet-SSD modeli yüklenemedi: {e}. HSV Renk Filtreleme moduna geçiliyor.")
                self.use_fallback = True
        else:
            logger.info("Model dosyası belirtilmedi. HSV Renk Filtreleme modunda çalışılıyor.")
            self.use_fallback = True

        # --- Gelişmiş Emniyet Filtreleri (Suda 10 Kötü Senaryo Önlemleri) ---
        # Senaryo 5 (Su Sıçraması / Kamera Kapanması) Kontrolü
        self.frame_count = 0
        self.camera_blocked = False
        
        # Görev 1.1 & 1.4: Çoklu duba takibi ve Jitter yumuşatma için Centroid Tracker veri yapıları
        self.next_track_id = 0
        self.tracks = []  # Aktif izler listesi
        self.filter_alpha = 0.35  # Jitter filtreleme EMA ağırlığı (0.0: tam sönümleme, 1.0: filtre yok)

    def check_lens_obstruction(self, frame) -> bool:
        """
        [Kötü Senaryo 5]: Merceğe su gelmesi veya kameranın tamamen kapanması durumunu kontrol eder.
        Görüntüdeki renk varyansını (kontrastı) ve ortalama parlaklığı ölçer.
        """
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        mean_brightness = np.mean(gray)
        std_deviation = np.std(gray)
        
        # Lens kapandıysa veya su damlasından dolayı görüntü aşırı bulanıklaştıysa standart sapma çok düşer.
        if std_deviation < 5.0 or mean_brightness < 8.0:
            if not self.camera_blocked:
                logger.warning(f"ACİL DURUM: Kamera merceği kapandı veya su sıçradı! Kontrast: {std_deviation:.1f}, Parlaklık: {mean_brightness:.1f}")
                self.camera_blocked = True
            return True
            
        self.camera_blocked = False
        return False

    def temporal_filter(self, raw_detections: list) -> list:
        """
        [Kötü Senaryo 6 & Görev 1.1 & 1.4 & 1.2]: Çoklu nesne takibi (Centroid Tracking),
        jitter yumuşatma filtresi (EMA) ve ekran kenarı kesilme telafisi.
        """
        confirmed_detections = []
        matched_track_indices = set()
        matched_det_indices = set()
        
        # 1. Mevcut izler ile yeni tespitleri eşleştirmeye çalış
        matches = []
        for det_idx, det in enumerate(raw_detections):
            cls = det["class"]
            dist = det["distance"]
            bearing = det["bearing"]
            
            # Kartezyen koordinatlar (İDA referanslı)
            x_det = dist * math.sin(bearing)
            y_det = dist * math.cos(bearing)
            
            for track_idx, track in enumerate(self.tracks):
                if track["class"] != cls:
                    continue
                
                # İz geçmişindeki son konum
                last_dist, last_bearing = track["history"][-1]
                x_track = last_dist * math.sin(last_bearing)
                y_track = last_dist * math.cos(last_bearing)
                
                # Öklid mesafesi
                distance_m = math.sqrt((x_det - x_track)**2 + (y_det - y_track)**2)
                
                # Eşleşme limitleri: 3.0 metre ve 20 derece açı sınırı
                if distance_m < 3.0 and abs(bearing - last_bearing) < math.radians(20.0):
                    matches.append((distance_m, det_idx, track_idx))
                    
        # Mesafeye göre küçükten büyüğe sırala
        matches.sort(key=lambda val: val[0])
        
        # En yakın eşleşmeleri kesinleştir
        for dist_m, det_idx, track_idx in matches:
            if det_idx in matched_det_indices or track_idx in matched_track_indices:
                continue
                
            matched_det_indices.add(det_idx)
            matched_track_indices.add(track_idx)
            
            track = self.tracks[track_idx]
            det = raw_detections[det_idx]
            
            # Görev 1.2: Ekran Sınır Kontrolü (Edge Truncation) telafisi
            # Eğer yeni tespit ekran kenarındaysa (truncated), mesafe patlamasını önlemek için 
            # iz geçmişindeki son güvenilir mesafeyi kullan.
            if det.get("is_truncated", False) and len(track["history"]) > 0:
                det["distance"] = track["history"][-1][0]
            
            # Görev 1.4: BB/Mesafe Jitter Filtresi (EMA - Exponential Moving Average)
            if "filtered_distance" in track:
                track["filtered_distance"] = self.filter_alpha * det["distance"] + (1.0 - self.filter_alpha) * track["filtered_distance"]
                track["filtered_bearing"] = self.filter_alpha * det["bearing"] + (1.0 - self.filter_alpha) * track["filtered_bearing"]
            else:
                track["filtered_distance"] = det["distance"]
                track["filtered_bearing"] = det["bearing"]
                
            # Filtrelenmiş değerleri geri yaz
            det["distance"] = track["filtered_distance"]
            det["bearing"] = track["filtered_bearing"]
            
            # Geçmişe ekle
            track["history"].append((det["distance"], det["bearing"]))
            if len(track["history"]) > 5:
                track["history"].pop(0)
            track["missed_frames"] = 0
            
            # 5 karede en az 3 kez görüldüyse izi onayla
            if len(track["history"]) >= 3:
                track["confirmed"] = True
                
            if track["confirmed"]:
                confirmed_detections.append(det)
                
        # 2. Eşleşmeyen yeni tespitler için yeni izler oluştur
        for det_idx, det in enumerate(raw_detections):
            if det_idx not in matched_det_indices:
                new_track = {
                    "id": self.next_track_id,
                    "class": det["class"],
                    "history": [(det["distance"], det["bearing"])],
                    "filtered_distance": det["distance"],
                    "filtered_bearing": det["bearing"],
                    "confirmed": False,
                    "missed_frames": 0
                }
                self.next_track_id += 1
                self.tracks.append(new_track)
                
        # 3. Eşleşmeyen eski izleri yaşlandır ve temizle (3 kare boyunca görülmezse sil)
        remaining_tracks = []
        for track_idx, track in enumerate(self.tracks):
            if track_idx not in matched_track_indices:
                track["missed_frames"] += 1
                if track["missed_frames"] <= 3:
                    remaining_tracks.append(track)
                    # COASTING (Örtbas etme): Eğer daha önce onaylanmış bir izse ve geçici olarak
                    # görülmüyorsa, son bilinen güvenilir (filtrelenmiş) konumuyla bildirmeye devam et.
                    if track["confirmed"]:
                        confirmed_detections.append({
                            "class": track["class"],
                            "distance": track["filtered_distance"],
                            "bearing": track["filtered_bearing"],
                            "is_coasted": True  # Bunun eski bir veri olduğunu belirten bayrak
                        })
            else:
                remaining_tracks.append(track)
                
        self.tracks = remaining_tracks
        return confirmed_detections

    def detect(self, frame, pitch: float = 0.0, roll: float = 0.0) -> list:
        """
        Görüntüde duba algılar ve açı/mesafe hesaplar. Emniyet filtrelerinden geçirir.
        """
        if frame is None:
            return []
            
        # Dinamik çözünürlük uyarlaması (Hata: 159 çözümü)
        h, w = frame.shape[:2]
        if w != self.image_width or h != self.image_height:
            self.image_width = w
            self.image_height = h
            self.focal_length_px = (self.image_width / 2.0) / math.tan(self.hfov_rad / 2.0)
            logger.info(f"Kamera çözünürlüğü dinamik olarak güncellendi: {w}x{h}, Odak Uzaklığı: {self.focal_length_px:.1f} px")
            
        self.frame_count += 1
        
        # [Senaryo 5 Önlemi] Lens tıkanıklık kontrolü
        if self.check_lens_obstruction(frame):
            return []
            
        if self.use_fallback:
            raw_dets = self._detect_hsv(frame, pitch, roll)
        else:
            # --- Horizon ROI Cropping (Ufuk Kırpması) ---
            ymin_px = int(self.roi_ymin_ratio * h)
            ymax_px = int(self.roi_ymax_ratio * h)
            
            # Kırpılmış görüntüyü al
            cropped_frame = frame[ymin_px:ymax_px, 0:w]
            
            # SSD Çıkarımını kırpılmış görüntü üzerinde yap, ymin_px offsetini geçir
            raw_dets = self._detect_ssd(frame, cropped_frame, ymin_px, pitch, roll)
            
        # [Senaryo 6 Önlemi] Zamansal doğrulama filtresi uygula
        return self.temporal_filter(raw_dets)

    def _verify_color_hsv(self, frame, box: list) -> str:
        """
        Duba kutusunun içinde lokalize HSV renk filtrelemesi koşturur.
        Baskın olan rengi tespit edip sınıf etiketini döndürür.
        """
        x, y, w, h = box
        
        # Sınır kontrolleri
        x_min = max(0, min(x, self.image_width - 1))
        y_min = max(0, min(y, self.image_height - 1))
        x_max = max(0, min(x + w, self.image_width))
        y_max = max(0, min(y + h, self.image_height))
        
        roi = frame[y_min:y_max, x_min:x_max]
        if roi.size == 0:
            return None
            
        hsv_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        
        # Renk aralıkları tanımları (detect_hsv ile birebir uyumlu)
        color_ranges = {
            "orange_gate": [((5, 100, 80), (15, 255, 255)), ((165, 100, 80), (175, 255, 255))],
            "yellow_obstacle": [((20, 80, 80), (35, 255, 255))],
            "target_red": [((0, 120, 60), (10, 255, 255)), ((170, 120, 60), (180, 255, 255))],
            "target_green": [((35, 60, 60), (85, 255, 255))],
            "target_blue": [((95, 100, 60), (135, 255, 255))]
        }
        
        color_counts = {}
        for name, ranges in color_ranges.items():
            mask = None
            for lower, upper in ranges:
                m = cv2.inRange(hsv_roi, np.array(lower), np.array(upper))
                mask = m if mask is None else cv2.bitwise_or(mask, m)
            color_counts[name] = cv2.countNonZero(mask)
            
        best_color = max(color_counts, key=color_counts.get)
        max_pixels = color_counts[best_color]
        total_pixels = roi.shape[0] * roi.shape[1]
        
        # Eğer en baskın rengin kapladığı alan kutunun en az %5'i ise doğrulanmış kabul et
        if total_pixels > 0 and (max_pixels / float(total_pixels)) >= self.hsv_min_pixel_ratio:
            return best_color
            
        return None

    def _detect_ssd(self, original_frame, cropped_frame, ymin_offset: int, pitch: float = 0.0, roll: float = 0.0) -> list:
        """
        OpenCV DNN ile MobileNetV3-SSD modelini kırpılmış görüntü üzerinde çalıştırır.
        """
        h_cropped, w_cropped = cropped_frame.shape[:2]
        
        # MobileNet-SSD genellikle 320x320 girdi bekler
        blob = cv2.dnn.blobFromImage(cropped_frame, 1.0, (320, 320), swapRB=True, crop=False)
        self.net.setInput(blob)
        
        # Çıkarım yap
        outputs = self.net.forward()
        
        # SSD çıktı formatı: [1, 1, N, 7]
        # Her bir satır: [batch_id, class_id, confidence, left, top, right, bottom]
        detections = []
        
        if len(outputs.shape) < 4:
            return detections
            
        num_detections = outputs.shape[2]
        
        for i in range(num_detections):
            row = outputs[0, 0, i]
            confidence = float(row[2])
            
            if confidence >= self.conf_threshold:
                class_id = int(row[1])
                
                # Koordinatlar normalleştirilmiştir (0.0 - 1.0), kırpılmış görüntü boyutlarıyla çarp
                left = int(row[3] * w_cropped)
                top = int(row[4] * h_cropped)
                right = int(row[5] * w_cropped)
                bottom = int(row[6] * h_cropped)
                
                width = right - left
                height = bottom - top
                
                # Orijinal 640x480 görüntüsüne geri eşle
                original_left = left
                original_top = top + ymin_offset
                
                # Bounding box sınırlarını kontrol et
                original_left = max(0, min(original_left, self.image_width - 1))
                original_top = max(0, min(original_top, self.image_height - 1))
                width = max(1, min(width, self.image_width - original_left))
                height = max(1, min(height, self.image_height - original_top))
                
                box = [original_left, original_top, width, height]
                
                # --- Hibrit Renk Doğrulaması ---
                # Bounding box içerisindeki renk analizini yap
                verified_class = self._verify_color_hsv(original_frame, box)
                
                # Eğer renk doğrulandıysa o rengi ata, yoksa SSD'nin tahmin ettiği sınıfa güven
                if verified_class:
                    final_class = verified_class
                else:
                    final_class = self.classes.get(class_id, "unknown")
                    
                distance, bearing, is_truncated = self.estimate_distance_and_bearing(box, pitch, roll)
                
                detections.append({
                    "class": final_class,
                    "bbox": box,
                    "confidence": confidence,
                    "distance": distance,
                    "bearing": bearing,
                    "is_truncated": is_truncated
                })
                
        return detections

    def _detect_hsv(self, frame, pitch: float = 0.0, roll: float = 0.0) -> list:
        """
        Yedek algılama mekanizması: HSV renk eşikleme ve kontur analizi.
        Dinamik HSV eşikleme: Işık ve bulut durumlarına göre S ve V alt limitleri uyarlanır (Görev 15).
        """
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        detections = []
        
        # Görüntü ortalama parlaklığını hesapla
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        mean_brightness = np.mean(gray)
        
        # Parlaklığa bağlı alt limit kaymaları (128 referans alınarak)
        # Hava karanlıksa/bulutluysa (mean_brightness < 128) offsetler negatif olur ve eşikler gevşetilir.
        v_offset = int((mean_brightness - 128.0) * 0.4)
        s_offset = int((mean_brightness - 128.0) * 0.2)
        
        color_ranges = {
            "orange_gate": [((5, 120, 100), (15, 255, 255)), ((165, 120, 100), (175, 255, 255))],
            "yellow_obstacle": [((20, 100, 100), (35, 255, 255))],
            "target_red": [((0, 150, 80), (10, 255, 255)), ((170, 150, 80), (180, 255, 255))],
            "target_green": [((40, 80, 80), (80, 255, 255))],
            "target_blue": [((100, 120, 80), (130, 255, 255))]
        }
        
        for name, ranges in color_ranges.items():
            mask = None
            for lower, upper in ranges:
                # Eşikleri parlaklığa göre dinamik uyarla
                low_h, low_s, low_v = lower
                up_h, up_s, up_v = upper
                
                # S alt sınırını 40, V alt sınırını 30'un altına düşürmeyecek şekilde sınırla
                adj_low_s = max(40, min(255, low_s + s_offset))
                adj_low_v = max(30, min(255, low_v + v_offset))
                
                m = cv2.inRange(hsv, np.array([low_h, adj_low_s, adj_low_v]), np.array([up_h, up_s, up_v]))
                mask = m if mask is None else cv2.bitwise_or(mask, m)
                
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
            
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for cnt in contours:
                area = cv2.contourArea(cnt)
                if area < 150:
                    continue
                    
                x, y, w, h = cv2.boundingRect(cnt)
                aspect_ratio = w / float(h)
                if aspect_ratio < 0.2 or aspect_ratio > 1.8:
                    continue
                
                # Görev 1.3: Dalga köpüğü gürültü filtresi (Extent / Doluluk oranı kontrolü)
                # Yuvarlak duba konturları yüksek doluluğa sahiptir (>0.45). Düzensiz köpükler ise elenir.
                extent = area / float(w * h)
                if extent < 0.45:
                    continue
                    
                box = [x, y, w, h]
                distance, bearing, is_truncated = self.estimate_distance_and_bearing(box, pitch, roll)
                
                detections.append({
                    "class": name,
                    "bbox": box,
                    "confidence": 0.85,
                    "distance": distance,
                    "bearing": bearing,
                    "is_truncated": is_truncated
                })
                
        return detections

    def estimate_distance_and_bearing(self, bbox: list, pitch: float = 0.0, roll: float = 0.0) -> tuple:
        """
        Duba piksel genişliğinden mesafe ve merkez sapmasından açı çıkarımı yapar.
        Görev 1.2 (Kenar kesilmesi telafisi) ve Görev 1.5 (Roll/Pitch yalpalama düzeltmesi) içerir.
        """
        x, y, w, h = bbox
        
        # Görev 1.2: Ekran sınır kontrolü (Truncation) tespiti
        # Bounding box sol veya sağ kenara 2 pikselden yakınsa kırpılmış kabul edilir.
        is_truncated = (x <= 2) or (x + w >= self.image_width - 2)
        
        # Eğer kırpılma varsa, mesafe patlamasını önlemek için genişlik yerine yüksekliği referans alıyoruz
        if is_truncated:
            w_px = max(1, h)
        else:
            w_px = max(1, w)
        
        # Ham mesafe hesabı
        distance = (self.focal_length_px * self.BUOY_REAL_WIDTH_M) / w_px
        
        # Görev 1.5: Yalpalama (pitch) açı telafisi
        # Tekne öne/arkaya şahlandığında perspektif sıkışmasını düzelt
        if abs(pitch) > 0.1:
            distance = distance * math.cos(math.radians(pitch))
            
        box_center_x = x + w / 2.0
        box_center_y = y + h / 2.0
        
        offset_x = box_center_x - (self.image_width / 2.0)
        offset_y = box_center_y - (self.image_height / 2.0)
        
        # Görev 1.5: Yalpalama (roll) açı telafisi
        # Tekne sola/sağa yattığında görüntünün dönmesini düzelt (koordinatları ters döndür)
        if abs(roll) > 0.1:
            roll_rad = math.radians(-roll) # Eksen dönüşü tersi yönünde
            offset_x_corr = offset_x * math.cos(roll_rad) - offset_y * math.sin(roll_rad)
            offset_x = offset_x_corr
            
        bearing = math.atan2(offset_x, self.focal_length_px)
        return distance, bearing, is_truncated

    def draw_detections(self, frame, detections: list):
        for det in detections:
            if "bbox" not in det:
                continue
            x, y, w, h = det["bbox"]
            label = f"{det['class']} ({det['confidence']:.2f})"
            dist_label = f"Dist: {det['distance']:.2f}m, Ang: {math.degrees(det['bearing']):.1f}deg"
            
            if "orange" in det["class"]:
                color = (0, 165, 255)
            elif "yellow" in det["class"]:
                color = (0, 255, 255)
            elif "red" in det["class"]:
                color = (0, 0, 255)
            elif "green" in det["class"]:
                color = (0, 255, 0)
            elif "blue" in det["class"]:
                color = (255, 0, 0)
            else:
                color = (255, 255, 255)
                
            cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
            cv2.putText(frame, label, (x, y - 22), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
            cv2.putText(frame, dist_label, (x, y - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)
        return frame
