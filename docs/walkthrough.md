# Donanım Entegrasyonu ve Test Doğrulama Walkthrough Raporu

Bu belgede, onaylanan yeni donanımların (Çift UVC Geniş Açılı Kamera, RPLIDAR A1, Su Sızıntı Sensörü, JSN-SR04T Ultrasonik Sensör, Voltaj/Akım Güç Modülü) otonom yazılımımıza (OnePlus 6 Python + STM32 Autopilot) nasıl entegre edildiği, yapılan kod değişiklikleri ve simülasyon testlerinin doğrulama sonuçları özetlenmektedir.

---

## 1. Gerçekleştirilen Kod Değişiklikleri

### A. Seri Protokol Güncellemesi (68 Bayt Telemetri)
*   **[protocol.h](file:///c:/Users/Şahakan/Desktop/aydede/STM32/Core/Inc/protocol.h) & [protocol.h](file:///c:/Users/Şahakan/Desktop/aydede/low_level/include/protocol.h):** 
    `Telemetry_t` yapısının sonuna `leak_detected` (1 byte), `battery_current` (4 bytes) ve `front_ultrasonic_m` (4 bytes) alanları eklendi. Statik boyut assert'ü `68` bayt olarak güncellendi.
*   **[protocol.py](file:///c:/Users/Şahakan/Desktop/aydede/high_level/src/protocol.py):** 
    Format dizesi `<ddffBfffffffBHHBBff` olarak güncellendi ve pack/unpack fonksiyonları yeni alanları çözümleyecek/paketleyecek şekilde genişletildi.

### B. High-Level Python Kodları (Birden Fazla Kamera ve LIDAR)
*   **[config.json](file:///c:/Users/Şahakan/Desktop/aydede/high_level/src/config.json):** 
    Çoklu kamera kaynak listesi (`video_sources`: `[0, 1]`), kamera açı sapmaları (`camera_bearing_offsets_deg`: `[-60.0, 60.0]`) ve RPLIDAR A1 parametreleri (`lidar_enabled`: `true`, `lidar_port`: `"/dev/ttyUSB0"`) tanımlandı.
*   **[main.py](file:///c:/Users/Şahakan/Desktop/aydede/high_level/src/main.py):**
    *   **Çift Kamera İşleme:** Her kamera kaynağı için ayrı bir asenkron `VideoGrabber` ve race-condition (veri çakışması) yaşamamak adına ayrı birer `YOLOInferenceWorker` thread'i başlatıldı. Tespit edilen dubaların bearing (açı) değerleri, kameranın montaj açısına göre (`-60°` ve `+60°`) otomatik offsetlenerek birleştirildi.
    *   **RPLIDAR A1 Entegrasyonu:** Asenkron `LidarWorker` thread'i eklendi. RPLIDAR A1 taramalarından gelen 360 derecelik verilerden tekne gövdesi içindeki (`< 0.45m`) noktalar filtrelendi, 5 derecelik dilimlerle downsample edilerek `costmap` katmanına `yellow_obstacle` (sarı engel) olarak beslendi. Kütüphane bulunamazsa sistem çökmeden çalışmaya devam eder (soft-fail).

### C. Low-Level STM32 Firmware (Sensörler ve Emniyet)
*   **[main.h](file:///c:/Users/Şahakan/Desktop/aydede/STM32/Core/Inc/main.h):** 
    Çakışmaları önlemek adına serbest pinlerden `LEAK_SENSOR` (PA4), `ULTRASONIC_TRIG` (PA5), `ULTRASONIC_ECHO` (PB0) ve `CURRENT_SENSOR` (PA0) tanımları yapıldı. (Çünkü PA1 batarya ADC, PA2/PA3 ise GPS USART'tı).
*   **[sensors.c](file:///c:/Users/Şahakan/Desktop/aydede/STM32/Core/Src/sensors.c):** 
    JSN-SR04T için Trigger pulse'ı ve Echo pulse süresini ölçerek metreye çeviren `sensors_read_ultrasonic` fonksiyonu yazıldı. Güç modülünün akımını okuyan `sensors_current_read` yazıldı. ADC kanal çakışmalarını önlemek için voltaj ve akım okumaları öncesi kanallar (`ADC_CHANNEL_1` ve `ADC_CHANNEL_0`) dinamik olarak yeniden yapılandırıldı.
*   **[safety.c](file:///c:/Users/Şahakan/Desktop/aydede/STM32/Core/Src/safety.c):** 
    Sızıntı sensörü pini (PA4) her döngüde okunacak şekilde entegre edildi. Sızıntı tespiti (`LOW` sinyali) durumunda sistem anında `MODE_EMERGENCY` durumuna geçirilerek motor PWM'leri kesilir.
*   **[main.c](file:///c:/Users/Şahakan/Desktop/aydede/STM32/Core/Src/main.c):** 
    `TelemetryTask` içinde akım, mesafe ve sızıntı sensörleri okunarak 68 baytlık telemetri paketi ile telefona aktarıldı. GPIO ve analog pin kurulumları `MX_GPIO_Init` içinde yapıldı.

---

## 2. Test ve Doğrulama Sonuçları

Entegrasyon sonrası tüm otonomi ve haberleşme yapısının testleri koşturulmuş ve hepsi başarıyla tamamlanmıştır.

### Test 1: STM32 ve Python İletişim Uyumluluk Testi
[test_stm32_compatibility.py](file:///c:/Users/Şahakan/Desktop/aydede/scratch/test_stm32_compatibility.py) test scripti yeni 68 baytlık telemetri yapısı ve 17 baytlık komut yapısına göre güncellenip çalıştırıldı.
```bash
python scratch/test_stm32_compatibility.py
```
**Sonuç:**
*   `[TEST 1] Telefon Komut Paketleme Test Ediliyor... -> Toplam Komut Paket Uzunluğu: 17 bayt [OK]`
*   `[TEST 2] STM32 Telemetri Paket Çözme Test Ediliyor... -> Telemetri Payload Uzunluğu: 68 bayt [OK] -> Tüm çözülen veriler STM32 yapısal hizalaması ile %100 UYUMLU! [OK]`
*   `[TEST 3] CRC16 Modbus Algoritması Test Ediliyor... -> Hesaplanan CRC: 0x1028 [OK]`
*   **Genel Durum:** `STM32 ve Python Haberleşme Yapısı %100 Uyumlu! Test Başarılı.`

### Test 2: FSM, Ramp ve Kamikaze Zaman Aşımı Testleri
[test_stage10.py](file:///c:/Users/Şahakan/Desktop/aydede/scratch/test_stage10.py) çalıştırıldı.
```bash
python scratch/test_stage10.py
```
**Sonuç:**
*   `=== TEST 1: Dinamik Konfigürasyon Yükleme === SUCCESS`
*   `=== TEST 2: FSM Durum Zaman Aşımı === SUCCESS (IDLE -> PARKUR1 -> PARKUR2 -> PARKUR3 -> RETURN)`
*   `=== TEST 3: Motor Ramp Filtresi === SUCCESS`
*   `=== TEST 4: Kamikaze Hedef Kaybı Stratejisi === SUCCESS (3 aşamalı koruma doğrulanarak RETURN_HOME tetiklendi)`
*   **Genel Durum:** `TÜM TESTLER BAŞARIYLA TAMAMLANDI!`

### Test 3: Otonom Kapı Geçiş ve Seyrüsefer Testi
[test_gate_navigation.py](file:///c:/Users/Şahakan/Desktop/aydede/scratch/test_gate_navigation.py) simülatörü çalıştırıldı.
```bash
python scratch/test_gate_navigation.py
```
**Sonuç:**
*   İDA otonom olarak 4 kapı waypoint'ini de başarıyla takip etti.
*   Lokal minimuma girmeden kapıları ortalayarak rota planladı.
*   **Genel Durum:** `SUCCESS: Passed between Gate 3 buoys!`

---

## 3. Donanımsal Kurulum ve Kalibrasyon Tavsiyeleri

1.  **LIDAR Montaj Yönü:** LIDAR bota yerleştirilirken ön tarafının İDA'nın burnuyla aynı hizada olduğundan emin olunmalıdır. Sapma varsa `config.json` içindeki `lidar_yaw_offset` parametresi ile düzeltilebilir.
2.  **Sızıntı Sensörü:** Sensörün tekne gövdesinin en derin (dip) noktasına yerleştirilmesi, su almanın en erken evrede yakalanması açısından hayatidir.
3.  **Ultrasonik Mesafe Sensörü:** JSN-SR04T sensör kafasının sudan en az 15 cm yukarıda, teknenin tam burun ucunda su sıçramalarına karşı korunacak şekilde yerleştirilmesi önerilir.

---

## 4. GitHub Reposu Geçişi (Beebot)

Kullanıcının talebi üzerine proje **"Beebot"** olarak yeniden adlandırılmış ve GitHub üzerinde yeni bir repo oluşturularak tüm kod tabanı oraya aktarılmıştır.

*   **Yeni Depo (Remote URL):** `https://github.com/Awosakan/beebot.git`
*   **Kullanıcı Adı:** `Awosakan`
*   **Gerçekleştirilen Adımlar:**
    1.  `scratch/create_beebot_repo.py` script'i aracılığıyla GitHub API üzerinden yeni `beebot` reposu oluşturuldu.
    2.  Proje adlandırma ve yeni eklenen tüm donanımları (Çift UVC Kamera, RPLIDAR A1, su sızıntı koruması, ön ultrasonik sensör, akım takibi vb.) kapsayacak şekilde Türkçe (`README_TR.md`) ve İngilizce (`README.md`) dökümantasyon dosyaları güncellendi.
    3.  Yerel git deposunun remote URL adresi yeni repoya yönlendirildi: `git remote set-url origin https://github.com/Awosakan/beebot.git`
    4.  Tüm kodlar ve yeni eklenen dosyalar (`STM32/Core/Inc/rc.h`, `STM32/Core/Src/rc.c`, `low_level/include/rc.h`, `low_level/src/rc.c`, `high_level/src/astar.py` vb.) stage edilerek commitlendi.
    5.  `scratch/create_beebot_repo.py` içerisinde bulunan hassas GitHub Token bilgisi temizlendi, çevre değişkenine (`os.environ.get`) bağlandı ve commit amend edilerek push korumasına takılmadan temiz bir şekilde yeni repoya (`main` branch) pushlandı.
    6.  Kullanıcının geri bildirimi doğrultusunda, donanım fiyat analizi raporundaki donanım bağlantı şeması (mermaids formatında) Türkçe (`README_TR.md`) ve İngilizce (`README.md`) dökümanlarına eklendi.

---

## 5. MobileNetV3-SSD Model Geçişi ve Optimizasyonlar

YOLOv8n modelinin OnePlus 6 CPU'sunda yarattığı termal yükü azaltmak amacıyla sistem tamamen **MobileNetV3-SSD** model mimarisine geçirilmiştir.

*   **Gerçekleştirilen Kod Değişiklikleri:**
    1.  **[config.json](file:///c:/Users/Şahakan/Desktop/aydede/high_level/src/config.json):** Ufuk kırpması (`roi_ymin_ratio`, `roi_ymax_ratio`) ve lokal renk analizi oranı (`hsv_min_pixel_ratio`) konfigürasyona eklendi.
    2.  **[detector.py](file:///c:/Users/Şahakan/Desktop/aydede/high_level/src/detector.py):** 
        *   `BuoyDetector.__init__` MobileNet SSD (ONNX) modeli yükleyebilecek şekilde güncellendi.
        *   **Horizon ROI Cropping:** `detect()` içinde görüntünün sadece su hattı kırpılarak (`ymin_px` ve `ymax_px` sınırlarında) modele beslendi ve saptanan bbox koordinatları orijinal frame sistemine geri eşlendi.
        *   **Hybrid SSD + Localized HSV:** Her sınırlayıcı kutunun içinde dinamik bir HSV renk dağılım analizi yapılarak dubaların renkleri (`orange_gate`, `yellow_obstacle`, `target_red`, `target_green`, `target_blue`) yüksek doğrulukla doğrulandı.
        *   `_detect_yolo` metodu yerine SSD çıktı matris yapısını `(1, 1, N, 7)` ayrıştıran `_detect_ssd` metodu yazıldı.
    3.  **[main.py](file:///c:/Users/Şahakan/Desktop/aydede/high_level/src/main.py):** `YOLOInferenceWorker` sınıfı `SSDInferenceWorker` olarak güncellendi ve tüm otonom log çıktıları MobileNet-SSD'ye uyarlandı.
*   **Doğrulama Sonuçları:**
    *   `scratch/test_ssd_detection.py` yazıldı ve koşturuldu. Hem HSV fallback modunun hem de SSD çıkarım + lokalize renk doğrulaması ve ROI koordinat eşleme işlemlerinin başarıyla çalıştığı teyit edildi (`TÜM TESTLER BAŞARIYLA GEÇİLDİ!`).
    *   `test_stage10.py` çalıştırılarak tüm FSM durum zaman aşımları, PID motor rampası ve kamikaze duba kaybı koruma stratejileri başarıyla doğrulandı.
