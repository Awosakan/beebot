# İDA ve STM32 Otopilot Hata & Risk Analiz Raporu (hatalar.txt)

Bu rapor, [hatalar.txt](file:///c:/Users/Şahakan/Desktop/aydede/hatalar.txt) dosyasında belirtilen tüm yazılımsal, donanımsal ve seyrüsefer algoritmik risklerini detaylıca incelemektedir. Sistem bileşenleri **Algılama (Perception)**, **Seyrüsefer Planlama (Navigation/APF/Costmap)**, **Haberleşme & Protokol** ve **STM32 Otopilot & Donanım Kararlılığı** olmak üzere 4 ana kategoriye ayrılarak analiz edilmiştir.

Ayrıca, raporda **mevcut kod tabanımızda (Stage 8 - 12 çalışmalarımızda) zaten düzeltilmiş olan kritik hatalar** ile **hâlâ aktif olan ve düzeltilmesi gereken hususlar** net bir şekilde ayrıştırılmıştır.

---

## 1. Algılama (Perception) ve Kamera Hataları

Bu kategorideki hatalar görsel veri alımı, renk uzayı filtreleri, duba algılama ve mesafe çıkarımı aşamalarındaki zafiyetleri tanımlar.

| Hata Adı / Risk | İlgili Dosya | Teknik Ayrıntı / Etki | Mevcut Durum & Çözüm Önerisi |
| :--- | :--- | :--- | :--- |
| **Çoklu Duba Körlüğü** *(Multi-Object Tracking Bug)* | `detector.py` | Nesne takip anahtarı doğrudan sınıf adına göre tutulduğu için aynı anda birden fazla turuncu veya sarı duba kadraja girdiğinde veriler birbirinin üzerine yazılır. | **AKTİF.** <br> *Öneri:* Her duba tespiti için benzersiz bir ID atayan (Centroid Tracker veya basit bir mesafe tabanlı IOU eşleştirme) nesne izleme (MOT) algoritması entegre edilmelidir. |
| **Ekran Kenarı Mesafe Patlaması** *(Edge Truncation Error)* | `detector.py` | Mesafe hesabı kutunun (bounding box) piksel genişliğine bağlıdır. Duba ekran kenarından kısmen çıktığında genişliği azalır; sistem nesneyi çok uzaklaşmış kabul ederek costmap'te yanlış yere yerleştirir. | **AKTİF.** <br> *Öneri:* Dubanın ekran sınırlarına dokunup dokunmadığı kontrol edilmelidir (`x_min <= margin` veya `x_max >= width - margin`). Kenardaki duba genişlik bilgisiyle mesafe hesaplanmamalı, duba tamamen görünene kadar son geçerli mesafe korunmalıdır. |
| **Sabit HSV Eşik Değerleri** *(Static Color Ranges)* | `detector.py` | Statik HSV sınırları bulutlanma, güneş yansıması veya su parlamalarında körleşmeye yol açar. | **AKTİF.** <br> *Öneri:* Ortam ışığına göre dinamik parlaklık (V kanalı) dengelemesi (CLAHE) yapılmalı veya HSV yedek kanalı yerine YOLO ONNX modeli birincil kabul edilmelidir. |
| **Dalga Köpüğü Eşleşme Hatası** *(Wave Foam False Positive)* | `detector.py` | Sudaki dalga köpükleri veya yansımalar HSV kontur analizinde duba gibi algılanıp costmap'e hayali engeller basabilir. | **AKTİF.** <br> *Öneri:* Kontur analizi öncesinde morfolojik işlemler (erosion/dilation - aşındırma/yayma) uygulanarak küçük gürültüler elenmelidir. |
| **Bounding Box Titremesi** *(Bounding Box Jitter)* | `detector.py` | Bounding box sınırlarının dalgalarla oynaması costmap'te gürültülü engel yerleşimine ve rotada titreşime sebep olur. | **AKTİF.** <br> *Öneri:* Duba koordinatları ve mesafeleri costmap'e eklenmeden önce tek boyutlu bir Kalman Filtresi veya Basit Hareketli Ortalama (SMA) ile yumuşatılmalıdır. |
| **Homografi & Perspektif Sapması** *(Perspective Distance Error)* | `detector.py` | Teknenin dalgalarla yalpalaması (pitch/roll) duba piksellerini değiştirerek mesafe hesaplarında yapay oynamalara yol açar. | **AKTİF.** <br> *Öneri:* STM32'den gelen roll/pitch açıları kullanılarak homografi matrisi dinamik olarak düzeltilmeli (Tilt Compensation) veya YOLO 2D koordinatları 3D projeksiyona dönüştürülmelidir. |
| **Kamera Görüntü Donması & Kopması** *(Video Stream Freeze / Blocking)* | `main.py` | Kamera donduğunda veya kablosu çıktığında sistem kör olduğunu anlamaz; donanım seviyesinde V4L2 arayüzü saniyelerce bloke olarak otonomiyi durdurabilir. | **KISMEN DÜZELTİLDİ.** <br> *Durum:* Lens tıkanıklığı koruması eklendi ancak donanımsal donma/kopma kontrolü eksik. <br> *Öneri:* Video yakalama döngüsü ayrı bir thread'e alınmalı, kare güncelleme zaman damgaları (timestamp) izlenerek 1 saniyeden uzun donmalarda sistem doğrudan `STATE_FAILSAFE` moduna geçirilmelidir. |
| **YOLO Sınıf İndeks Karışıklığı** *(Class Index Vulnerability)* | `detector.py` | YOLO sınıf indeksleri konfigürasyondan bağımsız hardcoded yazılmıştır. Yeni bir ONNX model yüklendiğinde duba renkleri karışabilir. | **AKTİF.** <br> *Öneri:* YOLO sınıf eşlemeleri (örn: `0: target_red`, `1: target_green`) `config.json` içerisine taşınmalıdır. |

---

## 2. Yerel Haritalandırma (Costmap) ve Rota Planlama (APF) Hataları

Engellerden kaçınma, rota takibi ve potansiyel alan hesaplamalarında karşılaşılan algoritmik limitler.

| Hata Adı / Risk | İlgili Dosya | Teknik Ayrıntı / Etki | Mevcut Durum & Çözüm Önerisi |
| :--- | :--- | :--- | :--- |
| **COLREGs Sağa Kaçış Kusuru** *(Asymmetric Repulsion Issue)* | `costmap.py` | Ön yarım küredeki her sarı engele sağa kaçış bükümü uygulandığında, zaten sağda duran güvenli engellerin üzerine doğru sürüş yapılması riski. | **DÜZELTİLDİ.** <br> *Durum:* Yapılan geliştirmelerde COLREGs kaçış yönü sadece engel sol ön veya tam kafa kafaya (`dx_m > 0.0` ve `dy_m <= 0.0`) ise aktif edilecek şekilde sınırlandırılmıştır. |
| **Kaçırılan Waypoint Sonsuz Döngüsü** *(Plane Crossing Logic)* | `planner.py` | Tekne rüzgar/akıntı ile savrulduğunda hedefin 3m dışından geçerse waypoint geçişini algılayamayıp daireler çizebilir. | **DÜZELTİLDİ.** <br> *Durum:* Tolerans `0.6` metreye düşürülmüş ve mesafe sınırı kaldırılmıştır. Rota doğrultusundaki izdüşüm düzlemi (Plane Crossing) geçildiği an sonraki waypoint'e atlanmaktadır. |
| **Dönüşlerde Sürat Kaybı** *(Steerage Way Problem)* | `planner.py` | Dönüşlerde hızın direkt `0.2 m/s`ye düşürülmesi dümen yeteneğini tamamen kaybettirip tekneyi akıntıya teslim eder. | **DÜZELTİLDİ.** <br> *Durum:* Planlayıcıdaki alt hız limiti `min_speed_ms = 0.5` m/s olarak güncellenmiş ve kilitlenmiştir. |
| **APF Doğal Kilidi & Yerel Minimum** *(Local Minima Vulnerability)* | `planner.py` | Dubanın hedef ile tekne arasında tam doğrusal hatta kalması durumunda itici ve çekici kuvvetler birbirini sıfırlar, tekne durur. | **AKTİF.** <br> *Öneri:* Local minima tespiti (hızın sıfırlanması ancak hedefe uzak olunması) yapıldığı anda APF bileşke kuvvetine sanal bir dik açılı teğetsel vektör (perturbation force) eklenerek kilit çözülmelidir. |
| **Costmap Sınır Dışı Körlüğü** *(Costmap Boundary Blindness)* | `costmap.py` | 40 metrelik dar costmap aralığı, yüksek hızlarda seyrederken erken kaçış manevraları üretmek için yetersiz kalır (<10sn tepki süresi). | **AKTİF.** <br> *Öneri:* Costmap boyutu veya görüş koridoru uzunluğu (look-ahead) teknenin anlık hızıyla orantılı olarak dinamik olarak genişletilmelidir. |
| **Costmap Ego-Hareket Telafisi** *(Ego-Motion Compensation)* | `costmap.py` | Tekne kendi ekseninde dönerken costmap grid hücreleri güncellenmezse, eski engeller su üstünde savrularak hayalet lekeler bırakır. | **AKTİF.** <br> *Öneri:* Teknenin her hareketinde (enlem/boylam değişimi ve yaw dönüşü) costmap matrisi dönüş matrisi ($R$) ve öteleme vektörü ($T$) ile güncellenmelidir (Ego-motion compensation). |
| **Rüzgar İntegrali Patlaması / Windup** *(Yaw PID Windup Risk / Saturation)* | `planner.py` | Akıntı ve rüzgara direnirken enine sapma integralinin (Cross-Track Error) aşırı birikmesi, dönüşlerde büyük aşım (overshoot) yaptırır. | **DÜZELTİLDİ.** <br> *Durum:* Waypoint'e ulaşıldığı an veya geri savrulmalarda navigasyon integral terimi (`cte_integrator`) otomatik olarak sıfırlanmaktadır. |

---

## 3. Haberleşme ve Protokol Hataları

Yüksek seviyeli Python programı ile alçak seviyeli STM32 firmware'i arasındaki senkronizasyon ve paket bütünlüğü riskleri.

| Hata Adı / Risk | İlgili Dosya | Teknik Ayrıntı / Etki | Mevcut Durum & Çözüm Önerisi |
| :--- | :--- | :--- | :--- |
| **Haberleşme Gecikmesi & Yığılma** *(Telemetry Task Latency)* | `main.c` / `main.py` | Python 24-25 Hz hızda veri basarken STM32 telemetri okuma görevinin 100 ms (10 Hz) çalışması tampon bellek yığılmasına ve gecikmelere sebep olur. | **AKTİF.** <br> *Öneri:* STM32 tarafındaki `TelemetryTask` periyodu 100 ms'den 20 ms'ye (50 Hz) çekilerek ring buffer sürekli boşaltılmalı ve anlık kontrol verileri gecikmesiz işlenmelidir. |
| **Unutulan PID Akort Paketi** *(Feature Mismatch Bug)* | `main.c` / `protocol.h` | `MSG_PID_TUNING` paketi tanımlı olmasına rağmen STM32 tarafında bu paketi yorumlayıp PID kazançlarını güncelleyecek kod bloğu yazılmamıştır. | **AKTİF.** <br> *Öneri:* `main.c` içindeki `TelemetryTask` içerisine `MSG_PID_TUNING` paket kontrolü eklenmeli ve gelen kp, ki, kd değerleri `control_set_pid_gains()` fonksiyonuna beslenmelidir. |
| **Paylaşılan Veri Yırtılması** *(Race Condition / Mutex)* | STM32 / Python | Çoklu iş parçacıklarının (task/thread) seyrüsefer ve telemetri verilerini korumasız güncellemesi. | **KISMEN DÜZELTİLDİ.** <br> *Durum:* Python tarafında `Lock` mekanizması ve Copy-on-Read yapıldı. Ancak STM32 tarafında `latest_commands` float değişkenleri veya sensör verileri FreeRTOS altında atomik olmayan şekilde güncellenmektedir. <br> *Öneri:* STM32 tarafında kritik değişken güncellemeleri `taskENTER_CRITICAL()` / `taskEXIT_CRITICAL()` blokları veya mutex ile korunmalıdır. |
| **Parçalanmış Paket Zaman Aşımı** *(Partial Packet Timeout)* | `protocol.py` | Seri portta gürültü nedeniyle yarım kalan paketler parser state-machine'i sonsuza kadar kilitleyebilir. | **AKTİF.** <br> *Öneri:* Paket okuma state-machine'ine zamansal kontrol eklenmeli, iki bayt arasındaki süre 50ms'yi aşarsa parser otomatik olarak `STATE_WAIT_SYNC1` durumuna sıfırlanmalıdır. |
| **Paket Sıra Numarası Eksikliği** *(Packet Sequence Number)* | `protocol.h` | Paketlerde sıra numarası olmadığı için seri portta geciken eski bir komut paketi yeni gelen güncel bir komutun yerine geçebilir. | **AKTİF.** <br> *Öneri:* `PhoneCommands_t` ve `Telemetry_t` yapılarına 1 baytlık `sequence_id` eklenmeli, eski kimliğe sahip paketler yoksayılmalıdır. |

---

## 4. STM32 Otopilot Yazılımı ve Donanım Kararlılığı

Mikrodenetleyici seviyesinde FreeRTOS görev yönetimi, donanımsal register kilitlenmeleri, acil durum rutinleri ve güç yönetimi riskleri.

| Hata Adı / Risk | İlgili Dosya | Teknik Ayrıntı / Etki | Mevcut Durum & Çözüm Önerisi |
| :--- | :--- | :--- | :--- |
| **Aşırı Aceleci Yosun/Stall Koruması** *(False Positive Failsafe)* | `safety.c` | Yosun koruma algoritmasının çok dar zaman diliminde yön değişimi arayarak normal dönüşte motorları kilitlemesi. | **DÜZELTİLDİ.** <br> *Durum:* En son yazdığımız `safety.c` dosyasında stall kontrolü 4.0 saniye (`STALL_DURATION_MS`) boyunca sürer ve motor itki farkı (`left - right > 0.2f`) varken tetiklenir. Bu sayede normal otonom sürüşteki dönüşler failsafe tetiklemez. |
| **Manuel Modda Tehlikeli Değer Ataması** *(Semantics Mismatch)* | `main.c` | 0-360 derecelik hedef heading verisinin manuel modda doğrudan sağ motorun PWM hücresine yazılması motoru kontrolsüz çalıştırır. | **DÜZELTİLDİ.** <br> *Durum:* Geliştirilen `main.c` içerisinde manuel modda `left_thrust` ve `right_thrust` değerleri doğrudan telefondan gelen normalize edilmiş `[-1.0, 1.0]` aralığındaki motor güç yüzdesi olarak atanmaktadır. |
| **GPS Sıçrama Filtresinde İlk Fix Tuzağı** *(GPS Outlier Initialization)* | `sensors.c` | İlk açılışta uydudan gelen ilk konum hatalı gelirse, sonraki tüm gerçek konumları hatalı kabul ederek filtreler. | **DÜZELTİLDİ / MİTİGE EDİLDİ.** <br> *Durum:* `sensors.c` içinde ilk konum doğrulaması mevcuttur. Ayrıca son veri alımından bu yana 5 saniye geçtiyse filtre otomatik sıfırlanıp yeni konumu kabul eder. |
| **Yan Yan Sürüklenmede Rota Sapması** *(Crab Walk Calibration Error)* | `sensors.c` | Sert yan rüzgar/akıntıda GPS COG (akış açısı) ile pusula yaw açısı farklı olacağından sensör füzyonu yönü saptırır. | **AKTİF.** <br> *Öneri:* GPS COG verisiyle pusula yaw açısı sadece yanal sürüklenme miktarı düşükken (yan ivme $a_y \approx 0$) kalibre edilmeli veya yanal sapmalar APF seyrüsefer planlaması düzeyinde CTE entegraliyle kompanze edilmeye devam edilmelidir. |
| **UART Kesme Kilitlenmesi** *(Overrun Error Vulnerability)* | `main.c` / `stm32f4xx_it.c` | Seri hatta gürültüden dolayı ORE (Overrun) veya FE (Framing) hatası oluştuğunda donanım kilitlenir ve haberleşme kopar. | **AKTİF.** <br> *Öneri:* USART1 ve USART2 kesme servis rutinleri (`USARTx_IRQHandler`) içerisine, hata bayraklarını kontrol eden ve gerekirse donanımı temizleyip yeniden başlatan `__HAL_UART_CLEAR_OREFLAG` ve `HAL_UART_Receive_DMA` kurtarma blokları eklenmelidir. |
| **FreeRTOS Yığın Taşması Riski** *(Stack Size Overflow)* | `main.c` | `StartNavigationTask` veya float matematiğin yoğun döndüğü görevlerde kısıtlı yığın boyutu taşarak çekirdek çökmesine sebep olur. | **MİTİGE EDİLDİ.** <br> *Durum:* `NavigationTask` yığın boyutu `512` kelimeye (2048 bayt) yükseltilerek emniyet payı artırılmıştır. `FreeRTOSConfig.h` içerisine stack overflow kontrol kancası (`configCHECK_FOR_STACK_OVERFLOW = 2`) eklenerek olası taşmaların izlenmesi önerilir. |
| **Acil Stop Butonu Gecikmesi** *(Polling Kill-Switch Delay)* | `main.c` / `stm32f4xx_it.c` | Acil stop butonunun EXTI kesmesi yerine periyodik yazılımsal taramayla okunmasının yarattığı gecikme. | **DÜZELTİLDİ.** <br> *Durum:* Projemizde PC13 pini gerçek donanımsal kesme hattına (`EXTI15_10_IRQHandler`) bağlanmıştır. Butona basıldığı mikro saniyede `HAL_GPIO_EXTI_Callback` tetiklenerek motor çıkışları sıfırlanır. |
| **İtki Doyumunda Yön Kaybı** *(Thrust Saturation Steering Loss)* | `control.c` | Hız ve dümen komutlarının toplamı motor limitlerini aştığında doğrudan kırpma yapılması dönüş kabiliyetini öldürür. | **AKTİF.** <br> *Öneri:* Motor miksaj formülü itki doyumu (saturation) durumunda yön öncelikli ölçeklendirme yapmalıdır. Örneğin, sol veya sağ motor $1.0$ limitini aşarsa, iki motorun gücü de dönüş farkını (steer) koruyacak şekilde orantılı olarak aşağı çekilmelidir. |
| **I2C/SPI Kilitlenmesinde Sensör Donması** *(Bus Lockup Freezing)* | `sensors.c` | I2C veri hattında (MPU6050) oluşacak elektriksel kilitlenmelerin tüm FreeRTOS sensör görevini kalıcı olarak dondurması. | **AKTİF.** <br> *Öneri:* `HAL_I2C_Mem_Read` çağrılarına makul timeout süreleri verilmeli, kilitlenme durumunda GPIO pinleri çıkış yapılarak SCL hattına 9 saat darbesi gönderen veri yolu kurtarma fonksiyonu (`I2C_RecoverBus`) tetiklenmelidir. |
| **İşlemci Kilitlenme Riski** *(Brownout Reset)* | Donanım | Yüksek motor akımının pili anlık çökertip STM32 besleme voltajını düşürdüğünde işlemcinin kararsız kalması. | **AKTİF (Donanım Seviyesi).** <br> *Öneri:* STM32 option byte ayarlarından Brownout Reset (BOR) seviyesi donanımsal olarak Level 3 (~2.7V) olarak programlanmalıdır. Bu sayede voltaj çöktüğünde işlemci donmak yerine güvenle kendini resetler. |
| **FreeRTOS Öncelik Terslemesi** *(Priority Inversion)* | `main.c` | Düşük öncelikli sensör görevinin yüksek öncelikli seyrüsefer görevinin kullandığı I2C bus hattını kilitlemesi. | **AKTİF.** <br> *Öneri:* Paylaşılan donanım kaynaklarına erişimde öncelik kalıtımı (priority inheritance) desteği sunan FreeRTOS Mutex yapısı (`xSemaphoreCreateMutex`) kullanılmalıdır. |

---

## 5. Özet ve Değerlendirme

Analiz sonuçlarına göre:
1. **Düzeltilmiş Olanlar (Güvenli Alan):** `hatalar.txt` dosyasındaki en kritik mantıksal zafiyetler (COLREGs sağa kaçış yönü, waypoint sonsuz döngüsü, yosun korumasındaki hassasiyet ayarı, manuel mod PWM aşımı ve acil stop butonunun kesme tabanlı yapılması) en son yazdığımız STM32 ve Python kodlarında **zaten başarıyla çözülmüştür**.
2. **Kritik Olan ve Düzeltilmesi Gerekenler (Bir Sonraki Adım):**
   - **STM32 UART Hata Yönetimi:** Overrun (ORE) ve Framing Error (FE) hata kesmelerinin temizlenmesi (aksi halde seri haberleşme ilk gürültüde kalıcı olarak kopar).
   - **STM32 Telemetri Hızı:** `TelemetryTask` periyodunun 100 ms'den 20 ms'ye (50 Hz) düşürülerek Python'ın 25 Hz hızıyla eşitlenmesi.
   - **İtki Doyumu Kontrolü (control.c):** Motor limitleri aştığında dümen komutunu korumak için oransal hız düşürme mantığı eklenmesi.
   - **PID Akort Entegrasyonu:** STM32 tarafında `MSG_PID_TUNING` paketinin çözülerek PID katsayılarının canlı güncellenmesi.
   - **Sensör Veri Yolları Timeout Koruması:** I2C kilitlenmelerinde sensör görevinin donmasını engelleyecek bus kurtarma algoritmasının yazılması.
