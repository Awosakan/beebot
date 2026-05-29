# YOLO'dan MobileNetV3-SSD Mimarlık Geçiş Planı

Bu plan, **Beebot** otonom seyrüsefer yazılımının algılama (perception) katmanında kullanılan YOLOv8n modelinin tamamen kaldırılıp, OnePlus 6 (Snapdragon 845) işlemcisini termal olarak yormayacak ve daha yüksek FPS sunacak **MobileNetV3-SSD (ONNX)** modeline geçişini ve bu yeni modele özel optimizasyonların sisteme entegrasyonunu hedeflemektedir.

---

## Kullanıcı İncelemesi Gereken Konular

> [!IMPORTANT]
> *   **Model Değişimi ve Çıktı Biçimi:** YOLOv8n çıktısı `(1, 84, 8400)` gibi karmaşık matris işlemleri gerektirirken; MobileNetV3-SSD çıktısı doğrudan `(1, 1, N, 7)` biçimindedir (SSD standardı). Kodun tüm çözümleme (post-process) kısmı bu hafif formata uyarlanacaktır.
> *   **Ufuk Çizgisi Kırpma (Horizon ROI Cropping):** Uzaktaki küçük dubaların piksellerinin küçültme esnasında kaybolmasını engellemek için görüntünün sadece su/ufuk hattı kesilerek modele beslenecektir. Kırpılan bölgeye ait koordinatlar, rota planlayıcıya iletilmeden önce orijinal görüntü koordinat sistemine matematiksel olarak geri eşlenecektir (Offset Mapping).
> *   **Yapay Zeka + HSV Hibrit Renk Doğrulama:** SSD modelinin duba rengini karıştırmasını engellemek için; yapay zeka ile saptanan her duba bölgesinin (bounding box) içinde dinamik ve lokalize bir **HSV Renk Histogram Analizi** koşturulacaktır. Renkler (Kırmızı/Yeşil/Sarı/Mavi) bu analizle teyit edilip sınıf etiketleri güncellenecektir.

---

## Önerilen Değişiklikler

### 1. Konfigürasyon Dosyası Güncellemesi

#### [MODIFY] [config.json](file:///c:/Users/Şahakan/Desktop/aydede/high_level/src/config.json)
*   Ufuk kırpma (ROI) oranları ve lokal renk analizi için eşik değerler eklenecektir:
    ```json
    "roi_ymin_ratio": 0.3,
    "roi_ymax_ratio": 0.8,
    "hsv_min_pixel_ratio": 0.05
    ```

---

### 2. Algılama ve Konumlandırma Katmanı

#### [MODIFY] [detector.py](file:///c:/Users/Şahakan/Desktop/aydede/high_level/src/detector.py)
*   **MobileNetV3-SSD Yükleme:**
    *   `BuoyDetector.__init__` içinde model yükleme fonksiyonu OpenCV'nin SSD/MobileNet formatlarını (ONNX) destekleyecek şekilde güncellenecektir.
*   **Horizon ROI Kırpma ve Eşleme:**
    *   `detect()` fonksiyonunda görüntü modele verilmeden önce `roi_ymin_ratio` (varsayılan 0.3) ve `roi_ymax_ratio` (varsayılan 0.8) oranlarına göre dikey olarak kırpılacaktır (`cropped_frame = frame[ymin_px:ymax_px, 0:W]`).
    *   Saptanan nesne koordinatlarının `y` eksenine `ymin_px` eklenerek orijinal 640x480 koordinat düzlemine geri dönüşümü sağlanacaktır.
*   **Localized HSV Renk Doğrulama (Hybrid Model):**
    *   Her bir bounding box için lokal HSV analizi yapan `_verify_color_hsv(self, frame, box) -> str` fonksiyonu eklenecektir.
    *   Bu fonksiyon duba kutusundaki renkli pikselleri sayarak baskın renge göre sınıfı (`orange_gate`, `yellow_obstacle`, `target_red`, `target_green`, `target_blue`) belirleyecektir.
*   **Çıkarım Fonksiyonu Güncellemesi:**
    *   `_detect_yolo` fonksiyonu `_detect_ssd` olarak değiştirilecek ve SSD'nin `(1, 1, N, 7)` çıktı formatını (class_id, confidence, xmin, ymin, xmax, ymax) çözümleyecek şekilde yeniden yazılacaktır.

---

### 3. Ana Otonomi Düğümü

#### [MODIFY] [main.py](file:///c:/Users/Şahakan/Desktop/aydede/high_level/src/main.py)
*   `YOLOInferenceWorker` thread sınıfı **`SSDInferenceWorker`** olarak yeniden adlandırılacak ve log çıktıları SSD modeline göre güncellenecektir.
*   `main.py` içerisindeki YOLO terimleri ve log uyarıları MobileNet-SSD'ye uyarlanacaktır.
*   Model dosya ismi kontrolü `"en_iyi_duba_modeli.onnx"` olarak kalabilir, ancak model yükleyici bu dosyayı SSD formatında parse edecektir.

---

### 4. Doğrulama ve Test Altyapısı

#### [NEW] [test_ssd_detection.py](file:///c:/Users/Şahakan/Desktop/aydede/scratch/test_ssd_detection.py)
*   MobileNetV3-SSD modelinin duba saptama, ufuk kırpma koordinat dönüşümü ve HSV renk doğrulama işlemlerini sahte bir resim veya kamera akışı üzerinde test eden yeni bir headless test script'i yazılacaktır.

---

## Doğrulama Planı

### Otomatik Testler
1. `python scratch/test_ssd_detection.py` çalıştırılarak:
   * SSD modelinin `(1, 1, N, 7)` çıktı matrisinin başarıyla ayrıştırıldığı,
   * Ufuk kırpması (ROI) sonrasında koordinat dönüşümlerinin hatasız yapıldığı,
   * Lokal HSV analizinin duba rengini doğru teyit ettiği doğrulanacaktır.
2. `python scratch/test_stm32_compatibility.py` çalıştırılarak yeni algılama yapısının STM32 telemetri uyumluluğunu bozmadığı teyit edilecektir.

### Manuel Doğrulama
1. SITL simülatörü (`scratch/sitl_simulator.py`) çalıştırılarak rota planlayıcının yeni model çıktıları ile engellerden başarıyla kaçabildiği test edilecektir.
2. OnePlus 6 telefon üzerinde kuru test yapılarak CPU kullanımının azaldığı ve FPS değerinin arttığı gözlemlenecektir.
