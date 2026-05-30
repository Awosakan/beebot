# Beebot Katamaran İDA - SolidWorks Türkçe/İngilizce Uyumlu Makro Tasarım Kılavuzu

Bu doküman, SolidWorks'ün **Türkçe** veya **İngilizce** kurulumlarında herhangi bir adlandırma hatası almadan (Ön Düzlem / Front Plane, Çizim / Sketch vb. dil uyuşmazlıkları) hatasız çalışacak, sızdırmaz bölmeli ve modüler kızaklı fütüristik katamaran gövdesi VBA makro kodlarını ve kullanım yönergelerini içerir.

---

## 🛠️ SolidWorks Dil Uyuşmazlığı Sorununun Mühendislik Çözümü

SolidWorks API, varsayılan düzlemleri (`Front Plane`, `Top Plane`, `Right Plane`) ve yeni açılan çizimleri (`Sketch1`, `Sketch2`) varsayılan dil ayarlarına göre adlandırır. İngilizce dışındaki (örneğin Türkçe) kurulumlarda makrolar çalıştırıldığında `"Front Plane seçilemedi"` veya `"Sketch1 bulunamadı"` gibi hata mesajları vererek durur.

Bu sorunu çözmek için makro kodlarımız **Dil Bağımsız (Cross-Language)** çalışacak şekilde yeniden tasarlandı:
1.  **Düzlem Seçim Yardımcısı (`SelectPlane`):** Düzlemleri seçerken önce İngilizce adını (`Front Plane`), eğer başarısız olursa Türkçe adını (`Ön Düzlem`) otomatik olarak dener.
2.  **Otomatik Çizim Yeniden Adlandırma (`ActiveSketch.GetFeature().Name`):** Çizim açıldığı anda, SolidWorks'ün otomatik atadığı dili (Sketch veya Çizim) sorgulamaksızın, çizim özelliğine doğrudan bellek seviyesinden erişerek ismi `BeebotSketch1`, `BeebotSketch2` gibi benzersiz dil bağımsız isimlerle değiştirir. Bu sayede sonraki adımlarda çizimler güvenle seçilebilir.

---

## 💾 SolidWorks Türkçe/İngilizce Uyumlu Makro Kodu (`Beebot_Katamaran.swp`)

Aşağıdaki kodu kopyalayarak SolidWorks VBA editörüne yapıştırıp çalıştırabilirsiniz:

```vba
' =========================================================================
'  BEEBOT AUTONOMOUS SYSTEMS - FUTURISTIC CATAMARAN ID DESIGN MACRO
'  SolidWorks Turkce ve Ingilizce Kurulumlariyla %100 Uyumlu VBA Makrosu
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

' Dil Uyumlu Duzlem Secim Fonksiyonu (Front Plane / Ön Düzlem)
Function SelectPlane(swModelDocExt As SldWorks.ModelDocExtension, planeNameEnglish As String, planeNameTurkish As String) As Boolean
    Dim status As Boolean
    status = swModelDocExt.SelectByID2(planeNameEnglish, "PLANE", 0, 0, 0, False, 0, Nothing, 0)
    If Not status Then
        status = swModelDocExt.SelectByID2(planeNameTurkish, "PLANE", 0, 0, 0, False, 0, Nothing, 0)
    End If
    SelectPlane = status
End Function

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
    
    ' Parca birim sistemini metreye sabitle (SI unit)
    swModel.SetUserPreferenceIntegerValue swUserPreferenceIntegerValue_e.swUnitSystem, swUnitSystem_e.swUnitSystem_MKS
    
    ' =========================================================================
    ' 1. ADIM: SOL GOVDE TEMEL KUTUSUNUN CIZIMI (EXTRUDE)
    ' =========================================================================
    ' Front Plane / Ön Düzlem Secimi
    boolstatus = SelectPlane(swModelDocExt, "Front Plane", "Ön Düzlem")
    swModel.ClearSelection2 True
    
    swSketchMgr.InsertSketch True
    ' Cizim adini dil-bagimsiz olarak yeniden adlandir
    Dim swSketch1 As SldWorks.Sketch
    Set swSketch1 = swModel.SketchManager.ActiveSketch
    swSketch1.GetFeature().Name = "BeebotSketch1"
    
    ' Sol Govde Dikdortgen Kesiti (X: -0.40m ile -0.27m arasi, Y: -0.20m ile +0.20m arasi)
    swSketchMgr.CreateCornerRectangle -0.4, 0.2, 0, -0.27, -0.2, 0
    swSketchMgr.InsertSketch True
    swModel.ClearSelection2 True
    
    ' 1.2m (1200mm) Kati Modelleme (Extrude)
    boolstatus = swModelDocExt.SelectByID2("BeebotSketch1", "SKETCH", 0, 0, 0, False, 0, Nothing, 0)
    Set myFeature = swFeatureMgr.FeatureExtrude2(True, False, False, 0, 0, 1.2, 0, False, False, False, False, 0, 0, False, False, False, False, True, True, True)
    swModel.ClearSelection2 True
    
    ' =========================================================================
    ' 2. ADIM: GOVDE ICI BATARYA VE ELEKTRONIK CEBI (CUT-EXTRUDE)
    ' =========================================================================
    ' Ust Yuzeyi Secerek Sketch Ac
    boolstatus = swModelDocExt.SelectByID2("", "FACE", -0.335, 0.2, -0.5, False, 0, Nothing, 0)
    swSketchMgr.InsertSketch True
    Dim swSketch2 As SldWorks.Sketch
    Set swSketch2 = swModel.SketchManager.ActiveSketch
    swSketch2.GetFeature().Name = "BeebotSketch2"
    
    swSketchMgr.CreateCornerRectangle -0.392, -0.1, 0, -0.278, -1.1, 0
    swSketchMgr.InsertSketch True
    
    ' 370mm Derinliginde Kesme Islemi (Tabanda 30mm et kalinligi birakir)
    boolstatus = swModelDocExt.SelectByID2("BeebotSketch2", "SKETCH", 0, 0, 0, False, 0, Nothing, 0)
    Set myFeature = swFeatureMgr.FeatureCut3(True, False, False, 0, 0, 0.37, 0, False, False, False, False, 0, 0, False, False, False, False, False, True, True, True, True, False)
    swModel.ClearSelection2 True
    
    ' =========================================================================
    ' 3. ADIM: GOVDE ICI MODULER BATARYA KIZAK RAYLARI (EXTRUDE RAILS)
    ' =========================================================================
    ' Cebin Taban Yuzeyini Sec (Y: -0.17m konumundaki ic yuzey)
    boolstatus = swModelDocExt.SelectByID2("", "FACE", -0.335, -0.17, -0.5, False, 0, Nothing, 0)
    swSketchMgr.InsertSketch True
    Dim swSketch3 As SldWorks.Sketch
    Set swSketch3 = swModel.SketchManager.ActiveSketch
    swSketch3.GetFeature().Name = "BeebotSketch3"
    
    ' 10mm Genisliginde, 10mm Yuksekliginde 2 Adet Paralel Ray Profili
    swSketchMgr.CreateCornerRectangle -0.365, -0.15, 0, -0.355, -0.95, 0
    swSketchMgr.CreateCornerRectangle -0.315, -0.15, 0, -0.305, -0.95, 0
    swSketchMgr.InsertSketch True
    
    ' Raylari 10mm Yuksekliginde Katila
    boolstatus = swModelDocExt.SelectByID2("BeebotSketch3", "SKETCH", 0, 0, 0, False, 0, Nothing, 0)
    Set myFeature = swFeatureMgr.FeatureExtrude2(True, False, False, 0, 0, 0.01, 0, False, False, False, False, 0, 0, False, False, False, False, True, True, True)
    swModel.ClearSelection2 True

    ' =========================================================================
    ' 4. ADIM: FUTURISTIK DALGA DELICI PRUVA (WAVE-PIERCING BOW CUTS)
    ' =========================================================================
    ' Top Plane / Üst Düzlem Secimi
    boolstatus = SelectPlane(swModelDocExt, "Top Plane", "Üst Düzlem")
    swSketchMgr.InsertSketch True
    Dim swSketch4 As SldWorks.Sketch
    Set swSketch4 = swModel.SketchManager.ActiveSketch
    swSketch4.GetFeature().Name = "BeebotSketch4"
    
    ' Pruva (Z: -0.9m ile -1.2m arasinda) ucgen daraltma cizgileri
    swSketchMgr.CreateLine -0.4, -0.9, 0, -0.34, -1.2, 0
    swSketchMgr.CreateLine -0.34, -1.2, 0, -0.4, -1.2, 0
    swSketchMgr.CreateLine -0.4, -1.2, 0, -0.4, -0.9, 0
    
    swSketchMgr.CreateLine -0.27, -0.9, 0, -0.33, -1.2, 0
    swSketchMgr.CreateLine -0.33, -1.2, 0, -0.27, -1.2, 0
    swSketchMgr.CreateLine -0.27, -1.2, 0, -0.27, -0.9, 0
    swSketchMgr.InsertSketch True
    
    ' Cift Yonlu Kesim
    boolstatus = swModelDocExt.SelectByID2("BeebotSketch4", "SKETCH", 0, 0, 0, False, 0, Nothing, 0)
    Set myFeature = swFeatureMgr.FeatureCut3(True, False, False, 1, 1, 0.5, 0.5, False, False, False, False, 0, 0, False, False, False, False, False, True, True, True, True, False)
    swModel.ClearSelection2 True

    ' =========================================================================
    ' 5. ADIM: GUVENLIK KOPRUSU VE UST DECK (BRIDGE DECK EXTRUDE)
    ' =========================================================================
    ' Top Plane / Üst Düzlem Secimi
    boolstatus = SelectPlane(swModelDocExt, "Top Plane", "Üst Düzlem")
    swSketchMgr.InsertSketch True
    Dim swSketch5 As SldWorks.Sketch
    Set swSketch5 = swModel.SketchManager.ActiveSketch
    swSketch5.GetFeature().Name = "BeebotSketch5"
    
    ' Kopru Dikdortgen Cizimi
    swSketchMgr.CreateCornerRectangle -0.27, -0.2, 0, 0, -1.0, 0
    swSketchMgr.InsertSketch True
    
    ' Asagi dogru 20mm Katila
    boolstatus = swModelDocExt.SelectByID2("BeebotSketch5", "SKETCH", 0, 0, 0, False, 0, Nothing, 0)
    Set myFeature = swFeatureMgr.FeatureExtrude2(True, False, True, 0, 0, 0.02, 0, False, False, False, False, 0, 0, False, False, False, False, True, True, True)
    swModel.ClearSelection2 True

    ' =========================================================================
    ' 6. ADIM: DONANIM MONTAJ YUVALARI (COMPONENT MOUNTING BOSSES)
    ' =========================================================================
    ' Ust Deck Yuzeyi Sec
    boolstatus = swModelDocExt.SelectByID2("", "FACE", -0.1, 0.2, -0.5, False, 0, Nothing, 0)
    swSketchMgr.InsertSketch True
    Dim swSketch6 As SldWorks.Sketch
    Set swSketch6 = swModel.SketchManager.ActiveSketch
    swSketch6.GetFeature().Name = "BeebotSketch6"
    
    ' Lidar, GPS, Kamera ve Killswitch dairesel cikintilari
    swSketchMgr.CreateCircleByRadius 0, -0.9, 0, 0.04
    swSketchMgr.CreateCircleByRadius 0, -0.3, 0, 0.015
    swSketchMgr.CreateCircleByRadius -0.15, -0.95, 0, 0.02
    swSketchMgr.CreateCircleByRadius -0.1, -0.45, 0, 0.0225
    swSketchMgr.InsertSketch True
    
    ' 15mm Katila
    boolstatus = swModelDocExt.SelectByID2("BeebotSketch6", "SKETCH", 0, 0, 0, False, 0, Nothing, 0)
    Set myFeature = swFeatureMgr.FeatureExtrude2(True, False, False, 0, 0, 0.015, 0, False, False, False, False, 0, 0, False, False, False, False, True, True, True)
    swModel.ClearSelection2 True

    ' =========================================================================
    ' 7. ADIM: SAG GÖVDENİN AYNALANMASI (MIRRORING ACROSS SYMMETRY PLANE)
    ' =========================================================================
    ' Simetri Duzlemi (Right Plane / Sağ Düzlem) Secimi ve Aynalama
    boolstatus = SelectPlane(swModelDocExt, "Right Plane", "Sağ Düzlem")
    swModel.FeatureManager.InsertMirrorFeature2 True, False, False, False, swFeatureMirrorBodyType_e.swFeatureMirrorBodyAll
    
    swModel.ClearSelection2 True
    
    MsgBox "Futuristik Beebot Katamaran IDA Tasarimi Basariyla Tamamlandi!" & vbCrLf & _
           "Boyutlar: 120 x 80 x 40 cm" & vbCrLf & _
           "Sizdirmaz Batarya Hazneleri ve Raylar Eklenmistir.", vbInformation, "Beebot Otonom Sistemleri"
End Sub
```

---

## 🔋 Türkçe/İngilizce Uyumlu Batarya Kızak Kutusu Makrosu (`Beebot_Kizak_Kutusu.swp`)

```vba
' =========================================================================
'  BEEBOT AUTONOMOUS SYSTEMS - BATTERY SLIDING BOX DESIGN MACRO
'  SolidWorks Turkce ve Ingilizce Kurulumlariyla %100 Uyumlu Ray Kutusu Makrosu
' =========================================================================

Dim swApp As SldWorks.SldWorks
Dim swModel As SldWorks.ModelDoc2
Dim swSketchMgr As SldWorks.SketchManager
Dim swFeatureMgr As SldWorks.FeatureManager
Dim swModelDocExt As SldWorks.Extension
Dim boolstatus As Boolean
Dim myFeature As SldWorks.Feature

' Duzlem Secim Fonksiyonu
Function SelectPlane(swModelDocExt As SldWorks.Extension, planeNameEnglish As String, planeNameTurkish As String) As Boolean
    Dim status As Boolean
    status = swModelDocExt.SelectByID2(planeNameEnglish, "PLANE", 0, 0, 0, False, 0, Nothing, 0)
    If Not status Then
        status = swModelDocExt.SelectByID2(planeNameTurkish, "PLANE", 0, 0, 0, False, 0, Nothing, 0)
    End If
    SelectPlane = status
End Function

Sub main()
    Set swApp = Application.SldWorks
    Set swModel = swApp.NewPart()
    If swModel Is Nothing Then Exit Sub
    
    Set swSketchMgr = swModel.SketchManager
    Set swFeatureMgr = swModel.FeatureManager
    Set swModelDocExt = swModel.Extension
    
    ' Birimi MKS Yap
    swModel.SetUserPreferenceIntegerValue swUserPreferenceIntegerValue_e.swUnitSystem, swUnitSystem_e.swUnitSystem_MKS
    
    ' Front Plane / Ön Düzlem Secimi
    boolstatus = SelectPlane(swModelDocExt, "Front Plane", "Ön Düzlem")
    swSketchMgr.InsertSketch True
    Dim swSketch1 As SldWorks.Sketch
    Set swSketch1 = swModel.SketchManager.ActiveSketch
    swSketch1.GetFeature().Name = "BeebotBoxSketch1"
    
    ' 160x50x50mm batarya kutusu taban cizimi ve yan kanatlar
    swSketchMgr.CreateCornerRectangle -0.055, 0.06, 0, 0.055, 0, 0
    swSketchMgr.CreateCornerRectangle -0.075, 0.01, 0, -0.055, 0, 0
    swSketchMgr.CreateCornerRectangle 0.055, 0.01, 0, 0.075, 0, 0
    swSketchMgr.InsertSketch True
    
    ' Plakayi 170mm Boyunda Katila
    boolstatus = swModelDocExt.SelectByID2("BeebotBoxSketch1", "SKETCH", 0, 0, 0, False, 0, Nothing, 0)
    Set myFeature = swFeatureMgr.FeatureExtrude2(True, False, False, 0, 0, 0.17, 0, False, False, False, False, 0, 0, False, False, False, False, True, True, True)
    swModel.ClearSelection2 True
    
    ' Ust Yuzeyden Cebi Kes
    boolstatus = swModelDocExt.SelectByID2("", "FACE", 0, 0.06, 0.085, False, 0, Nothing, 0)
    swSketchMgr.InsertSketch True
    Dim swSketch2 As SldWorks.Sketch
    Set swSketch2 = swModel.SketchManager.ActiveSketch
    swSketch2.GetFeature().Name = "BeebotBoxSketch2"
    
    swSketchMgr.CreateCornerRectangle -0.047, 0.008, 0, 0.047, 0.162, 0
    swSketchMgr.InsertSketch True
    
    boolstatus = swModelDocExt.SelectByID2("BeebotBoxSketch2", "SKETCH", 0, 0, 0, False, 0, Nothing, 0)
    Set myFeature = swFeatureMgr.FeatureCut3(True, False, False, 0, 0, 0.052, 0, False, False, False, False, 0, 0, False, False, False, False, False, True, True, True, True, False)
    swModel.ClearSelection2 True
    
    MsgBox "Moduler Kizakli Batarya Kutusu Tasarimi Tamamlandi!", vbInformation, "Beebot CAD"
End Sub
```
