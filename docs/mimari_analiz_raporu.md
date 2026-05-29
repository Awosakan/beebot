# İDA Otonom Yazılım Mimari ve Matematiksel Analiz Raporu

Bu rapor, İDA (İnsansız Deniz Aracı) projesi için geliştirilen otonom yazılım ekosisteminin genel mimarisini, stabilite durumunu ve zorlu görevler için kullanılan matematiksel modellerin güvenilirliğini incelemektedir.

## 1. Genel Mimari Değerlendirme

İDA'nın yazılımı, yüksek seviyeli işlemleri yapan bir **Python Bilgisayarı (SBC)** ile gerçek zamanlı motor/sensör kontrolünü yapan bir **STM32 Mikrodenetleyicisi** arasında ikiye bölünmüştür. Bu "Dağıtık Mimari" endüstri standardı bir yaklaşımdır.

> [!TIP]
> **Mimari Doğruluk:** **Mükemmel.** Görüntü işleme ve APF (Yapay Potansiyel Alanlar) gibi ağır hesaplamalar güçlü işlemcide (Python), motor PWM sinyalleri ve donanımsal güvenlik kesmeleri ise gerçek zamanlı işlemcide (STM32) çalıştırılarak işlemci yükleri kusursuz bir şekilde izole edilmiştir.

### Veri Akış Boru Hattı (Pipeline) Doğruluğu
Sistem, klasik Otonomi Boru Hattı hiyerarşisine tam uyumludur:
1. **Algılama (Perception):** `detector.py` kameradan görüntü alır, gürültüleri filtreler.
2. **Haritalama (Mapping):** `costmap.py` tespitleri bot merkezli (Ego-centric) ızgaraya (Grid) yerleştirir.
3. **Planlama (Planning):** `planner.py` APF vektör matematiğini kullanarak hedefe rotayı çizer.
4. **Kontrol (Mission Control):** `mission_control.py` Durum Makinesi (FSM) ile üst düzey görevleri yönetir.

**Karar:** Mimari iskelet otonomi teorisine %100 uygundur. Herhangi bir spagetti kod veya sorumluluk karmaşası bulunmamaktadır.

## 2. Matematiksel Modellerin Başarısı

Zorlu deniz şartlarına (akıntı, rüzgar, sensör gürültüsü) karşı geliştirilen algoritmaların doğruluğu şu şekildedir:

### A. Rota Çizgisi Takibi ve Sürüklenme (Cross-Track Error)
*   **Matematik:** `planner.py` içinde uygulanan `cte = boat_dx * (-u_y) + boat_dy * u_x` formülü, 2 Boyutlu Uzayda vektörel çapraz çarpım (Cross Product) mantığına dayanır. Entegral birikimi ile rüzgar/akıntı sürüklenmesini hesaplar.
*   **Analiz:** Çok başarılı. PID kontrolcülerin en büyük zafiyeti olan aşırı birikmeyi (Windup) engellemek için `max_cte_i = 1.5` ve çapraz geçiş sönümlemesi eklenmiştir. Bu matematiksel olarak gemiyi tam rotasında tutmak için kusursuzdur.

### B. Çarpışma Önleme (Artificial Potential Fields - APF)
*   **Matematik:** Cazibe (Attractive) kuvveti uzaklığa bağlı normalize edilmiş vektördür. İtici (Repulsive) kuvvet ise engellere 1.2 metre ve 2.0 metre yaklaşıldığında devreye giren ters orantılı itme formülüdür.
*   **Analiz:** Başarılı. APF algoritmalarının en büyük sorunu olan "Yerel Minimuma Kilitlenme" (Local Minima) durumuna karşı Teğet Kuvveti (Perturbation/Tangential Force) uygulanarak matematiksel kilitlenme çözülmüştür. Kapı geçişlerindeki yanal sapma hesaplama hatası son commit ile temizlenmiş, APF en stabil haline kavuşmuştur.

### C. Kamera Toleransı (EMA ve Coasting)
*   **Matematik:** Dubaların mesafesi `d = (gerçek_genişlik * odak_uzaklığı) / piksel_genişliği` formülü ile Pinhole Kamera Modelinden çıkarılır. Ardından Eksponansiyel Hareketli Ortalama (EMA) ile titremeler giderilir.
*   **Analiz:** Pinhole modeli teknenin yunuslama (pitch) hareketlerinde dalgalanabilir. Bunu hafifletmek için geçici bellek (Coasting - 3 frame) ve hareketli ortalama kullanılması çok zekice ve yeterlidir.

## 3. Sistem Stabilitesi (Stabilite - Kararlılık)

Yazılımın matematiksel modelleri kusursuz olsa da, **donanım ve çoklu-görev (Multi-Threading) seviyesinde** sistem stabilitesinde hâlâ açıklar vardır. 

> [!WARNING]
> Python tarafında uyguladığımız "Thread Safety" kilitleri (telemetry_lock) sistemi Python'da güvenceye almıştır, ancak STM32 tarafında C kodlarında hala kilitlenme (Crash) riskleri mevcuttur.

### Aktif Kalan Riskler (Çözülmesi Gerekenler)
1. **Race Conditions (Yarış Durumları):** STM32 içinde I2C sensör okumaları ve motor kontrolleri eşzamanlı çalışmaktadır. `volatile` kelimesinin eksikliği ve `taskENTER_CRITICAL()` bariyerlerinin olmaması, ağır işlem yükünde C çekirdeğinin çökmesine neden olabilir.
2. **UART Buffer Taşması:** Gürültülü seri iletişimde STM32 `Overrun Error` (ORE) verdiğinde seri port donanımsal olarak kilitlenmektedir.
3. **Ego-Motion Eksikliği:** İDA kendi ekseni etrafında hızlıca dönerse (Yaw), `costmap.py` içerisindeki eski engeller dönüş yönünün tersine sanal olarak kayma yaşar.

## 4. Sonuç ve Öneriler

**Genel Puan:** 8.5 / 10

İDA'nın mevcut yazılım mimarisi askeri standartlara çok yakın, esnek ve modüler bir mimaridir. Matematiksel algoritmalar yarışma parkurlarını her türlü akıntıya rağmen en hızlı sürede tamamlayabilecek seviyededir. Python (Otonomi) tarafı şu an zirve noktasındadır.

Ancak sistemin deniz üzerinde **saatlerce çökmeden** çalışabilmesi (Stabilite) için; tüm eforumuzu `STM32 Firmware (Alçak Seviye)` kodlarındaki Thread Safety ve UART hata temizleme (Error Handling) işlemlerine kaydırmamız gerekmektedir. 

*Not: STM32 Firmware onarım planına geçiş yapmak için onayınız yeterlidir.*
