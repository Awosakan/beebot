# Beebot İDA - Yarış Hazırlık ve Devreye Alma Kılavuzu (YAPILACAKLAR)

Bu belge, otonom deniz aracınızın (Beebot) fiziki montajı tamamlandıktan sonra, yarış gününde ve yarıştan hemen önce donanımları (OnePlus 6 ve STM32) yarışa hazır hale getirmek için yapılması gereken tüm adımları, kalibrasyonları ve doğrulama testlerini adım adım açıklamaktadır.

---

## 📋 İÇİNDEKİLER
1. [Donanım ve Fiziksel Kontroller](#1-donanım-ve-fiziksel-kontroller)
2. [STM32 Yazılım ve Kalibrasyon Adımları](#2-stm32-yazılım-ve-kalibrasyon-adımları)
3. [OnePlus 6 Telefon Kurulumu ve Çevre Birim Entegrasyonu](#3-oneplus-6-telefon-kurulumu-ve-çevre-birim-entegrasyonu)
4. [Kara Testleri (Karada Kuru Çalıştırma Protokolü)](#4-kara-testleri-karada-kuru-çalıştırma-protokolü)
5. [Suya İndirme ve Yarışı Başlatma Adımları](#5-suya-indirme-ve-yarışı-başlatma-adımları)
6. [Acil Durum (Killswitch) ve Güvenlik Senaryoları](#6-acil-durum-killswitch-ve-güvenlik-senaryoları)

---

## 1. Donanım ve Fiziksel Kontroller

Suya inmeden önce tekne içindeki fiziksel güvenliğin doğrulanması gerekir.

- [ ] **Sızdırmazlık (Waterproofing) Kontrolü:** 
  * Tüm kablo geçiş rakorlarını (cable glands) kontrol edin.
  * OnePlus 6'nın yer aldığı akrilik fanlı hazne kapağının O-ring contalarını silikon gres ile hafifçe yağlayın ve vidalarını çapraz sıkın.
- [ ] **Batarya Sabitleme ve Voltaj Kontrolü:**
  * İtici motorlar için kullanılan güç bataryalarını (örn. 4S LiPo) ve STM32/Telefon besleme bataryasını cırt cırt ve kayışlarla tekne gövdesine sabitleyin (ağırlık merkezinin tam ortada ve su hattına paralel olmasına dikkat edin).
  * Batarya voltajlarını ölçün. Hücre başına voltajın **En az 3.8V (Tercihen full dolu 4.2V)** olduğundan emin olun.
- [ ] **Kamera Açısı ve Lens Temizliği:**
  * OnePlus 6'nın ana kamerasını ufuk çizgisini net görecek şekilde **aşağıya doğru hafifçe eğimli (yaklaşık 10-15 derece)** sabitleyin.
  * Lens üzerindeki toz, parmak izi veya nem tabakasını mikrofiber bez ile temizleyin (Bu sayede sistemin *Lens Obstruction / Su Sıçraması* alarmı vermesini önlemiş olursunuz).
- [ ] **Anten Konumlandırma:**
  * RC Killswitch alıcı antenini ve GCS için kullanılan RF/Wi-Fi antenlerini tekne üstündeki karbon fiber veya metal yüzeylerden uzakta, dikey açıyla sabitleyin.

---

## 2. STM32 Yazılım ve Kalibrasyon Adımları

STM32 denetleyicisi motor kontrolü, sensör toplama ve güvenlikten sorumludur. Yarış öncesi kalibrasyonları hayati önem taşır.

### A. ESC (Hız Kontrolcü) Kalibrasyonu (Sadece Yeni ESC Kurulumunda veya Motor Değişiminde)
> [!WARNING]
> ESC kalibrasyonu yapılırken pervane ve motorların dönme ihtimaline karşı **pervaneleri mutlaka çıkarın!**
1. Alıcı kumandasını açın ve gaz kolunu en üste getirin.
2. STM32'ye güç verin. ESC'lerden bip sesleri gelecektir.
3. Gaz kolunu en alta indirin. ESC'ler onay bipi vererek maksimum/minimum gaz aralığını hafızaya alacaktır.

### B. IMU / Pusula (Magnetometre) Kalibrasyonu (En Kritik Adım!)
> [!IMPORTANT]
> Metal iskelelerden, elektrik direklerinden ve tekne içindeki yüksek akım taşıyan güç kablolarından uzakta açık bir alanda yapın.
1. STM32'ye güç vererek IMU sensörünün ısınması için 2 dakika bekleyin.
2. Tekneyi kendi ekseni etrafında (yaw ekseninde) 360 derece yavaşça döndürün (en az 2 tam tur).
3. Tekneyi pitch (öne-arkaya) ve roll (sağa-sola) eksenlerinde 30'ar derece sallayarak manyetik sapma haritasını (Hard-iron / Soft-iron) STM32'nin otomatik kalibre etmesini sağlayın.
4. Pusula yönünü (Heading) gerçek kuzey ile karşılaştırıp doğruluğunu onaylayın (maksimum $\pm 3^\circ$ sapma kabul edilebilirdir).

### C. Alıcı (RC) ve Killswitch Kanal Kontrolleri
1. Kumandadan **Kanal 5 (veya Killswitch için atanan anahtar)** açıldığında STM32 üzerindeki emniyet rölesinin tık sesini duyduğunuzdan emin olun.
2. Kumandayı tamamen kapattığınızda (Failsafe Durumu), STM32'nin motor çıkış sinyallerini anında sıfırladığını (nötr konuma çektiğini) osiloskop veya ESC bildirim ışıklarından teyit edin.

---

## 3. OnePlus 6 Telefon Kurulumu ve Çevre Birim Entegrasyonu

Telefon, otonom kararları veren ve görüntü işlemini gerçekleştiren beyindir.

### A. Python Çevre Birim Kurulumu
Telefon üzerinde yer alan Linux kabuğunda (Termux veya Linux Deploy ortamında) aşağıdaki komutu çalıştırarak gerekli tüm kütüphanelerin yüklü olduğunu doğrulayın:
```bash
# Proje ana dizinindeyken bağımlılıkları yükleyin:
pip install -r requirements.txt
```
*(Gerekli paketler: `opencv-python`, `numpy`, `pyserial`, `rplidar-roboticia`)*

### B. USB OTG Bağlantısı ve İzinleri
1. Kaliteli bir USB-C OTG adaptörü kullanarak telefonu STM32'nin seri-USB köprüsüne (FTDI/CH340) bağlayın.
2. Lidar sensörünün USB kablosunu da OTG çoklayıcıya bağlayın.
3. Android sistemi üzerinde `/dev/ttyUSB0` (Lidar) ve `/dev/ttyACM0` (STM32) portlarına okuma/yazma izinlerini tanımlayın:
   ```bash
   su -c "chmod 666 /dev/ttyUSB0 /dev/ttyACM0"
   ```

### C. Yapılandırma Dosyası (`config.json`) Kontrolü
[config.json](file:///c:/Users/Şahakan/Desktop/aydede/high_level/src/config.json) dosyasını yarış pistine uygun olarak güncelleyin:
*   **Pist Waypointleri:** Yarış komitesinin verdiği enlem/boylam koordinatlarını `p1_wps` (Nokta takibi) ve `p2_wps` (Engel kaçınma) dizilerine girin.
*   **Hedef Renk:** Parkur 3 Kamikaze görevi için hedef rengi (`target_color`) `"target_red"`, `"target_green"` ya da `"target_blue"` olarak ayarlayın.
*   **LIDAR Aktivasyonu:** Lidar bağlı ise `"lidar_enabled": true`, değilse `false` yapın.

---

## 4. Kara Testleri (Karada Kuru Çalıştırma Protokolü)

Suya inmeden önce sistemin bütünsel olarak çalıştığından emin olmak için bu testi mutlaka yapın.

1. **Test Kodlarını Çalıştırın:**
   ```bash
   # Sistem uyumluluk testini çalıştırın
   python scratch/test_stm32_compatibility.py
   
   # Yapay zeka ve duba algılama testini çalıştırın
   python scratch/test_ssd_detection.py
   ```
2. **Asenkron Günlük Sistemini Çalıştırın:**
   ```bash
   python scratch/test_usb_logging.py
   ```
   Bu test başarıyla tamamlandığında, tekne içindeki `/ida_logs` klasöründe ve yedek olarak takılı olan USB bellekte şu dosyaların oluştuğunu kontrol edin:
   - `dosya1_kamera_*.mp4` (Video kaydı)
   - `dosya2_telemetri_*.csv` (Hız, konum, pusula verileri)
   - `dosya3_costmap_*.jsonl` (Lidar engel haritası verisi)

3. **Kuru Eyleyici (Motor/Dümen) Testi:**
   * Otonom yazılımı karada çalıştırın (`python high_level/src/main.py MOCK`).
   * Kameranın önüne kırmızı veya sarı bir cisim getirdiğinizde dümen servosunun/motorların anında cismin tersi yönüne kaçınma manevrası yaptığını gözlemleyin.

---

## 5. Suya İndirme ve Yarışı Başlatma Adımları

Tekne suya indirilirken ve yarış başlatılırken uygulanacak kesin protokol:

```mermaid
graph TD
    A[Tekneyi Suya İndir] --> B[GPS Lock Bekle (HDOP < 1.5)]
    B --> C[Kumanda & GCS Bağlantısını Kur]
    C --> D[Killswitch Güvenlik Testi Yap]
    D --> E[Tekneyi Yarış Başlangıç Hattına Al]
    E --> F[GCS Üzerinden Emniyet Kilidini (ARM) Kaldır]
    F --> G[Yarışı Başlat (Otonom Modu Aktif Et)]
```

### Adım Adım Protokol:
1.  **Güç Verme Sırası:** 
    * Önce kontrol sistemine (Telefon, Lidar ve STM32 mantık devresine) güç verin.
    * Mantık devresinin tamamen açıldığından emin olduktan sonra itici güç motorlarının (ESC) anahtarlarını açın.
2.  **GPS Konum Sabitleme (GPS Lock):**
    * GCS (Yer Kontrol İstasyonu) ekranından teknenin uydulara bağlanmasını bekleyin.
    * **Uydusu sayısı > 10** ve **HDOP < 1.5** değerine ulaştığında konum sabitleme tamamlanmış demektir.
3.  **Killswitch Testi (Su Üstünde):**
    * Tekneyi suya koyup kıyıdan 2 metre açın.
    * Kumandadan Killswitch anahtarını kapatın. Motorların gücünün tamamen kesildiğini ve dümenin nötr konuma geldiğini doğrulayın. Emniyet doğrulandıktan sonra Killswitch anahtarını tekrar "RUN" (Çalışma) konumuna getirin.
4.  **Kamera Başlangıç Pozisyonu:**
    * OnePlus 6 üzerindeki otonom kamera izleyicinin çalıştığını ve ufuk kırpma filtresinin su üstündeki dubaları parlamasız algıladığını GCS canlı yayın ekranından kontrol edin.
5.  **ARM ve Başlatma:**
    * Hakem "BAŞLA" komutunu verdiğinde, GCS üzerinden otonom modu aktifleştirin (`MODE_AUTO`). 
    * FSM durum makinesinin anında `IDLE` durumundan `PARKUR1_NOKTA_TAKIP` durumuna geçtiğini ve teknenin ilk waypoint yönüne doğru hareketlendiğini teyit edin.

---

## 6. Acil Durum (Killswitch) ve Güvenlik Senaryoları

Yarış esnasında yaşanabilecek olası olumsuz durumlar ve alınacak önlemler:

| Durum / Arıza | Sistem Tepkisi | Yapılması Gereken Müdahale |
| :--- | :--- | :--- |
| **Tekne rotadan saptı veya hakem duba sınırlarını ihlal ediyor.** | Otonomi döngüsü devam edebilir. | **Acil Durum Kumanda Müdahalesi:** Kumandadaki Manuel Emniyet Killswitch anahtarını anında kapatın. Eşzamanlı olarak STM32 motor sinyallerini keser. |
| **Kamera merceğine su geldi veya kamera tamamen kapandı (Kötü Senaryo 5).** | `check_lens_obstruction` devresi tetiklenir, kamera engellendi uyarısı verilir ve sistem anında yedek **HSV Eşikleme / Kontur Analizi** moduna geçer. | GCS ekranından görsel durum izlenmeli. Eğer düzelmezse tekne güvenli duruşa geçebilir. |
| **GPS bağlantısı anlık olarak koptu veya uydu kaybı yaşandı.** | Sistem `costmap.py` ve pusula yardımıyla son bilinen rotada tahmini seyre (Dead Reckoning) başlar. 10 saniye boyunca GPS gelmezse `FAILSAFE` durumuna geçer. | Emniyet botu ile teknenin yanına gitmeye hazır olun. |
| **Kamikaze hedefi (kırmızı/yeşil duba) anlık olarak kaybedildi.** | 3 Aşamalı Kurtarma Devreye Girer: (1) 1 sn boyunca son bilinen rotaya git, (2) 2.5 sn boyunca arama modunda dairesel dön, (3) 10 sn boyunca bulunamazsa eve dönüş modunu (`RETURN_HOME`) tetikle. | Sistemin dairesel tarama yapmasını bekleyin, hedefi tekrar yakalayamazsa otonom eve dönüşü izleyin. |

---
**Teknofest 2026 Otonom İDA yarışmasında ekibimize başarılar dileriz! Beebot yarışmaya hazır!**
