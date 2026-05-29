# MobileNetV3-SSD Otonom Tekne Algılama Analiz Raporu

Bu rapor, **OnePlus 6 (Snapdragon 845)** üzerinde çalışan otonom karar yazılımımız için YOLOv8n modeline bir alternatif olarak önerilen **MobileNetV3-SSD (Single Shot Detector)** modelinin mimarisini, avantajlarını, sınırlılıklarını ve bu sınırlılıkları aşmak için uygulanabilecek mühendislik çözümlerini içermektedir.

---

## 1. MobileNetV3-SSD Nedir? (Mimari Yapı)

**MobileNetV3-SSD**, Google tarafından özellikle mobil CPU'lar ve düşük donanımlı gömülü sistemler için optimize edilmiş, iki temel bileşenden oluşan hafif bir nesne algılama (object detection) mimarisidir:

1.  **Backbone (MobileNetV3):** Özellik çıkarımı (feature extraction) yapan ana ağdır. 
    *   **Depthwise Separable Convolutions:** Standart konvolüsyon işlemlerini ikiye (Depthwise ve Pointwise) bölerek işlem yükünü (FLOPs) ve parametre sayısını yaklaşık **%80-90 oranında azaltır.**
    *   **Neural Architecture Search (NAS):** Ağın katman tasarımı insan eliyle değil, bilgisayar algoritmaları (NAS ve NetAdapt) tarafından mobil işlemcilerde en yüksek FPS'i verecek şekilde otomatik tasarlanmıştır.
    *   **Hard-Swish (h-swish) Aktivasyon Fonksiyonu:** Standart `sigmoid` ve `swish` fonksiyonlarının mobil CPU'larda yarattığı ağır üstel hesaplama yükünü ortadan kaldırmak için, bu fonksiyonların doğrusal yaklaşımları (`ReLU6` tabanlı) kullanılmıştır.
2.  **Head (SSD / SSDLite):** Konumlandırma ve sınıflandırma yapan kafadır.
    *   YOLO modelleri gibi tüm görüntüyü ızgaralara bölmek yerine, farklı ölçeklerdeki özellik haritaları (feature maps) üzerinde tanımlı **çapa kutuları (anchor boxes)** kullanarak tek bir geçişte nesneleri ve koordinatlarını saptar.

---

## 2. OnePlus 6 (Snapdragon 845) Performans Karşılaştırması

MobileNetV3-SSD ile mevcut YOLOv8n modellerinin OnePlus 6 üzerindeki teorik ve pratik performans karşılaştırması:

| Metrik | YOLOv8n (ONNX / FP32) | MobileNetV3-SSDLite (TFLite / FP32) | Fark / Avantaj |
| :--- | :--- | :--- | :--- |
| **Çıkarım Süresi (Inference)** | ~30 - 45 ms | **~15 - 20 ms** | MobileNet 2 kat daha hızlıdır. |
| **Pratik Kare Hızı (FPS)** | 22 - 30 FPS | **50 - 60 FPS** | Ekran yenileme hızına (Hz) yakın akıcılık. |
| **İşlemci Yükü (CPU Usage)**| ~%65 - 80 (Isınma yapabilir) | **~%25 - 35 (Serin çalışır)** | Uzun yarışlarda termal yavaşlamayı önler. |
| **Batarya Tüketimi** | Yüksek | **Düşük** | İDA batarya ömrünü doğrudan uzatır. |
| **Küçük Nesne Hassasiyeti** | **Yüksek** (FPN/PAN sayesinde) | Düşük | YOLO uzaktaki dubaları çok daha erken görür. |

---

## 3. Karşılaşılan Kritik Sorunlar ve Mühendislik Çözümleri

MobileNetV3-SSD mobil donanım için mükemmel bir performans sunsa da, açık su şartlarında ve İDA görevlerinde bazı dezavantajlara sahiptir. Bu sorunları çözmek için mimariye entegre edilmesi gereken çözümler aşağıdadır:

### Sorun A: Uzaktaki Dubaları Algılayamama (Küçük Nesne Sorunu)
*   **Neden:** SSD mimarisi, görüntüyü katman katman küçülterek işler. Derin katmanlara ulaşıldığında, uzaktaki 10-20 piksel büyüklüğündeki küçük dubaların bilgisi özellik haritalarında tamamen kaybolur.
*   **Çözüm 1: Bölgesel İlgi Alanı Kırpma (Horizon ROI Cropping)**
    *   Kameradan gelen 1080p görüntünün tamamını 320x320'ye küçültüp MobileNet'e vermek yerine, dubaların bulunabileceği su/ufuk hattını (Örn: görüntünün dikeydeki %30-%80 arası) kırpıp sadece bu bölgeyi modele besleriz. Böylece pikseller sıkışmaz ve uzaktaki dubalar büyük görünür.
*   **Çözüm 2: Feature Pyramid Network (FPN) Entegrasyonu**
    *   Ağın derin katmanlarındaki güçlü anlamsal bilgileri (semantic features) üst katmanlardaki yüksek çözünürlüklü geometrik bilgilerle birleştiren SSDLite-FPN yapısı kullanılır.

### Sorun B: Güneş Yansıması ve Işık Altında Yanlış Renk Sınıflandırması
*   **Neden:** Su üzerindeki yoğun güneş yansıması (parlama) ve gölgeler, yapay zeka ağlarının duba rengini (Kırmızı/Yeşil/Sarı) karıştırmasına neden olur.
*   **Çözüm 1: Localized HSV Histogram Analizi (Hibrit Yapı)**
    *   MobileNetV3-SSD sadece *"duba"* (buoy) sınıfını saptamak için eğitilir (renk sınıflarından arındırılır). Bu, modelin doğruluğunu ciddi ölçüde artırır.
    *   Model bir duba saptadığında, bounding box (sınırlayıcı kutu) koordinatları kırpılır ve sadece o kutunun içinde hızlı bir **HSV Renk Analizi** koşturulur. Piksel baskınlığına göre dubanın Kırmızı mı, Yeşil mi yoksa Sarı mı olduğu **%100 kararlılıkla** saptanır.
*   **Çözüm 2: Ağır Renk Bozulması Augmantasyonu (Color Jittering)**
    *   Model eğitilirken eğitim görüntülerine rastgele parlaklık, kontrast, doygunluk ve ton (hue) değişimleri uygulanarak modelin ışık değişimlerine karşı bağışıklık kazanması sağlanır.

### Sorun C: Sıfır Eğitimle (Zero-Shot) Doğrudan Çalıştıramama
*   **Neden:** Standart COCO veri kümesi modellerinde duba sınıfı yer almaz.
*   **Çözüm: Google Colab & Transfer Learning (Aktarımlı Öğrenme)**
    *   Modeli sıfırdan eğitmek yerine, Google'ın hazır COCO ağırlıklarına sahip MobileNetV3-SSDLite modeli alınır. Roboflow gibi platformlardan indirilen hazır Teknofest İDA veri setleri ile sadece son katmanlar (classification head) eğitilir. Bu eğitim güçlü bir bilgisayar gerektirmez ve Google Colab üzerinde 1 saat içinde tamamlanıp `.tflite` veya `.onnx` olarak dışa aktarılabilir.

---

## 4. Otonom Tekne (Beebot) İçin Hangi Model Seçilmeli?

Karar verme aşamasında projenin fiziksel montajı ve ortamı kritik rol oynar:

1.  **Telefon Su Geçirmez, Hava Almayan Kapalı Bir Kutu İçindeyse (Termal Risk):**
    *   **Seçimimiz `MobileNetV3-SSD` (TFLite) olmalıdır.** Çünkü OnePlus 6 kapalı kutuda güneş altında YOLOv8n koştururken çok ısınacak ve 10-15 dakika sonra termal throttling (frekans kısma) yaparak 5 FPS'e düşecektir. MobileNetV3 işlemciyi yormadığı için stabil 50 FPS'i saatlerce korur.
2.  **Telefonda Aktif Fan Soğutması Varsa ve Uzak Algılama Çok Kritikse:**
    *   **Seçimimiz `YOLOv8n` veya `YOLOv5n` olmalıdır.** Daha kararlı duba takibi yapar ve kapılardan daha erken hizalanmayı sağlar.
