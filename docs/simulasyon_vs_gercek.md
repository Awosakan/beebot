# 🔍 Simülasyon vs Gerçek Su — Dürüst Analiz

## TL;DR

| | Simülasyon | Gerçek Su |
|---|---|---|
| **Çalışan kod** | `costmap.py`, `planner.py`, `mission_control.py` | **Aynı dosyalar, aynı kod** |
| **Sensör verisi** | Sahte (ideal + küçük gürültü) | Gerçek (gürültülü, eksik, gecikmeli) |
| **Sonuç** | Algoritmayı doğruladık | Sensör kalitesine bağlı |

> [!IMPORTANT]
> Simülasyonda çalışan **algoritma** gerçek teknede de çalışacak. Soru şu: **sensörler algoritmaya yeterince temiz veri verebilecek mi?**

---

## Simülasyonun Basitleştirdiği 6 Kritik Alan

### 1. 📷 Kamera Algılama Kalitesi

| | Simülasyon | Gerçek |
|---|---|---|
| Tespit oranı | %100 (her frame'de her duba görülür) | YOLO: %85-95, HSV: %70-90 |
| Yanlış pozitif | Hiç yok | Su yüzey yansıması, güneş parlaması |
| Sınıf karışıklığı | Hiç yok | Turuncu↔sarı karışabilir |
| Mesafe gürültüsü | ±0.1m Gaussian | ±0.3-0.8m (piksel tabanlı) |
| Açı gürültüsü | ±0.8° Gaussian | ±1.5-3.0° (bbox titremesi) |

**Kodda zaten var olan korumalar:**
- `temporal_filter()` → Centroid tracker, 3 frame onay şartı, EMA yumuşatma
- HSV fallback → YOLO çökerse renk filtrelemeye geçer
- `check_lens_obstruction()` → Su sıçraması tespiti

**Kalan risk:** Dubalar arasından geçerken bir duba kamera kenarında kalırsa `is_truncated` tetiklenir ve mesafe önceki frame'den alınır. Bu **iyi** bir davranış.

> [!NOTE]
> **Koridor algoritması kameraya bağımlı değil, costmap'e bağımlı.** Kamera kötü veri verse bile costmap'teki decay mekanizması sayesinde eski pozisyonlar korunur. Yani bir frame duba görülmese bile costmap'te hâlâ kapı çifti var.

---

### 2. 📡 GPS Doğruluğu (EN KRİTİK FARK)

| | Simülasyon | Gerçek (ucuz GPS) |
|---|---|---|
| Gürültü | ±0.22m (σ=0.000002°) | **±2.0-5.0m** CEP |
| Sapma modeli | Gaussian (sıfır ortalama) | Bias drift + multipath |
| Güncelleme hızı | Her frame (25Hz) | 1-10Hz |

**Kodda zaten var olan korumalar:**
- `gps_filter_size = 5` → 5 örneklik hareketli ortalama
- CTE integratör → Sürüklenme düzeltmesi

**Ama:** 2 metrelik GPS sapması demek, **waypoint'in dubaların ortası yerine bir dubanın üzerine düşmesi** demek olabilir. Bu durumda:
- Planlayıcı hedefe çekerken botu dubaya götürür
- Ama corridor force botu yanal olarak orta hatta iter
- **Net etki:** Bot yine ortadan geçer, ama yolculuk biraz zikzaklı olur

> [!WARNING]
> GPS sapması waypoint'i etkilese de, **kapı geçişi GPS'e değil kameraya bağlı.** Kamera dubayı görüyor → costmap'e koyuyor → koridor kuvveti orta hatta çekiyor. GPS sadece "hedefe ne kadar yakınım" sorusuna cevap verir. Asıl yönlendirme kamera + costmap yapıyor.

---

### 3. 🌊 Dalga ve Tekne Salınımı

| | Simülasyon | Gerçek |
|---|---|---|
| Roll/Pitch | Sabit 0° | ±5-15° (dalga boyuna göre) |
| Kamera titremesi | Yok | Dalga frekansında salınım |
| Algılama kaybı | Yok | Dalga zirvesinde duba kaybolabilir |

**Kodda zaten var olan korumalar:**
- `estimate_distance_and_bearing()` → pitch ve roll telafisi var
- `temporal_filter()` → Missed frames 3'e kadar tolere edilir (duba kaybolsa bile 3 frame iz devam eder)
- Costmap decay = 0.85 → Duba görülmese bile 5-6 frame boyunca costmap'te kalır

**Kalan risk:** Düşük, çünkü İDA küçük bir havuzda/gölde yarışacak, okyanus dalgaları değil.

---

### 4. ⏱️ İşlem Gecikmesi

| | Simülasyon | Gerçek (Raspberry Pi / Telefon) |
|---|---|---|
| Frame süresi | Sabit 40ms | YOLO: 80-200ms, HSV: 30-60ms |
| Costmap güncelleme | Anında | Aynı (NumPy hesaplaması hızlı) |
| Kontrol döngüsü | 25Hz garanti | 5-15Hz gerçekçi |

**Kodda zaten var olan korumalar:**
- `dt = max(0.001, min(1.0, dt))` → Dinamik dt, gecikmeli frame'lere uyum sağlar
- CTE integratör dt ile çarpılır → Hız bağımsız

**Kalan risk:** 5Hz'de costmap decay daha az uygulanır (daha az frame = daha az decay), dubalar costmap'te daha uzun kalır. Bu aslında **avantaj** — kapı çifti daha kararlı.

---

### 5. 👁️ Tek Duba Görüş Problemi

**Simülasyonda:** Her iki duba her zaman aynı anda görülür.

**Gerçekte:** Bot kapıya doğru giderken açı değişir, bir duba kamera FOV'unun dışına çıkabilir. Bu durumda:

| Senaryo | Ne olur |
|---|---|
| 2 duba görülür | ✅ Koridor kuvveti aktif, orta hatta tutar |
| 1 duba görülür | ⚠️ Çift eşleştirme başarısız → tekli duba itmesi (hafif, 2m altı) |
| 0 duba görülür | Costmap decay ile önceki veriler korunur, planner sadece attractive force kullanır |

**Bu iyi mi?** Evet, çünkü:
- Tek duba görüldüğünde hafif itme + planner çekici kuvveti = dubadan kaçınarak hedefe gider
- Costmap'teki eski çift verisi henüz decay etmemişse koridor hâlâ aktif
- Eşleşme başarısız olsa bile bot **eski APF gibi dönmez**, çünkü tekli duba itmesi çok hafif (eski K_repulsive=5.0 yerine sadece 2.0)

---

### 6. 🔄 Costmap Şişirme Birleşmesi

**Simülasyonda:** Dubalar arası mesafe 3m, şişirme yarıçapı ~1m → kümeler ayrık kalır.

**Gerçekte:** Hız arttıkça dinamik şişirme yarıçapı 2.5m'ye kadar çıkabilir. 3m aralıklı iki duba, 2.5m şişirme ile **tek bir küme** olarak birleşir.

**Bu olursa:** `_cluster_gate_posts()` tek bir centroid bulur → çift eşleştirme başarısız → tekli duba itmesi uygulanır → koridor kuvveti **çalışmaz.**

> [!CAUTION]
> Bu en ciddi risk. Çözüm: Kapı katmanı (`grid_gates`) için şişirme yarıçapını sınırlandırmak veya kapı dubalarına daha küçük şişirme uygulamak.

---

## Sonuç: Ne Kadar Güvenebiliriz?

| Bileşen | Güven Seviyesi | Neden |
|---|---|---|
| **Koridor algoritması** | 🟢 %95 | Matematiksel olarak doğru, body-frame'de çalışır |
| **Kamera → Costmap pipeline** | 🟡 %75 | Temporal filter + HSV fallback var ama ışık koşullarına bağımlı |
| **GPS → Planner pipeline** | 🟡 %70 | 5 örneklik filtre 2m sapma için yeterli değil, ama kapı geçişi GPS'e bağlı değil |
| **Tekli duba fallback** | 🟢 %85 | Hafif itme + çekici kuvvet birlikte çalışır |
| **Şişirme birleşme riski** | 🔴 %50 | Yüksek hızda kümeler birleşebilir |

### Önerilen İyileştirmeler (Suya İnmeden Önce)

1. **Kapı şişirme sınırı** → `grid_gates` için inflation radius'u max 0.8m ile sınırla
2. **Simülasyona gerçekçi gürültü ekle** → GPS σ=0.00002° (≈2m), kamera %15 kayıp frame
3. **Simülasyona tek duba senaryosu ekle** → FOV sınırı daraltarak test et
4. **Sahada kalibrasyon** → İlk suya inişte K_corridor ve corridor_influence değerlerini ayarla
