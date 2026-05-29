# Otonom Tekne Yazılım Mimarileri ve Mühendislik Yaklaşımları Analizi

Bu raporda, günümüzde otonom deniz araçları (İnsansız Deniz Araçları - İDA / Autonomous Surface Vessels - ASV) alanında öncü olan üniversitelerin (**MIT**, **İTÜ** ve **ODTÜ**) kullandığı yazılım yığınları, uyguladıkları mühendislik metodolojileri ve sistem mimarileri detaylı olarak analiz edilmiş, kendi geliştirdiğimiz yazılımla karşılaştırılmıştır.

---

## 1. MIT (Massachusetts Institute of Technology) - Marine Autonomy Lab & Roboat

MIT, otonom deniz sistemleri konusunda hem teorik hem de pratik düzeyde dünyaya yön veren iki ana yazılım mimarisine sahiptir.

### A. MOOS-IvP (Mission Oriented Operating Suite - Interval Programming)
MIT ve Oxford ortaklığıyla geliştirilen **MOOS-IvP**, özellikle askeri ve bilimsel deniz otopilot projelerinde (denizaltılar, okyanus araştırma gemileri vb.) dünya standardıdır.

*   **Merkezi Veri Tabanı (MOOSDB):** Sistem, tüm süreçlerin (sensör okuma, kontrolör, planlayıcı) birbirleriyle doğrudan haberleşmek yerine **MOOSDB** adlı merkezi bir yayınla-abone ol (publish-subscribe) veri tabanına bağlandığı bir yıldız topolojisine sahiptir. Bu yapı, süreçler arası kilitlenmeleri (deadlock) önler ve olağanüstü bir modülerlik sunar.
*   **Davranış Tabanlı Autonomy (IvP Helm):** Karar verme süreçleri sonlu durum makineleriyle değil, "Davranışlar" (Behaviors) ile yönetilir. Her davranış (örn. *Engelden Kaçma*, *Rotayı Takip Et*, *COLREGs Deniz Çatışma Kuralları*) bağımsız çalışır.
*   **Çoklu Hedef Optimizasyonu (IvP Solver):** Her davranış, doğrudan yön veya hız komutu vermek yerine, olası tüm yön ve hız kombinasyonlarına puan veren parçalı lineer fayda fonksiyonları (**IvP Functions**) üretir. **IvP Solver** (Çözücü), bu fonksiyonları matematiksel olarak birleştirerek o anki tüm hedefleri (örn. hem hedefe gitme hem de engelden kaçma) optimize eden tek bir optimal yön ve hız kararını verir.

### B. MIT Roboat Projesi (Kentsel Otonomi)
MIT ve AMS Institute işbirliğiyle Amsterdam kanallarında yolcu ve lojistik taşımacılığı için geliştirilen tam otonom bot projesidir.

*   **Yazılım Yığını:** ROS (Robot Operating System) + NMPC (Nonlinear Model Predictive Control).
*   **Donanım ve Entegrasyon:** Güçlü endüstriyel bilgisayarlar (Intel NUC / Nvidia Jetson) üzerinde ROS düğümleri çalışır. LiDAR, stereo kameralar ve yüksek hassasiyetli RTK-GPS/IMU verileri füzyona tabi tutulur. Alt seviye motor sürücüleri ve güç yönetimi ise mikrodenetleyiciler (ESP32/STM32) üzerinden CAN Bus ve RS485 hatlarıyla yönetilir.

---

## 2. İTÜ (İstanbul Teknik Üniversitesi) - İnsansız Deniz Aracı Ekipleri (Autobee vb.)

İTÜ bünyesindeki öğrenci ve araştırma takımları (özellikle RoboBoat dünya şampiyonalarında yarışan **ITU Autobee** ve Teknofest ekipleri), modern robotik standartlarını projelerine entegre etmektedir.

*   **Yazılım Yığını:** ROS 2 (Robot Operating System) tabanlı modüler mimari.
*   **Algılama ve Bilgisayarlı Görü (Perception):**
    *   Kameralardan alınan görüntü verileri, dubaların (buoy) tespiti ve sınıflandırılması için **YOLOv8** (veya benzeri evrişimsel sinir ağları - CNN) modelleriyle işlenir.
    *   Bu modeller, SBC (Single Board Computer - örn. Nvidia Jetson) üzerinde **TensorRT** ile optimize edilerek yüksek FPS değerlerinde çalıştırılır.
    *   Tespit edilen dubaların gerçek dünyadaki 3 boyutlu koordinatlarını çıkarmak için 3D LiDAR (örn. Velodyne) ve derinlik kameraları (örn. Intel RealSense) verileri **sensör füzyonu** ile birleştirilir.
*   **Navigasyon ve Karar Verme (GNC):**
    *   Görev akışları için **Davranış Ağaçları (Behavior Trees)** kullanılır.
    *   Global yol planlama için **A\* Algorithm**, lokal engellerden kaçma ve dinamik manevra üretimi için **APF (Artificial Potential Fields)** veya **DWA (Dynamic Window Approach)** algoritmaları ROS 2 Nav2 paketi altında özelleştirilir.
*   **Kontrol ve Simülasyon:**
    *   Alt seviye kontrolör olarak Pixhawk (ArduPilot/PX4 firmware) kullanılır. ROS 2, otopilota MAVLink protokolü üzerinden yönlendirme (guided) komutları gönderir.
    *   Testler sahaya çıkmadan önce **Gazebo** ve **VRX (Virtual RobotX)** fiziksel deniz simülasyon ortamında teknenin dijital ikizi (digital twin) üzerinde gerçekleştirilir.

---

## 3. ODTÜ (Orta Doğu Teknik Üniversitesi) - Robotik Araştırmaları ve İDA Projeleri

ODTÜ bünyesindeki savunma sanayii işbirlikli projeler ve robotik laboratuvarları, askeri standartlara yakın gürbüz (robust) mimarilere odaklanır.

*   **Yazılım Yığını:** ROS/ROS 2, C++ ve Python hibrit altyapısı.
*   **Öne Çıkan Mühendislik Yaklaşımları:**
    *   **Sensör Füzyonu:** GPS (GNSS) kesintilerine karşı IMU ve Compass verileri **Extended Kalman Filter (EKF)** veya **Unscented Kalman Filter (UKF)** ile yüksek frekansta birleştirilerek teknenin yönelimi (heading) ve konumu filtrelenir.
    *   **Sürü Kontrolü (Swarm Autonomy):** Birden fazla İDA'nın formasyon halinde hareket etmesi için merkeziyetsiz haberleşme protokolleri ve ROS'un DDS (Data Distribution Service) katmanı üzerinde çalışılır.
    *   **Gürbüz Kontrol algoritmaları:** Deniz dalgası bozucu etkileri, akıntı ve rüzgar dirençlerini modelleyerek bunları sönümlemek amacıyla klasik PID'nin yanı sıra **LQR (Linear Quadratic Regulator)** veya **Sliding Mode Control (SMC)** kontrolörleri geliştirilir.

---

## 4. Geliştirdiğimiz Yazılım ile Üniversite Ekiplerinin Karşılaştırılması

Kendi geliştirdiğimiz otonom tekne yazılımı ile bu büyük üniversitelerin mühendislik yaklaşımları karşılaştırıldığında, sistemimizin pratiklik ve kaynak verimliliği odaklı tasarlandığı görülmektedir:

| Özellik | Büyük Üniversiteler (MIT, İTÜ, ODTÜ vb.) | Bizim Geliştirdiğimiz Yazılım | Analiz & Yorum |
| :--- | :--- | :--- | :--- |
| **İşletim Sistemi ve Middleware** | ROS, ROS 2, MOOS-IvP (Yoğun işlemci ve RAM ihtiyacı olan karmaşık sistemler) | **STM32 Bare-Metal / FreeRTOS + Python SBC (Lightweight Hibrit Yapı)** | Bizim yapımız, ROS gibi büyük işletim sistemi yüklerini taşımadan, düşük güç tüketen companion bilgisayarlarda (örn. Raspberry Pi) yüksek kararlılıkla çalışabilmektedir. |
| **Düşük Seviye Kontrol (Low-Level)** | Genellikle hazır Pixhawk otopilot kartı (ArduPilot/PX4 hazır yazılımları) | **Özel Geliştirilmiş STM32 C Yazılımı (control.c, sensors.c, safety.c)** | Hazır otopilotlar yerine STM32 üzerinde kendi bare-metal/FreeRTOS kodumuzun olması, donanım kaynaklarına doğrudan erişim sağlayarak gecikmeyi (latency) sıfıra indirir ve özel donanım entegrasyonunu kolaylaştırır. |
| **Sensör Füzyonu** | ROS Robot Localization paketleri (EKF/UKF) | **STM32 Üzerinde Çalışan Özel EKF (Sensors/IMU/GPS)** | Bizim konum ve yön kestirimimiz donanım seviyesinde (STM32 içinde) EKF ile hesaplanmaktadır. Bu durum, üst seviye bilgisayarda oluşabilecek bir kilitlenmede dahi teknenin güvenli konumunu korumasını sağlar. |
| **Yol Planlama (Path Planning)** | ROS Nav2 (A\*, DWA, TEB Local Planner vb.) | **A\* Global Planner + APF (Suni Potansiyel Alanlar) Local Planner** | Kullandığımız matematiksel altyapı (A\* ile global rota çizimi, APF ile dubalardan kaçma) İTÜ ve ODTÜ takımlarının kullandığı modern engelden kaçma algoritmalarıyla tamamen aynı teorik temele dayanır. Python tarafında hafif ve performanslı şekilde sıfırdan yazılmıştır. |
| **Algılama (Perception)** | YOLOv8 + Derinlik Kamerası / 3D LiDAR | **HSV Tabanlı Renk Filtreleme ve Kontur Bulma (Mock Entegrasyonlu)** | Teknofest İDA gibi yarışmalarda dubaların renkleri çok belirgin olduğundan, ağır derin öğrenme modelleri (YOLO) yerine HSV renk uzayında filtreleme yapmak işlem gücünden muazzam tasarruf sağlar ve gecikmeyi azaltır. |
| **Haberleşme Protokolü** | ROS Topics (DDS), MAVLink | **Özel İkili (Binary) Paket Protokolü (protocol.h / protocol.py)** | Hazır protokollerin getirdiği overhead'leri (ekstra veri yükü) önlemek amacıyla tasarlanan `protocol.h`, STM32 ile Python arasında doğrudan ve yüksek hızlı veri akışı sağlar. |
| **Güvenlik ve Kumanda (Safety / RC)** | Otopilot içi güvenlik çemberleri, RC Override | **STM32 Seviyesinde Geofence, Watchdog ve CRSF (ELRS 915MHz) Entegrasyonu** | Kumanda üzerinden tek tuşla Manuel/Otonom geçişi ve ELRS (CRSF) entegrasyonu doğrudan STM32 donanım kesmeleri (interrupt) ile yönetilir. Bu, yüksek hızlı ve güvenilir bir acil müdahale (failsafe) katmanı oluşturur. |

### Sonuç ve Değerlendirme

Üniversite ekipleri genellikle akademik araştırma odaklı olduklarından **ROS/ROS 2** gibi hazır ve geniş kütüphanelere sahip fakat ağır çerçeveleri (framework) tercih ederler. Bu durum, projelerinde yüksek maliyetli ve güç tüketen bilgisayarların kullanılmasını zorunlu kılar.

Bizim geliştirdiğimiz mimari ise **Endüstriyel Gömülü Sistem Yaklaşımı** ile tasarlanmıştır. Gerçek zamanlı kritik görevler (sensör okuma, Kalman filtresi, motor kontrolü ve güvenlik mekanizmaları) tamamen mikrodenetleyici (STM32) üzerinde çözülürken; yoğun hesaplama gerektiren yol planlama ve algılama görevleri üst bilgisayardaki Python betiğine aktarılmıştır. Bu modüler ve hafif tasarım, yarışma parkurundaki görevleri eksiksiz tamamlamak için hem gürbüz hem de son derece maliyet-etkin bir mühendislik çözümüdür.
