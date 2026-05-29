import cv2
import numpy as np
import sys
import os
import math

# Project paths
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "high_level", "src"))
from detector import BuoyDetector

def run_test():
    print("=== MobileNetV3-SSD ve Hibrit HSV Testleri Başlatılıyor ===")
    
    # 1. Test Resmi Oluştur (640x480)
    # Üst yarısı mavi (gökyüzü), alt yarısı su rengi. Su alanında kırmızı, yeşil ve sarı daireler (dubalar) var.
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    # Su arka planı (gri-mavi)
    frame[150:, :] = (120, 100, 80)
    # Gökyüzü (açık mavi)
    frame[:150, :] = (230, 200, 150)
    
    # Kırmızı duba (Parkur 3 Kamikaze Hedef): Merkez: (200, 260), Yarıçap: 15
    cv2.circle(frame, (200, 260), 15, (0, 0, 255), -1)
    
    # Yeşil duba: Merkez: (350, 260), Yarıçap: 15
    cv2.circle(frame, (350, 260), 15, (0, 255, 0), -1)
    
    # Sarı duba (Engel): Merkez: (500, 260), Yarıçap: 15
    cv2.circle(frame, (500, 260), 15, (0, 255, 255), -1)
    
    # 2. Dedektörü Başlat
    detector = BuoyDetector(
        model_path=None,  # Fallback modunu tetikler, test etmek için manuel model mocklayacağız
        image_width=640,
        image_height=480,
        roi_ymin_ratio=0.3, # 480 * 0.3 = 144px
        roi_ymax_ratio=0.8, # 480 * 0.8 = 384px
        hsv_min_pixel_ratio=0.05
    )
    
    # HSV Yedek Modu Testi
    print("\n[TEST 1] HSV Fallback (Yedek Modu) Test Ediliyor...")
    for _ in range(3):
        dets_hsv = detector.detect(frame)
        
    print(f"Tespit Edilen Nesne Sayısı: {len(dets_hsv)}")
    for d in dets_hsv:
        print(f"Nesne Sınıfı: {d['class']}, Mesafe: {d['distance']:.2f}m, Açı: {math.degrees(d['bearing']):.1f}°")
    
    classes_found = [d['class'] for d in dets_hsv]
    assert "target_red" in classes_found, "Kırmızı duba tespit edilemedi!"
    assert "target_green" in classes_found, "Yeşil duba tespit edilemedi!"
    assert "yellow_obstacle" in classes_found, "Sarı duba tespit edilemedi!"
    print("-> HSV Fallback Testi [OK]")
    
    # 3. MobileNetV3-SSD Çıkarım Yapısı ve Koordinat Geri Eşleme Testi
    print("\n[TEST 2] MobileNetV3-SSD Çıktı Çözümleme ve ROI Koordinat Geri Eşleme Test Ediliyor...")
    
    # Dedektör ağını mock'layacağız
    class MockNet:
        def __init__(self):
            pass
        def setInput(self, blob):
            pass
        def forward(self):
            # SSD Formatında yapay çıktı: [1, 1, 3, 7]
            # Her satır: [0, class_id, confidence, left, top, right, bottom] (normalize edilmiş değerler)
            # Not: Kırpılmış resim boyutu: H_cropped = 480 * (0.8 - 0.3) = 240, W_cropped = 640
            # Kırmızı duba koordinatları orijinalde: x=185, y=245, w=30, h=30
            # Kırpılmışta y offseti = 144. O halde kırpılmıştaki y koordinatları: y_cropped = 245 - 144 = 101.
            # Normalleştirilmiş x: [185/640, 215/640] -> [0.289, 0.336]
            # Normalleştirilmiş y: [101/240, 131/240] -> [0.420, 0.545]
            
            # 3 adet duba çıktısı (Kırmızı, Yeşil, Sarı)
            # Normalde SSD modeli sadece genel 'buoy' (örn: class_id = 0) bulsa dahi, localized HSV rengi belirleyecektir.
            out = np.zeros((1, 1, 3, 7), dtype=np.float32)
            # 1. Nesne: Kırmızı
            out[0, 0, 0] = [0, 0, 0.95, 185.0/640.0, 101.0/240.0, 215.0/640.0, 131.0/240.0]
            # 2. Nesne: Yeşil (x=335, y=245, w=30, h=30 -> kırpılmış y=101)
            out[0, 0, 1] = [0, 0, 0.92, 335.0/640.0, 101.0/240.0, 365.0/640.0, 131.0/240.0]
            # 3. Nesne: Sarı (x=485, y=245, w=30, h=30 -> kırpılmış y=101)
            out[0, 0, 2] = [0, 0, 0.88, 485.0/640.0, 101.0/240.0, 515.0/640.0, 131.0/240.0]
            return out
            
    detector.net = MockNet()
    detector.use_fallback = False
    
    # detect() çağrısı yap. Kırpma, SSD çıkarım çözümü ve HSV localized renk doğrulama devreye girecek.
    for _ in range(3):
        dets_ssd = detector.detect(frame)
    print(f"SSD İle Tespit Edilen Nesne Sayısı: {len(dets_ssd)}")
    
    assert len(dets_ssd) == 3, f"Hata: 3 nesne bekleniyordu, {len(dets_ssd)} bulundu."
    
    for d in dets_ssd:
        cls = d["class"]
        bbox = d["bbox"]
        print(f"SSD + HSV Sonucu -> Sınıf: {cls}, Orijinal BBox: {bbox}, Güven: {d['confidence']:.2f}")
        
        # BBox y koordinatı yaklaşık 245 olmalı (orijinal frame koordinatı)
        assert abs(bbox[1] - 245) <= 2, f"Koordinat geri eşleme hatası! Beklenen Y: ~245, Bulunan: {bbox[1]}"
        
        if cls == "target_red":
            assert abs(bbox[0] - 185) <= 2, "Kırmızı X koordinatı yanlış!"
        elif cls == "target_green":
            assert abs(bbox[0] - 335) <= 2, "Yeşil X koordinatı yanlış!"
        elif cls == "yellow_obstacle":
            assert abs(bbox[0] - 485) <= 2, "Sarı X koordinatı yanlış!"
            
    print("-> MobileNetV3-SSD Çözümleme ve Geri Eşleme Testi [OK]")
    print("\n=== TÜM TESTLER BAŞARIYLA GEÇİLDİ! ===")

if __name__ == "__main__":
    run_test()
