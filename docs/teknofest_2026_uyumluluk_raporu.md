# TEKNOFEST 2026 İnsansız Deniz Aracı (İDA) Yarışma Şartnamesi Uyumluluk Raporu

Bu rapor, `2026_İnsansız_Deniz_Araci_Şartnamesi_TR_20_02_V2_0WyXP (1).pdf` resmi yarışma şartnamesinde belirtilen teknik, otonom ve emniyet isterlerinin, İDA otonom tekne yazılım mimarimiz (Python SBC kontrolörü ve STM32 Autopilot) ile olan uyumluluk analizini içerir.

---

## 1. Uyumlu Olduğumuz Teknik ve Yazılım İsterleri (Fully Compliant)

Yazılım altyapımız, şartnamede tanımlanan birçok karmaşık otonom ve veri loglama isterini varsayılan olarak tam anlamıyla karşılamaktadır:

### A. Veri Kaydetme ve Teslim İsterleri (Şartname Madde 4.2)
Yarışma sonrasında hakem heyetine USB bellek ile 20 dakika içinde teslim edilmesi gereken 3 zorunlu dosya formatı yazılımımız tarafından asenkron olarak üretilmektedir:
1.  **Dosya 1 (Otonomi Sensörleri Veri Seti - Kamera):**
    *   *İster:* En az 1 Hz frekansta, her karede zaman etiketi bulunan, obje çerçeveleri (Bounding Box) ve sınıf etiketleri çizilmiş işlenmiş video (MP4).
    *   *Durum:* **Tam Uyumlu.** [telemetry_logger.py](file:///c:/Users/Şahakan/Desktop/aydede/high_level/src/telemetry_logger.py) içindeki asenkron video yazıcı, YOLO/HSV tespit kutuları çizilmiş kareleri alır, sol üst köşeye milisaniye hassasiyetli zaman damgasını (yeşil yazı/siyah kutu zemininde) basar ve 24 Hz (şartnamede istenen 1 Hz'in çok üzerinde) kararlı bir şekilde MP4 formatında kaydeder.
2.  **Dosya 2 (Araç Telemetri Verisi):**
    *   *İster:* En az 1 Hz frekansta; zaman etiketi, konum (lat, lon), yer hızı, yönelim açıları (roll, pitch, heading), hız setpoint'i, yön setpoint'i içeren CSV dosyası. İlk satır header olmalıdır.
    *   *Durum:* **Tam Uyumlu.** `log_telemetry` fonksiyonu 24 Hz frekansta tam olarak bu sütun düzeninde (`Timestamp, Latitude, Longitude, Speed, Roll, Pitch, Heading, SpeedSetpoint, HeadingSetpoint`) header satırlı CSV kaydı üretir.
3.  **Dosya 3 (Lokal Engel Haritası):**
    *   *İster:* En az 1 Hz frekansta lokal costmap/engel haritası.
    *   *Durum:* **Tam Uyumlu.** [mission_control.py](file:///c:/Users/Şahakan/Desktop/aydede/high_level/src/mission_control.py) ızgara verisini 4 Hz frekansta (24/6 oranında) JSON Lines formatında (`timestamp, resolution, grid_size, grid_data`) diske yazar.
4.  **Eşzamanlı USB Çift Loglama (Failsafe Loglama):**
    *   Yarışma sonundaki 20 dakikalık kısıtlı teslim süresinde veri kaybı veya kopyalama telaşı yaşamamak için, logger sistemimiz verileri hem bota (`./ida_logs`) hem de takılacak harici USB belleğe (`config.json` içindeki `usb_log_dir` parametresiyle) **eşzamanlı (asenkron dual-write)** olarak kaydeder. Cihaz sudan çıktığı an USB bellek sökülüp hakemlere doğrudan teslim edilebilir.

### B. Emniyet ve Failsafe Önlemleri (Şartname Madde 4.2 & 5.5.3)
1.  **Fiziksel Acil Durdurma (PC13 EXTI):**
    *   *İster:* Araç üzerinde motor ve aktüatörlerin gücünü anında kesen kırmızı acil stop butonu.
    *   *Durum:* **Tam Uyumlu.** [main.c](file:///c:/Users/Şahakan/Desktop/aydede/STM32/Core/Src/main.c) içinde `EMERGENCY_STOP_PIN` kesmesi tetiklendiği an STM32 donanımsal kesme (ISR) üzerinden motor PWM çıkışlarını anında `1500us` (nötr/stop) değerine çekerek sistemi `MODE_EMERGENCY` durumunda kilitler.
2.  **Kamera ve Sensör Failsafe Modları:**
    *   Kamera bağlantısı koptuğunda veya görüntü donduğunda sistem anında failsafe durumuna geçer, motorları yumuşak rampa ile durdurur.
    *   GPS kilidi koptuğunda İDA akıntıya kapılıp sürüklenmemek için `STATE_LOITER` moduna geçerek rüzgar/akıntıya karşı minimal hızla yönünü korur. GPS kilidi geri geldiğinde kaldığı parkur görevine otomatik devam eder.
3.  **Sanal Çit (Predictive Geofence):**
    *   İDA, başlangıç noktasından (Home WP) 100 metreden fazla uzaklaşırsa veya hızı/ataleti nedeniyle 2 saniye içinde bu çiti aşacağı öngörülüyorsa motorları kapatır ve eve dönüş (`STATE_RETURN`) modunu tetikler.

---

## 2. Durum Makinesi ve Parkur Görevleri Uyumu (FSM Compliance)

Mevcut [mission_control.py](file:///c:/Users/Şahakan/Desktop/aydede/high_level/src/mission_control.py) üzerindeki durum makinemiz, şartnamede tanımlı görev sırasıyla kusursuz çalışmaktadır:

```
[STATE_IDLE] ──(Görev Tetikleme)──> [STATE_PARKUR1] ──(Başarı/Zaman Aşımı)──> [STATE_PARKUR2]
                                                                                   │
[STATE_RETURN] <──(Başarı/Zaman Aşımı)── [STATE_PARKUR3] (Kamikaze) <──────────────┘
```

1.  **Parkur 1 (Nokta Takip):**
    *   Resmi duba ikilileri arasından geçiş görevidir. Rota çizgisi (along-track) düzlem geçiş kontrolü ve CTE (Cross-Track Error) sönümlemeli entegral kontrolümüz sayesinde İDA kapıları ortalayarak geçer ve erken dönüp kapı kaçırma (corner cutting) hatası yapmaz.
2.  **Parkur 2 (Engelli Rota Takip):**
    *   Sarı engel dubalarından sakınarak hedefe gitme görevidir. APF planlayıcımız sarı engeller etrafında otomatik olarak sağa kaçışı (COLREGs Sancak Kaçınması) tetikler. Kıyı şeridine veya sığlığa yakın olunduğunda karaya oturmayı önlemek için sağ tarafın engelli olduğu durumda (`is_right_blocked`) asimetrik sağa kaçış engellenir, güvenli tarafa kaçış yapılır.
3.  **Parkur 3 (Kamikaze Angajmanı):**
    *   UAV/IHA veya hakemlerden gelen hedef rengine göre (Kırmızı, Yeşil, Mavi) doğru dubaya fiziksel temas yapma görevidir. 
    *   *Çözümümüz:* Planlayıcımız hedef rengindeki dubayı itici APF alanı dışında tutar (itme kuvvetini sıfırlar) ve duba etrafındaki engel şişirmesini kaldırır. Diğer iki renkli duba ve sarı engeller ise itmeye devam eder. Bu sayede İDA engellerden kaçarken doğrudan hedef renkli dubaya yönelir ve temas kurar.

---

## 3. Yarışma Günü İçin Kritik Operasyonel Boşluklar (Gap Analysis)

Şartnameye tam uyum sağlamak için yarışma günü sahada çözülmesi gereken ve mevcut yazılımda "boşluk" (gap) teşkil eden kritik unsurlar şunlardır:

### ⚠️ Boşluk 1: Kablosuz Başlatma Komutu İsteri (Wireless Start Command)
*   **Şartname Kuralı:** *"Görev/Hareket Başlat komutu kablolu olarak verilmeyecektir." (Madde 5.5.3.1)*
*   **Mevcut Durum:** `main.py` dosyasında program başladıktan 3.0 saniye sonra otomatik olarak Parkur 1 görevi tetiklenmektedir (`auto_started` tetiği). Bu durum gerçek yarışmada büyük bir kural ihlalidir ve teknenin karada/iskelede otonom çalışmasına neden olur.
*   **Çözüm Planı:**
    *   `main.py` içindeki 3 saniyelik otomatik otonomi başlatma kod bloğu silinmelidir.
    *   Sistem, bota takılacak bir kablosuz haberleşme modülü (örneğin 433MHz telemetry telsizi veya RC kumanda) üzerinden "Başlat" sinyali gelene kadar `STATE_IDLE` durumunda beklemelidir.
    *   RC kumandadaki boş bir kanal (örneğin AUX switch) STM32 üzerinden okunarak veya GCS (Yer Kontrol İstasyonu) yazılımı üzerinden kablosuz olarak telefona gönderilecek bir MAVLink/IDA paketi ile otonomi tetiklenmelidir.

### ⚠️ Boşluk 2: İHA (UAV) ile Hedef Rengi Aktarımı Arayüzü
*   **Şartname Kuralı:** *"Bırakılan plakanın rengi, İHA tarafından otomatik olarak algılanacaktır. İDA’nın İHA tarafından saptanan renkteki hedefe angajman yapılması beklenecektir." (Madde 5.5.3.1)*
*   **Mevcut Durum:** Hedef renk şu anda statik olarak `config.json` içinde tanımlanmaktadır.
*   **Çözüm Planı:**
    *   *Seçenek A (Kablosuz SSH/Reload):* İHA plakayı algıladığında, yerdeki bilgisayar/laptop bu bilgiyi alıp botun (telefonun) üzerindeki `config.json` dosyasını kablosuz (RF/SSH) üzerinden günceller. Canlı config okuyucumuz (`main.py` Görev 9) sayesinde bot sudan çıkarılmadan hedef renk otomatik olarak güncellenmiş olur.
    *   *Seçenek B (Seri Paket):* Telemetri hattı üzerinden İHA/YKİ bota `MSG_HEARTBEAT` veya yeni bir `MSG_SET_TARGET_COLOR` paketi göndererek otonomi rengini anlık set eder.

### ⚠️ Boşluk 3: YKİ / Kalifikasyon Videosu Motor İtki İsteri
*   **Şartname Kuralı:** *Otonomi Videosu Ekran 2 grafiklerinde "Thrusterlardan kuvvet isteği" (motorlara giden güç yüzdesi/PWM) senkron olarak gösterilmelidir. (Madde 3.3.1.1)*
*   **Mevcut Durum:** STM32'den telefona gönderilen `Telemetry_t` paketi motor PWM değerlerini veya o an uygulanan `left_thrust`, `right_thrust` değerlerini barındırmamaktadır. Dolayısıyla telefon loglarında veya YKİ ekranında motorların anlık ne kadar güç uyguladığı senkron grafiklenemez.
*   **Çözüm Planı:**
    *   [protocol.h](file:///c:/Users/Şahakan/Desktop/aydede/STM32/Core/Inc/protocol.h) ve [protocol.py](file:///c:/Users/Şahakan/Desktop/aydede/high_level/src/protocol.py) içindeki `Telemetry_t` yapısının sonuna 2 adet `float` (veya `int16_t` PWM mikrosaniye) motor itki değeri eklenmelidir.
    *   Böylece STM32 anlık uyguladığı PWM sürelerini telefona geri raporlar, telefon da bunu telemetri CSV/JSON loguna yazar ve GCS ekranına aktarır.

---

## 4. Sonuç ve Öneriler

Yazılım mimarimiz, sunduğu ** failsafe korumaları, dinamik sönümlemeleri, akıllı APF tangetial kaçınmaları ve 3-dosya otomatik USB yedekleme altyapısı** ile TEKNOFEST şartnamesinin gereksinimlerini en üst düzeyde karşılamaktadır.

Yarışma gününe kadar giderilmesi gereken en önemli operasyonel eksiklik, **kablosuz başlatma tetiği (wireless start trigger)** ve kalifikasyon videosundaki **motor itki telemetrisinin (thruster feedback)** entegrasyonudur.
