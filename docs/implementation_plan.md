# Donanım Entegrasyonu (Çift Kamera, LIDAR ve Emniyet Sensörleri) ve GCS Haberleşme Planı

Bu plan, onaylanan yeni donanımların (Çift UVC Kamera, RPLIDAR A1, Su Sızıntı Sensörü, JSN-SR04T Su Geçirmez Ultrasonik Sensör, Voltaj/Akım Sensörlü Güç Modülü) yazılıma entegre edilmesi ve Yer Kontrol İstasyonu (GCS) üzerinden uzaktan kablosuz acil motor durdurma (Kill-Switch) mekanizmasının doğrulanması/entegrasyonunu hedeflemektedir.

## Kullanıcı İncelemesi Gereken Konular

> [!IMPORTANT]
> - **GCS Kill-Switch Mekanizması:** Hem RC kumandadan (Ch 6) hem de GCS üzerinden (UDP/Telsiz yoluyla "STOP" ASCII paketi) motorlar anında durdurulabilmektedir.
> - **Seri Protokol Değişikliği:** Telemetri paket boyutu, yeni sensörlerin (sızıntı durumu, akım, ultrasonik mesafe) telefona aktarılması için **59 bayttan 68 bayta** çıkarılacaktır. Bu değişiklik hem STM32 (`protocol.h`) hem de Python (`protocol.py`) tarafında eşzamanlı olarak yapılacaktır.
> - **LIDAR Entegrasyonu:** RPLIDAR A1 verileri otonomi döngüsünde taranarak `costmap` (engel haritası) katmanına "sarı engel" olarak eklenecektir. `rplidar` kütüphanesi yoksa veya cihaz takılı değilse sistem çökmeden çalışmaya devam edecektir (Soft-fail).

---

## Önerilen Değişiklikler

### 1. Protokol Güncellemesi (68 Byte Telemetri)

#### [MODIFY] [protocol.h](file:///c:/Users/Şahakan/Desktop/aydede/STM32/Core/Inc/protocol.h)
*   `Telemetry_t` yapısının sonuna 3 yeni alan eklenecektir:
    ```c
    uint8_t leak_detected;      // 0 = Normal, 1 = Sızıntı var!
    float battery_current;      // Amper cinsinden çekilen akım
    float front_ultrasonic_m;   // Metre cinsinden ön ultrasonik mesafe
    ```
*   `_Static_assert` makrosundaki boyut kontrolü 68 bayt olacak şekilde güncellenecektir:
    ```c
    _Static_assert(sizeof(Telemetry_t) == 68, "Telemetry_t size must be exactly 68 bytes");
    ```

#### [MODIFY] [protocol.py](file:///c:/Users/Şahakan/Desktop/aydede/high_level/src/protocol.py)
*   `pack_stm32_telemetry` ve `unpack_stm32_telemetry` fonksiyonları yeni alanları destekleyecek şekilde güncellenecektir.
*   Format karakter dizisi `<ddffBfffffffBHHB` yerine **`<ddffBfffffffBHHBBff`** olarak değiştirilecektir.
*   Boyut doğrulaması `59` yerine `68` olarak güncellenecektir.

---

### 2. High-Level Python Yazılım Bileşenleri

#### [MODIFY] [main.py](file:///c:/Users/Şahakan/Desktop/aydede/high_level/src/main.py)
*   **Çift Kamera Desteği:**
    *   `config.json` dosyasındaki `video_source` parametresi bir liste alabilecek şekilde güncellenecektir (örn: `[0, 1]`).
    *   Eğer liste verilmişse, her kamera kaynağı için ayrı bir `VideoGrabber` thread'i başlatılacaktır.
    *   YOLO işçisi (`YOLOInferenceWorker`) her iki kameranın görüntüsünü ayrı ayrı işleyecek ve tespit açılarını (bearing) kameranın konumuna göre offsetleyecektir. Sol kamera için `-60°`, sağ kamera için `+60°` açı sapması (`camera_bearing_offsets_deg`) eklenecektir.
*   **RPLIDAR A1 İşçisi (`LidarWorker`):**
    *   Asenkron olarak seri porttan (örn: `/dev/ttyUSB0`) RPLIDAR verilerini okuyan yeni bir thread eklenecektir.
    *   Gelen 360 derecelik noktalar filtre edilecektir (tekne gövdesi içindeki `< 0.45m` noktalar yoksayılacak, geri kalanı 5 derecelik dilimlerle downsample edilecektir).
    *   Bu noktalar duba dedektörü çıktısıyla birleştirilerek costmap'e `yellow_obstacle` olarak beslenecektir.
    *   Kütüphane bulunamaz veya seri port açılmazsa sistem uyarı vererek LIDAR'sız otonomiye devam edecektir (Soft-fail).

#### [MODIFY] [config.json](file:///c:/Users/Şahakan/Desktop/aydede/high_level/src/config.json)
*   Çift kamera ve LIDAR konfigürasyon parametreleri eklenecektir:
    ```json
    "video_sources": [0, 1],
    "camera_bearing_offsets_deg": [-60.0, 60.0],
    "lidar_enabled": true,
    "lidar_port": "/dev/ttyUSB0",
    "lidar_yaw_offset": 0.0
    ```

---

### 3. Low-Level STM32 Firmware Bileşenleri

#### [MODIFY] [sensors.h](file:///c:/Users/Şahakan/Desktop/aydede/STM32/Core/Inc/sensors.h) & [sensors.c](file:///c:/Users/Şahakan/Desktop/aydede/STM32/Core/Src/sensors.c)
*   **Ultrasonik Sensör (JSN-SR04T):** Trigger (Output) ve Echo (Input) pinleri üzerinden 10us tetikleme pulse'ı gönderilip, yankı dönüş süresini mikro saniye cinsinden ölçen ve metreye çeviren `sensors_read_ultrasonic()` fonksiyonu eklenecektir.
*   **Akım Ölçümü:** Güç modülünün akım çıkış pininden ADC okuması yapacak ve kalibre edilmiş amper değerini döndürecek `sensors_current_read()` fonksiyonu eklenecektir.

#### [MODIFY] [safety.h](file:///c:/Users/Şahakan/Desktop/aydede/STM32/Core/Inc/safety.h) & [safety.c](file:///c:/Users/Şahakan/Desktop/aydede/STM32/Core/Src/safety.c)
*   **Su Sızıntı Sensörü (Leak Sensor):** PA1 pininin (Internal Pull-Up) durumu her döngüde okunacaktır. Eğer pin `LOW` durumuna düşerse su sızıntısı algılanacak ve sistem anında `MODE_EMERGENCY` durumuna geçirilerek motorlar durdurulacaktır.
*   `SafetyStatus_t` yapısına `leak_detected` bayrağı eklenecektir.

#### [MODIFY] [main.c](file:///c:/Users/Şahakan/Desktop/aydede/STM32/Core/Src/main.c)
*   `Telemetry_t` nesnesi doldurulurken yeni akım, sızıntı ve ultrasonik veriler yerleştirilecektir.
*   Giriş/Çıkış pin kurulumları (Leak GPIO input, Ultrasonic GPIOs) `main.c` içinde başlatılacaktır.

---

### 4. Test Scriptleri

#### [MODIFY] [test_stm32_compatibility.py](file:///c:/Users/Şahakan/Desktop/aydede/scratch/test_stm32_compatibility.py)
*   Test verisi oluşturma ve doğrulama aşamaları 68 baytlık yeni telemetri formatına göre güncellenecektir. Akım, sızıntı ve mesafe doğrulamaları test kapsamına alınacaktır.

---

## Doğrulama Planı

### Otomatik Testler
1. `python scratch/test_stm32_compatibility.py` çalıştırılarak yeni 68 baytlık telemetri yapısının paketleme ve açma işlemlerinin kayıpsız yapıldığı test edilecektir.
2. Yazılım kuru simülasyon modunda çalıştırılarak LIDAR ve çift kamera thread'lerinin kütüphane/donanım yokluğunda çökme yaşatmadığı doğrulanacaktır.

### Manuel Doğrulama
1. YKİ arayüzü (GCS) üzerinden UDP / Telsiz vasıtasıyla "STOP" komutu gönderilecek ve teknenin otonomi durumundan anında Failsafe durumuna geçtiği gözlemlenecektir.
2. Kumandadaki acil durum anahtarı (Ch 6) kapatılarak STM32'nin motor çıkış PWM'lerini `1500us` (stop) değerine çektiği osiloskop/mantık analizörü ile teyit edilecektir.
