# Donanım Entegrasyonu Görev Listesi

- `[x]` **Görev 1: Seri İletişim Protokolü Güncellemesi (68 Bayt Telemetri)**
  - `[x]` STM32 `protocol.h` içerisindeki `Telemetry_t` yapısına `leak_detected`, `battery_current` ve `front_ultrasonic_m` eklenmesi ve statik assert'ün 68 bayt yapılması.
  - `[x]` Python `protocol.py` içerisindeki format dizesinin `<ddffBfffffffBHHBBff` yapılması, pack/unpack fonksiyonlarının güncellenmesi ve boyut doğrulamalarının 68 bayt yapılması.
- `[x]` **Görev 2: High-Level Python Kodunda Çift Kamera ve RPLIDAR A1 Entegrasyonu**
  - `[x]` `config.json` dosyasına çift kamera (`video_sources`), açı sapmaları (`camera_bearing_offsets_deg`) ve LIDAR konfigürasyonlarının eklenmesi.
  - `[x]` `main.py` içinde birden fazla kamera için asenkron `VideoGrabber` listesi başlatılması ve YOLO çıkarımında açı offsetleri uygulanarak tespitlerin birleştirilmesi.
  - `[x]` `main.py` içinde `LidarWorker` asenkron okuyucu thread'i eklenerek RPLIDAR A1 verilerinin taranması, downsample edilmesi ve costmap'e `yellow_obstacle` olarak beslenmesi.
- `[x]` **Görev 3: Low-Level STM32 Firmware Entegrasyonu (Sensörler ve Emniyet)**
  - `[x]` `sensors.c` / `sensors.h` içinde JSN-SR04T ultrasonik sensör okuma fonksiyonunun (`sensors_read_ultrasonic()`) yazılması.
  - `[x]` `sensors.c` / `sensors.h` içinde Güç Modülü akım okuma fonksiyonunun (`sensors_current_read()`) yazılması.
  - `[x]` `safety.c` / `safety.h` içinde sızıntı sensörü pin okuması (PA4) ve sızıntı durumunda `MODE_EMERGENCY` tetiklenmesi.
  - `[x]` `main.c` içinde GPIO pin kurulumlarının (PA4 sızıntı input, PA5/PB0 ultrasonik Trigger/Echo, PA0 akım) yapılması ve `Telemetry_t` yapısının doldurulması.
- `[x]` **Görev 4: Uyum Testleri ve Doğrulama**
  - `[x]` `test_stm32_compatibility.py` test script'inin 68 baytlık formata göre güncellenmesi.
  - `[x]` `test_stm32_compatibility.py` testinin çalıştırılarak doğrulanması.
