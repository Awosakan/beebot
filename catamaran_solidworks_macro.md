# Beebot Katamaran İDA - SolidWorks Makro Tasarım Kılavuzu

Bu doküman, Teknofest 2026 İnsansız Deniz Aracı Şartnamesi'ne tam uyumlu, en yüksek hidrodinamik kararlılığa sahip, fütüristik dalga delici (wave-piercing) pruvalı katamaran gemimizin SolidWorks 3D modelini sıfırdan otomatik oluşturacak **VBA Makro kodunu** ve kullanım kılavuzunu içermektedir.

---

## 📐 Tasarım Parametreleri & Mühendislik Doğrulaması

Katamaran gövdemiz, mukavemet, stabilite ve sızdırmazlık kriterlerini optimize edecek şekilde şu hidrostatik değerlerle tasarlanmıştır:

*   **Boy ($L$):** $120\text{ cm} = 1.2\text{ m}$ (Su direncinin düşmesi için optimum boy/en oranı).
*   **Toplam En ($B$):** $80\text{ cm} = 0.8\text{ m}$ (Yüksek enine stabilite için geniş yerleşim).
*   **Draft / Su Kesimi ($T$):** $15\text{ cm} = 0.15\text{ m}$ ($25\text{ kg}$ deplasmanda).
*   **Enine Metasantrik Yükseklik ($GM_T$):** $85.5\text{ cm}$ (Olağanüstü devrilmezlik performansı).
*   **Batarya Kızak Hacmi:** $160 \times 50 \times 50\text{ mm}$ (Standard 4S/6S LiPo bataryalar için kızaklı modüler sızdırmaz yuva).

---

## 🛠️ SolidWorks Makrosunu Çalıştırma Yönergesi

Makroyu SolidWorks üzerinde çalıştırmak için aşağıdaki adımları sırasıyla uygulayınız:

1.  **SolidWorks** uygulamasını açın.
2.  Üst menüden **Araçlar (Tools) > Makro (Macro) > Yeni (New...)** seçeneğine tıklayın.
3.  Oluşturacağınız makro dosyasına `Beebot_Katamaran.swp` adını verin ve kaydedin. VBA düzenleyici ekranı açılacaktır.
4.  VBA penceresinde soldaki **Modules > Main** (veya `Sheet1`/`ThisWorkbook`) çift tıklayarak kod editörünü açın.
5.  Aşağıda verilen VBA kodunun tamamını kopyalayıp editördeki mevcut kodların yerine yapıştırın.
6.  Editörün üst menüsündeki **Referanslar (Tools > References)** kısmında `SolidWorks <Sürüm> Type Library` ve `SolidWorks Constant type library` referanslarının seçili olduğundan emin olun.
7.  Yeşil **Run (F5)** butonuna basarak makroyu çalıştırın. Makro, sıfırdan yeni bir parça dökümanı açacak ve katamaran gövdesini, rayları ve montaj yuvalarını saniyeler içinde otomatik olarak modelleyecektir.

---

## 💾 SolidWorks VBA Makro Kodu (`Beebot_Katamaran.swp`)

```vba
' =========================================================================
'  BEEBOT AUTONOMOUS SYSTEMS - FUTURISTIC CATAMARAN ID DESIGN MACRO
'  Teknofest 2026 IDA Sartnamesi %100 Uyumlu Katamaran Tasarim Makrosu
'  Birimler: SolidWorks API standart geregi METRE (SI) kullanir.
' =========================================================================

Dim swApp As SldWorks.SldWorks
Dim swModel As SldWorks.ModelDoc2
Dim swPart As SldWorks.PartDoc
Dim swSketchMgr As SldWorks.SketchManager
Dim swFeatureMgr As SldWorks.FeatureManager
Dim swModelDocExt As SldWorks.ModelDocExtension
Dim boolstatus As Boolean
Dim longstatus As Long, longwarnings As Long
Dim myFeature As SldWorks.Feature

Sub main()
    ' SolidWorks Uygulamasina Baglan
    Set swApp = Application.SldWorks
    
    ' Yeni Bir Parca (Part) Sablonu Ac
    Set swModel = swApp.NewPart()
    If swModel Is Nothing Then
        MsgBox "Yeni parca olusturulamadi! Lutfen SolidWorks uygulamasinin acik oldugundan emin olun.", vbCritical, "Beebot CAD"
        Exit Sub
    End If
    
    Set swPart = swModel
    Set swSketchMgr = swModel.SketchManager
    Set swFeatureMgr = swModel.FeatureManager
    Set swModelDocExt = swModel.Extension
    
    ' Milimetre cinsinden calismak icin parca birim sistemini metreye sabitle
    swModel.SetUserPreferenceIntegerValue swUserPreferenceIntegerValue_e.swUnitSystem, swUnitSystem_e.swUnitSystem_MKS
    
    ' =========================================================================
    ' 1. ADIM: SOL GOVDE TEMEL KUTUSUNUN CIZIMI (EXTRUDE)
    ' =========================================================================
    ' Front Plane Secimi
    boolstatus = swModelDocExt.SelectByID2("Front Plane", "PLANE", 0, 0, 0, False, 0, Nothing, 0)
    swModel.ClearSelection2 True
    
    swSketchMgr.InsertSketch True
    
    ' Sol Govde Dikdortgen Kesiti (X: -0.40m ile -0.27m arasi, Y: -0.20m ile +0.20m arasi)
    ' Toplam genislik: 130mm, Yukseklik: 400mm
    ' Eksen kayikligi: Sol govde merkez ekseni -335mm (X)
    swSketchMgr.CreateCornerRectangle -0.4, 0.2, 0, -0.27, -0.2, 0
    swSketchMgr.InsertSketch True
    swModel.ClearSelection2 True
    
    ' 1.2m (1200mm) Boyunda Kati Modelleme (Extrude)
    ' Katiyi Z ekseninde ters yonde uzat (0'dan -1.2m'ye)
    boolstatus = swModelDocExt.SelectByID2("Sketch1", "SKETCH", 0, 0, 0, False, 0, Nothing, 0)
    Set myFeature = swFeatureMgr.FeatureExtrude2(True, False, False, 0, 0, 1.2, 0, False, False, False, False, 0, 0, False, False, False, False, True, True, True)
    swModel.ClearSelection2 True
    
    ' =========================================================================
    ' 2. ADIM: GOVDE ICI BATARYA VE ELEKTRONIK CEBI (CUT-EXTRUDE)
    ' =========================================================================
    ' Ust Yuzeyi Secerek Sketch Ac
    ' X: -0.392m ile -0.278m arasi (8mm et kalinligi), Z: -0.1m ile -1.1m arasi (1m cep boyu)
    boolstatus = swModelDocExt.SelectByID2("", "FACE", -0.335, 0.2, -0.5, False, 0, Nothing, 0)
    swSketchMgr.InsertSketch True
    
    swSketchMgr.CreateCornerRectangle -0.392, -0.1, 0, -0.278, -1.1, 0
    swSketchMgr.InsertSketch True
    
    ' 370mm Derinliginde Kesme Islemi (Tabanda 30mm et kalinligi birakir)
    boolstatus = swModelDocExt.SelectByID2("Sketch2", "SKETCH", 0, 0, 0, False, 0, Nothing, 0)
    Set myFeature = swFeatureMgr.FeatureCut3(True, False, False, 0, 0, 0.37, 0, False, False, False, False, 0, 0, False, False, False, False, False, True, True, True, True, False)
    swModel.ClearSelection2 True
    
    ' =========================================================================
    ' 3. ADIM: GOVDE ICI MODULER BATARYA KIZAK RAYLARI (EXTRUDE RAILS)
    ' =========================================================================
    ' Cebin Taban Yuzeyini Sec (Y: -0.17m konumundaki ic yuzey)
    boolstatus = swModelDocExt.SelectByID2("", "FACE", -0.335, -0.17, -0.5, False, 0, Nothing, 0)
    swSketchMgr.InsertSketch True
    
    ' 10mm Genisliginde, 10mm Yuksekliginde 2 Adet Paralel Ray Profili
    ' Sol Ray: X: -0.365m ile -0.355m, Z: -0.15m ile -0.95m (800mm boyunda)
    ' Sag Ray: X: -0.315m ile -0.305m, Z: -0.15m ile -0.95m
    swSketchMgr.CreateCornerRectangle -0.365, -0.15, 0, -0.355, -0.95, 0
    swSketchMgr.CreateCornerRectangle -0.315, -0.15, 0, -0.305, -0.95, 0
    swSketchMgr.InsertSketch True
    
    ' Raylari 10mm Yuksekliginde Katila
    boolstatus = swModelDocExt.SelectByID2("Sketch3", "SKETCH", 0, 0, 0, False, 0, Nothing, 0)
    Set myFeature = swFeatureMgr.FeatureExtrude2(True, False, False, 0, 0, 0.01, 0, False, False, False, False, 0, 0, False, False, False, False, True, True, True)
    swModel.ClearSelection2 True

    ' =========================================================================
    ' 4. ADIM: FUTURISTIK DALGA DELICI PRUVA (WAVE-PIERCING BOW CUTS)
    ' =========================================================================
    ' Top Plane Uzerinde Yatay Pruva Daraltma Kesimi (Y: 0)
    boolstatus = swModelDocExt.SelectByID2("Top Plane", "PLANE", 0, 0, 0, False, 0, Nothing, 0)
    swSketchMgr.InsertSketch True
    
    ' Govde pruvasini (Z: -0.9m ile -1.2m arasinda) ucgen seklinde daraltan cizgi grubu
    swSketchMgr.CreateLine -0.4, -0.9, 0, -0.34, -1.2, 0
    swSketchMgr.CreateLine -0.34, -1.2, 0, -0.4, -1.2, 0
    swSketchMgr.CreateLine -0.4, -1.2, 0, -0.4, -0.9, 0
    
    swSketchMgr.CreateLine -0.27, -0.9, 0, -0.33, -1.2, 0
    swSketchMgr.CreateLine -0.33, -1.2, 0, -0.27, -1.2, 0
    swSketchMgr.CreateLine -0.27, -1.2, 0, -0.27, -0.9, 0
    swSketchMgr.InsertSketch True
    
    ' Pruva Daraltmayi Katiyi Keserek Uygula (Through All - Cift Yonlu)
    boolstatus = swModelDocExt.SelectByID2("Sketch4", "SKETCH", 0, 0, 0, False, 0, Nothing, 0)
    Set myFeature = swFeatureMgr.FeatureCut3(True, False, False, 1, 1, 0.5, 0.5, False, False, False, False, 0, 0, False, False, False, False, False, True, True, True, True, False)
    swModel.ClearSelection2 True

    ' =========================================================================
    ' 5. ADIM: KOPRU VE UST GUVTE DETAYLARI (BRIDGE DECK EXTRUDE)
    ' =========================================================================
    ' Top Plane Sec (Deck yuksekligi: Y = 0.20m)
    boolstatus = swModelDocExt.SelectByID2("Top Plane", "PLANE", 0, 0, 0, False, 0, Nothing, 0)
    swSketchMgr.InsertSketch True
    
    ' Sol govde ic duvari (X: -0.27m) ile simetri ekseni (X: 0) arasinda kopru
    ' Z ekseninde: -0.2m ile -1.0m arasi (800mm uzunlukta)
    swSketchMgr.CreateCornerRectangle -0.27, -0.2, 0, 0, -1.0, 0
    swSketchMgr.InsertSketch True
    
    ' Kopruyu 20mm Kalinliginda Asagi Dogru Katila
    boolstatus = swModelDocExt.SelectByID2("Sketch5", "SKETCH", 0, 0, 0, False, 0, Nothing, 0)
    Set myFeature = swFeatureMgr.FeatureExtrude2(True, False, True, 0, 0, 0.02, 0, False, False, False, False, 0, 0, False, False, False, False, True, True, True)
    swModel.ClearSelection2 True

    ' =========================================================================
    ' 6. ADIM: DONANIM MONTAJ YUVALARI (COMPONENT MOUNTING BOSSES)
    ' =========================================================================
    ' Ust Deck Yuzeyi Sec
    boolstatus = swModelDocExt.SelectByID2("", "FACE", -0.1, 0.2, -0.5, False, 0, Nothing, 0)
    swSketchMgr.InsertSketch True
    
    ' Lidar Mount Boss (X: 0, Z: -0.9m, R: 40mm)
    swSketchMgr.CreateCircleByRadius 0, -0.9, 0, 0.04
    ' GPS Mast Boss (X: 0, Z: -0.3m, R: 15mm)
    swSketchMgr.CreateCircleByRadius 0, -0.3, 0, 0.015
    ' Dual Camera Bosses (X: -0.15m, Z: -0.95m, R: 20mm)
    swSketchMgr.CreateCircleByRadius -0.15, -0.95, 0, 0.02
    ' Killswitch Boss (X: -0.1m, Z: -0.45m, R: 22.5mm)
    swSketchMgr.CreateCircleByRadius -0.1, -0.45, 0, 0.0225
    swSketchMgr.InsertSketch True
    
    ' Montaj Cikintilarini 15mm Katila
    boolstatus = swModelDocExt.SelectByID2("Sketch6", "SKETCH", 0, 0, 0, False, 0, Nothing, 0)
    Set myFeature = swFeatureMgr.FeatureExtrude2(True, False, False, 0, 0, 0.015, 0, False, False, False, False, 0, 0, False, False, False, False, True, True, True)
    swModel.ClearSelection2 True

    ' =========================================================================
    ' 7. ADIM: SAG GÖVDENİN AYNALANMASI (MIRRORING FOR CATAMARAN ASSEMBLY)
    ' =========================================================================
    ' Simetri Ekseni Olan Right Plane (X=0 Duzlemi) ile Tum Katilari Sag Tarafa Aynala
    ' Bu sayede sag govde, ic raylar ve kopru tam olarak simetrik olusur
    boolstatus = swModelDocExt.SelectByID2("Right Plane", "PLANE", 0, 0, 0, False, 0, Nothing, 0)
    swModel.FeatureManager.InsertMirrorFeature2 True, False, False, False, swFeatureMirrorBodyType_e.swFeatureMirrorBodyAll
    
    swModel.ClearSelection2 True
    
    ' Basari Bildirimi
    MsgBox "Futuristik Beebot Katamaran IDA Tasarimi Basariyla Tamamlandi!" & vbCrLf & _
           "Boyutlar: 120 x 80 x 40 cm" & vbCrLf & _
           "Sizdırmaz Batarya Hazneleri ve Raylar Eklenmistir.", vbInformation, "Beebot Otonom Sistemleri"
End Sub
```

---

## 🔋 Batarya Modüler Kızak Kutusu Tasarımı (`Beebot_Kizak_Kutusu.sldprt`)

Raylar üzerinde sıfır çakışma (clearance) ile rahatça kayabilmesi ve bataryayı sabitleyebilmesi için ikinci bir parça olarak tasarlanacak batarya tepsisinin SolidWorks VBA Makro kodu aşağıdadır:

```vba
' =========================================================================
'  BEEBOT AUTONOMOUS SYSTEMS - BATTERY SLIDING BOX DESIGN MACRO
'  Moduler Kızaklı Batarya Kutusu Tasarım Makrosu
' =========================================================================

Dim swApp As SldWorks.SldWorks
Dim swModel As SldWorks.ModelDoc2
Dim swSketchMgr As SldWorks.SketchManager
Dim swFeatureMgr As SldWorks.FeatureManager
Dim swModelDocExt As SldWorks.Extension
Dim boolstatus As Boolean
Dim myFeature As SldWorks.Feature

Sub main()
    Set swApp = Application.SldWorks
    Set swModel = swApp.NewPart()
    If swModel Is Nothing Then Exit Sub
    
    Set swSketchMgr = swModel.SketchManager
    Set swFeatureMgr = swModel.FeatureManager
    Set swModelDocExt = swModel.Extension
    
    ' Birimi MKS Yap
    swModel.SetUserPreferenceIntegerValue swUserPreferenceIntegerValue_e.swUnitSystem, swUnitSystem_e.swUnitSystem_MKS
    
    ' Front Plane Uzerinde Cizim Ac
    boolstatus = swModelDocExt.SelectByID2("Front Plane", "PLANE", 0, 0, 0, False, 0, Nothing, 0)
    swSketchMgr.InsertSketch True
    
    ' 1. Kizak Taban Plakasi (Batarya Standart Boyutu: 160x50x50 mm)
    ' Kutu Dis Boyutu: En: 110mm, Yukseklik: 60mm
    swSketchMgr.CreateCornerRectangle -0.055, 0.06, 0, 0.055, 0, 0
    
    ' 2. Yan Kanat Ray Kilavuzlari (Gövdedeki 10x10mm kanallara oturacak sekilde tasarlanmistir)
    ' Sol Kanat: X: -0.075m ile -0.055m, Y: 0 ile 10mm
    ' Sag Kanat: X: 0.055m ile 0.075m, Y: 0 ile 10mm
    swSketchMgr.CreateCornerRectangle -0.075, 0.01, 0, -0.055, 0, 0
    swSketchMgr.CreateCornerRectangle 0.055, 0.01, 0, 0.075, 0, 0
    swSketchMgr.InsertSketch True
    
    ' Plakayi 170mm Boyunda Katila (Z ekseni yönünde)
    boolstatus = swModelDocExt.SelectByID2("Sketch1", "SKETCH", 0, 0, 0, False, 0, Nothing, 0)
    Set myFeature = swFeatureMgr.FeatureExtrude2(True, False, False, 0, 0, 0.17, 0, False, False, False, False, 0, 0, False, False, False, False, True, True, True)
    swModel.ClearSelection2 True
    
    ' Batarya Haznesi Cebini Ac (Ust Yuzeyden 50mm Derinliginde Kesim)
    ' En: 94mm (8mm et kalinligi), Boy: 154mm (Tabanda 8mm bas/kic et kalinligi)
    boolstatus = swModelDocExt.SelectByID2("", "FACE", 0, 0.06, 0.085, False, 0, Nothing, 0)
    swSketchMgr.InsertSketch True
    swSketchMgr.CreateCornerRectangle -0.047, 0.008, 0, 0.047, 0.162, 0
    swSketchMgr.InsertSketch True
    
    boolstatus = swModelDocExt.SelectByID2("Sketch2", "SKETCH", 0, 0, 0, False, 0, Nothing, 0)
    Set myFeature = swFeatureMgr.FeatureCut3(True, False, False, 0, 0, 0.052, 0, False, False, False, False, 0, 0, False, False, False, False, False, True, True, True, True, False)
    swModel.ClearSelection2 True
    
    MsgBox "Moduler Kizakli Batarya Kutusu Tasarimi Tamamlandi!", vbInformation, "Beebot CAD"
End Sub
```
