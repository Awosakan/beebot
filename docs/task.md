# MobileNetV3-SSD Geçiş Görev Listesi

- `[x]` **Görev 1: Konfigürasyon Güncellemeleri**
  - `[x]` `config.json` dosyasına `roi_ymin_ratio`, `roi_ymax_ratio` ve `hsv_min_pixel_ratio` parametrelerinin eklenmesi.
- `[x]` **Görev 2: `detector.py` Dosyasının MobileNetV3-SSD ile Yeniden Yapılandırılması**
  - `[x]` `BuoyDetector.__init__` içinde SSD model yapısının kurulması.
  - `[x]` `detect()` içinde Horizon ROI Kırpması (Ufuk Kırpması) ve koordinat geri eşlemenin eklenmesi.
  - `[x]` Lokalize HSV renk doğrulaması (`_verify_color_hsv`) fonksiyonunun entegre edilmesi.
  - `[x]` `_detect_yolo` yerine `_detect_ssd` yazılarak `(1, 1, N, 7)` SSD çıktısının çözümlenmesi.
- `[x]` **Görev 3: `main.py` Otonomi Düğümünün Güncellenmesi**
  - `[x]` `YOLOInferenceWorker` -> `SSDInferenceWorker` sınıf adı ve mantığının güncellenmesi.
  - `[x]` Log mesajları ve tanımların MobileNet-SSD'ye uyarlanması.
- `[x]` **Görev 4: Test ve Doğrulama**
  - `[x]` `scratch/test_ssd_detection.py` test betiğinin yazılması ve çalıştırılması.
  - `[x]` `test_stm32_compatibility.py` haberleşme testinin doğrulanması.
  - `[x]` Simülasyon (`sitl_simulator.py` / `test_stage10.py`) ile otonom rota planlamanın doğrulanması.
- `[x]` **Görev 5: Raporlama ve GitHub Reposuna Gönderim**
  - `[x]` Rapor dosyalarının (`docs/`) güncellenmesi.
  - `[x]` Tüm değişikliklerin committen geçirilip pushlanması.
