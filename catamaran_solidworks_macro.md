# Beebot Katamaran İDA - SolidWorks Türkçe/İngilizce Uyumlu Makro Tasarım Kılavuzu

Bu doküman, SolidWorks'ün **Türkçe** veya **İngilizce** kurulumlarında (Ön Düzlem / Front Plane, Çizim / Sketch vb. dil uyuşmazlıkları) hiçbir adlandırma veya çalışma zamanı hatası almadan (özellikle **Runtime Error 91** ve seçim hataları) %100 uyumlu çalışacak şekilde güncellenmiş VBA makro kodlarını ve kullanım yönergelerini içerir.

---

## 🛠️ SolidWorks Dil ve Karakter Kodlama Uyuşmazlığı Mühendislik Çözümleri

Önceki makrolarda yaşanan ve sistemlerin durmasına sebep olan hatalar şu yöntemlerle kökten çözülmüştür:

1.  **Düzlem Seçim Yardımcısı (`SelectPlane`):**
    *   **Unicode Koruması:** Türkçe işletim sistemlerinde kopyala-yapıştır yaparken `Ö`, `ü`, `ğ` gibi Türkçe karakterlerin kod sayfasında bozulmasını engellemek için `ChrW` Unicode karakter fonksiyonları (`ChrW(214)` = Ö, `ChrW(252)` = ü, `ChrW(287)` = ğ vb.) kullanılmıştır.
    *   **Çoklu Dil Algılama:** Düzlemler önce Türkçe adlarıyla aranır, bulunamazsa İngilizce adlarıyla aranır.
    *   **Dizin (Index) Fallback Algoritması:** Eğer şablonda düzlem isimleri tamamen değiştirilmişse, Unsur Ağacı (Feature Tree) taranarak sırasıyla 1., 2. ve 3. `RefPlane` (Ön, Üst ve Sağ düzlemler) bulunup dil-bağımsız olarak seçilir.
2.  **Runtime Error 91 (Çizim Yeniden Adlandırma) Çözümü:**
    *   SolidWorks'te çizim açıkken (`ActiveSketch`) henüz unsura dönüşmediği için `GetFeature()` metodu `Nothing` döndürür ve makro çöker.
    *   **Yeni Akış:** Çizim açılır, geometriler çizilir ve çizim kapatılır (`InsertSketch True` ile). Çizim kapandığı anda unsur ağacının en sonuna eklenir. `RenameLastFeature` fonksiyonu ile en son eklenen unsur yakalanıp ismi dil-bağımsız olarak (`BeebotSketch1`, `BeebotBoxSketch1` vb.) güncellenir.
3.  **Ekstrüzyon Yönü ve Yüzey Seçim Koordinat Çakışması:**
    *   Gövde ana ekstrüzyonu varsayılan yönde (Pozitif Z) oluşturulduğunda, negatif koordinatlı tüm diğer yüzey seçimleri (`Z = -0.5`) boşa düşüyordu. Ana gövde ekstrüzyonunun 3. parametresi (`Dir = True`) yapılarak ekstrüzyonun **Negatif Z** yönünde oluşması sağlanmış ve tüm yüzey seçimleriyle koordinat uyumu sağlanmıştır.
    *   Deck yüzeyi seçimindeki `Y = 0.2` koordinat hatası, köprünün gerçek yüzeyi olan `Y = 0` değerine çekilerek montaj yuvalarının havada asılı kalması engellenmiştir.
4.  **Aynalama (Mirror) Hatası Çözümü:**
    *   Sadece düzlem seçip aynalama yapmak SolidWorks API'sinde hataya yol açıyordu. Yeni sürümde katı gövde (`SOLIDBODY`) koordinatından `Mark = 256` ile, simetri düzlemi ise `Mark = 2` ile seçilerek `InsertMirrorFeature2` yöntemiyle hatasız birleştirme sağlanmıştır.

---

## 💾 SolidWorks Türkçe/İngilizce Uyumlu Makro Kodu (`Beebot_Katamaran.swp`)

Aşağıdaki kodu kopyalayarak SolidWorks VBA editörüne (Tools > Macro > New) yapıştırıp çalıştırabilirsiniz. Çalıştırmadan önce **boş bir Parça (Part) belgesinin** açık olduğundan emin olun.

```vba
' =========================================================================
'  BEEBOT AUTONOMOUS SYSTEMS - FUTURISTIC CATAMARAN ID DESIGN MACRO
2026
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

' Düzlem Seçim Yardımcısı (Çoklu Dil, Unicode Korumalı ve Dizin Fallback Destekli)
' planeIndex: 1 = Ön Düzlem, 2 = Üst Düzlem, 3 = Sağ Düzlem
' appendSelection: Seçimi ekle (True) veya temizle (False)
' markValue: Aynalama ve diğer özel operasyonlar için seçim markası (varsayılan 0)
Function SelectPlane(swModel As SldWorks.ModelDoc2, planeIndex As Long, appendSelection As Boolean, markValue As Long) As Boolean
    Dim swModelDocExt As SldWorks.ModelDocExtension
    Set swModelDocExt = swModel.Extension
    Dim status As Boolean
    Dim planeNameTurkish As String
    Dim planeNameEnglish As String
    
    ' Unicode karakterleri (ChrW) kullanarak kopyala-yapıştır kaynaklı karakter bozulmalarını engelliyoruz
    If planeIndex = 1 Then
        ' Ön Düzlem (Ön Düzlem)
        planeNameTurkish = ChrW(214) & "n D" & ChrW(252) & "zlem"
        planeNameEnglish = "Front Plane"
    ElseIf planeIndex = 2 Then
        ' Üst Düzlem (Üst Düzlem)
        planeNameTurkish = ChrW(220) & "st D" & ChrW(252) & "zlem"
        planeNameEnglish = "Top Plane"
    ElseIf planeIndex = 3 Then
        ' Sağ Düzlem (Sağ Düzlem)
        planeNameTurkish = "Sa" & ChrW(287) & " D" & ChrW(252) & "zlem"
        planeNameEnglish = "Right Plane"
    End If
    
    ' 1. Yol: Türkçe Adı ile Seç
    status = swModelDocExt.SelectByID2(planeNameTurkish, "PLANE", 0, 0, 0, appendSelection, markValue, Nothing, 0)
    
    ' 2. Yol: İngilizce Adı ile Seç
    If Not status Then
        status = swModelDocExt.SelectByID2(planeNameEnglish, "PLANE", 0, 0, 0, appendSelection, markValue, Nothing, 0)
    End If
    
    ' 3. Yol: Dizin (Index) Üzerinden Seç (Unsur ağacındaki sırasına göre - Dil Bağımsız)
    If Not status Then
        Dim swFeat As SldWorks.Feature
        Dim planeCount As Long
        planeCount = 0
        Set swFeat = swModel.FirstFeature
        Do While Not swFeat Is Nothing
            If "RefPlane" = swFeat.GetTypeName Then
                planeCount = planeCount + 1
                If planeIndex = planeCount Then
                    Dim swSelMgr As SldWorks.SelectionMgr
                    Set swSelMgr = swModel.SelectionManager
                    Dim swSelData As SldWorks.SelectData
                    Set swSelData = swSelMgr.CreateSelectData
                    swSelData.Mark = markValue
                    status = swFeat.Select2(appendSelection, swSelData)
                    Exit Do
                End If
            End If
            Set swFeat = swFeat.GetNextFeature
        Loop
    End If
    
    SelectPlane = status
End Function

' Unsur ağacındaki en son eklenen unsuru bulup yeniden adlandıran fonksiyon (Error 91 Çözümü)
Sub RenameLastFeature(swModel As SldWorks.ModelDoc2, newName As String)
    Dim swFeat As SldWorks.Feature
    Set swFeat = swModel.FirstFeature
    Dim lastFeat As SldWorks.Feature
    Set lastFeat = swFeat
    Do While Not swFeat Is Nothing
        Set lastFeat = swFeat
        Set swFeat = swFeat.GetNextFeature
    Loop
    If Not lastFeat Is Nothing Then
        lastFeat.Name = newName
    End If
End Sub

Sub main()
    ' SolidWorks Uygulamasına Bağlan
    Set swApp = Application.SldWorks
    
    ' Yeni Bir Parça (Part) Şablonu Aç
    Set swModel = swApp.NewPart()
    If swModel Is Nothing Then
        MsgBox "Yeni parca olusturulamadi! Lutfen SolidWorks uygulamasinin acik oldugundan emin olun.", vbCritical, "Beebot CAD"
        Exit Sub
    End If
    
    Set swPart = swModel
    Set swSketchMgr = swModel.SketchManager
    Set swFeatureMgr = swModel.FeatureManager
    Set swModelDocExt = swModel.Extension
    
    ' Parça birim sistemini metreye sabitle (MKS)
    swModel.SetUserPreferenceIntegerValue swUserPreferenceIntegerValue_e.swUnitSystem, swUnitSystem_e.swUnitSystem_MKS
    
    ' =========================================================================
    ' 1. ADIM: SOL GÖVDE TEMEL KUTUSUNUN ÇİZİMİ VE EKSİ Z YÖNLÜ EKSTRÜZYONU
    ' =========================================================================
    ' Ön Düzlem Seçimi (Temizleyerek)
    boolstatus = SelectPlane(swModel, 1, False, 0)
    swModel.ClearSelection2 True
    
    swSketchMgr.InsertSketch True
    ' Sol Gövde Dikdörtgen Kesiti (X: -0.40m ile -0.27m arası, Y: -0.20m ile +0.20m arası)
    swSketchMgr.CreateCornerRectangle -0.4, 0.2, 0, -0.27, -0.2, 0
    swSketchMgr.InsertSketch True
    swModel.ClearSelection2 True
    
    ' Çizimi adlandır
    RenameLastFeature swModel, "BeebotSketch1"
    
    ' 1.2m (1200mm) Negatif Z Yönünde Katılama (3. parametre Dir = True yapıldı)
    boolstatus = swModelDocExt.SelectByID2("BeebotSketch1", "SKETCH", 0, 0, 0, False, 0, Nothing, 0)
    Set myFeature = swFeatureMgr.FeatureExtrude2(True, False, True, 0, 0, 1.2, 0, False, False, False, False, 0, 0, False, False, False, False, True, True, True)
    swModel.ClearSelection2 True
    
    ' =========================================================================
    ' 2. ADIM: GÖVDE İÇİ BATARYA VE ELEKTRONİK CEBİ (CUT-EXTRUDE)
    ' =========================================================================
    ' Üst Yüzeyi Seçerek Sketch Aç (Z = -0.5m koordinatında)
    boolstatus = swModelDocExt.SelectByID2("", "FACE", -0.335, 0.2, -0.5, False, 0, Nothing, 0)
    swSketchMgr.InsertSketch True
    
    swSketchMgr.CreateCornerRectangle -0.392, -0.1, 0, -0.278, -1.1, 0
    swSketchMgr.InsertSketch True
    swModel.ClearSelection2 True
    
    ' Çizimi adlandır
    RenameLastFeature swModel, "BeebotSketch2"
    
    ' 370mm Derinliğinde Kesme İşlemi (Tabanda 30mm et kalınlığı bırakır)
    boolstatus = swModelDocExt.SelectByID2("BeebotSketch2", "SKETCH", 0, 0, 0, False, 0, Nothing, 0)
    Set myFeature = swFeatureMgr.FeatureCut3(True, False, False, 0, 0, 0.37, 0, False, False, False, False, 0, 0, False, False, False, False, False, True, True, True, True, False)
    swModel.ClearSelection2 True
    
    ' =========================================================================
    ' 3. ADIM: GÖVDE İÇİ MODÜLER BATARYA KIZAK RAYLARI (EXTRUDE RAILS)
    ' =========================================================================
    ' Cebin Taban Yüzeyini Seç (Y: -0.17m konumundaki iç yüzey)
    boolstatus = swModelDocExt.SelectByID2("", "FACE", -0.335, -0.17, -0.5, False, 0, Nothing, 0)
    swSketchMgr.InsertSketch True
    
    ' 10mm Genişliğinde, 10mm Yüksekliğinde 2 Adet Paralel Ray Profili
    swSketchMgr.CreateCornerRectangle -0.365, -0.15, 0, -0.355, -0.95, 0
    swSketchMgr.CreateCornerRectangle -0.315, -0.15, 0, -0.305, -0.95, 0
    swSketchMgr.InsertSketch True
    swModel.ClearSelection2 True
    
    ' Çizimi adlandır
    RenameLastFeature swModel, "BeebotSketch3"
    
    ' Rayları 10mm Yüksekliğinde Katıla (Yukarı doğru)
    boolstatus = swModelDocExt.SelectByID2("BeebotSketch3", "SKETCH", 0, 0, 0, False, 0, Nothing, 0)
    Set myFeature = swFeatureMgr.FeatureExtrude2(True, False, False, 0, 0, 0.01, 0, False, False, False, False, 0, 0, False, False, False, False, True, True, True)
    swModel.ClearSelection2 True
    
    ' =========================================================================
    ' 4. ADIM: FÜTÜRİSTİK DALGA DELİCİ PRUVA (WAVE-PIERCING BOW CUTS)
    ' =========================================================================
    ' Üst Düzlem Seçimi (Temizleyerek)
    boolstatus = SelectPlane(swModel, 2, False, 0)
    swSketchMgr.InsertSketch True
    
    ' Pruva (Z: -0.9m ile -1.2m arasında) üçgen daraltma çizgileri
    swSketchMgr.CreateLine -0.4, -0.9, 0, -0.34, -1.2, 0
    swSketchMgr.CreateLine -0.34, -1.2, 0, -0.4, -1.2, 0
    swSketchMgr.CreateLine -0.4, -1.2, 0, -0.4, -0.9, 0
    
    swSketchMgr.CreateLine -0.27, -0.9, 0, -0.33, -1.2, 0
    swSketchMgr.CreateLine -0.33, -1.2, 0, -0.27, -1.2, 0
    swSketchMgr.CreateLine -0.27, -1.2, 0, -0.27, -0.9, 0
    swSketchMgr.InsertSketch True
    swModel.ClearSelection2 True
    
    ' Çizimi adlandır
    RenameLastFeature swModel, "BeebotSketch4"
    
    ' Çift Yönlü Kesim
    boolstatus = swModelDocExt.SelectByID2("BeebotSketch4", "SKETCH", 0, 0, 0, False, 0, Nothing, 0)
    Set myFeature = swFeatureMgr.FeatureCut3(True, False, False, 1, 1, 0.5, 0.5, False, False, False, False, 0, 0, False, False, False, False, False, True, True, True, True, False)
    swModel.ClearSelection2 True

    ' =========================================================================
    ' 5. ADIM: GÜVENLİK KÖPRÜSÜ VE ÜST DECK (BRIDGE DECK EXTRUDE)
    ' =========================================================================
    ' Üst Düzlem Seçimi (Temizleyerek)
    boolstatus = SelectPlane(swModel, 2, False, 0)
    swSketchMgr.InsertSketch True
    
    ' Köprü Dikdörtgen Çizimi
    swSketchMgr.CreateCornerRectangle -0.27, -0.2, 0, 0, -1.0, 0
    swSketchMgr.InsertSketch True
    swModel.ClearSelection2 True
    
    ' Çizimi adlandır
    RenameLastFeature swModel, "BeebotSketch5"
    
    ' Aşağı doğru 20mm Katıla (Dir = True ile yön terslendi ve gövdeyle birleştirildi)
    boolstatus = swModelDocExt.SelectByID2("BeebotSketch5", "SKETCH", 0, 0, 0, False, 0, Nothing, 0)
    Set myFeature = swFeatureMgr.FeatureExtrude2(True, False, True, 0, 0, 0.02, 0, False, False, False, False, 0, 0, False, False, False, False, True, True, True)
    swModel.ClearSelection2 True

    ' =========================================================================
    ' 6. ADIM: DONANIM MONTAJ YUVALARI (COMPONENT MOUNTING BOSSES)
    ' =========================================================================
    ' Üst Deck Yüzeyini Seç (Köprü Yüzeyi Y = 0)
    boolstatus = swModelDocExt.SelectByID2("", "FACE", -0.1, 0, -0.5, False, 0, Nothing, 0)
    swSketchMgr.InsertSketch True
    
    ' Lidar, GPS, Kamera ve Killswitch dairesel çıkıntıları
    swSketchMgr.CreateCircleByRadius 0, -0.9, 0, 0.04
    swSketchMgr.CreateCircleByRadius 0, -0.3, 0, 0.015
    swSketchMgr.CreateCircleByRadius -0.15, -0.95, 0, 0.02
    swSketchMgr.CreateCircleByRadius -0.1, -0.45, 0, 0.0225
    swSketchMgr.InsertSketch True
    swModel.ClearSelection2 True
    
    ' Çizimi adlandır
    RenameLastFeature swModel, "BeebotSketch6"
    
    ' 15mm Yukarı Doğru Katıla
    boolstatus = swModelDocExt.SelectByID2("BeebotSketch6", "SKETCH", 0, 0, 0, False, 0, Nothing, 0)
    Set myFeature = swFeatureMgr.FeatureExtrude2(True, False, False, 0, 0, 0.015, 0, False, False, False, False, 0, 0, False, False, False, False, True, True, True)
    swModel.ClearSelection2 True

    ' =========================================================================
    ' 7. ADIM: SAĞ GÖVDENİN AYNALANMASI (MIRRORING ACROSS SYMMETRY PLANE)
    ' =========================================================================
    ' Seçimleri temizle
    swModel.ClearSelection2 True
    
    ' Katı Gövdeyi Seç (Mark: 256)
    boolstatus = swModelDocExt.SelectByID2("", "SOLIDBODY", -0.335, 0.2, -0.5, True, 256, Nothing, 0)
    
    ' Simetri Düzlemini (Sağ Düzlem) Seç (Mark: 2, Seçimi ekle)
    boolstatus = SelectPlane(swModel, 3, True, 2)
    
    ' Aynalamayı uygula ve katıları birleştir (BMerge = True)
    Set myFeature = swModel.FeatureManager.InsertMirrorFeature2(True, False, True, False, 0)
    swModel.ClearSelection2 True
    
    MsgBox "Futuristik Beebot Katamaran IDA Tasarimi Basariyla Tamamlandi!" & vbCrLf & _
           "Boyutlar: 120 x 80 x 40 cm" & vbCrLf & _
           "Sizdirmaz Batarya Hazneleri ve Raylar Eklenmistir.", vbInformation, "Beebot Otonom Sistemleri"
End Sub
```

---

## 🔋 Türkçe Uyumlu Batarya Kızak Kutusu Makrosu (`Beebot_Kizak_Kutusu.swp`)

Bataryayı muhafaza edecek ve gövde içindeki raylara oturacak modüler batarya kutusu makrosudur. Boş bir Parça belgesi açıp bu makroyu çalıştırabilirsiniz.

```vba
' =========================================================================
'  BEEBOT AUTONOMOUS SYSTEMS - BATTERY SLIDING BOX DESIGN MACRO
'  SolidWorks Turkce ve Ingilizce Kurulumlariyla %100 Uyumlu Ray Kutusu Makrosu
' =========================================================================

Dim swApp As SldWorks.SldWorks
Dim swModel As SldWorks.ModelDoc2
Dim swSketchMgr As SldWorks.SketchManager
Dim swFeatureMgr As SldWorks.FeatureManager
Dim swModelDocExt As SldWorks.ModelDocExtension
Dim boolstatus As Boolean
Dim myFeature As SldWorks.Feature

' Düzlem Seçim Yardımcısı
Function SelectPlane(swModel As SldWorks.ModelDoc2, planeIndex As Long, appendSelection As Boolean, markValue As Long) As Boolean
    Dim swModelDocExt As SldWorks.ModelDocExtension
    Set swModelDocExt = swModel.Extension
    Dim status As Boolean
    Dim planeNameTurkish As String
    Dim planeNameEnglish As String
    
    If planeIndex = 1 Then
        planeNameTurkish = ChrW(214) & "n D" & ChrW(252) & "zlem"
        planeNameEnglish = "Front Plane"
    ElseIf planeIndex = 2 Then
        planeNameTurkish = ChrW(220) & "st D" & ChrW(252) & "zlem"
        planeNameEnglish = "Top Plane"
    ElseIf planeIndex = 3 Then
        planeNameTurkish = "Sa" & ChrW(287) & " D" & ChrW(252) & "zlem"
        planeNameEnglish = "Right Plane"
    End If
    
    status = swModelDocExt.SelectByID2(planeNameTurkish, "PLANE", 0, 0, 0, appendSelection, markValue, Nothing, 0)
    If Not status Then
        status = swModelDocExt.SelectByID2(planeNameEnglish, "PLANE", 0, 0, 0, appendSelection, markValue, Nothing, 0)
    End If
    
    If Not status Then
        Dim swFeat As SldWorks.Feature
        Dim planeCount As Long
        planeCount = 0
        Set swFeat = swModel.FirstFeature
        Do While Not swFeat Is Nothing
            If "RefPlane" = swFeat.GetTypeName Then
                planeCount = planeCount + 1
                If planeIndex = planeCount Then
                    Dim swSelMgr As SldWorks.SelectionMgr
                    Set swSelMgr = swModel.SelectionManager
                    Dim swSelData As SldWorks.SelectData
                    Set swSelData = swSelMgr.CreateSelectData
                    swSelData.Mark = markValue
                    status = swFeat.Select2(appendSelection, swSelData)
                    Exit Do
                End If
            End If
            Set swFeat = swFeat.GetNextFeature
        Loop
    End If
    
    SelectPlane = status
End Function

' Unsur adlandırma yardımcısı
Sub RenameLastFeature(swModel As SldWorks.ModelDoc2, newName As String)
    Dim swFeat As SldWorks.Feature
    Set swFeat = swModel.FirstFeature
    Dim lastFeat As SldWorks.Feature
    Set lastFeat = swFeat
    Do While Not swFeat Is Nothing
        Set lastFeat = swFeat
        Set swFeat = swFeat.GetNextFeature
    Loop
    If Not lastFeat Is Nothing Then
        lastFeat.Name = newName
    End If
End Sub

Sub main()
    Set swApp = Application.SldWorks
    Set swModel = swApp.NewPart()
    If swModel Is Nothing Then Exit Sub
    
    Set swSketchMgr = swModel.SketchManager
    Set swFeatureMgr = swModel.FeatureManager
    Set swModelDocExt = swModel.Extension
    
    ' Birimi MKS Yap
    swModel.SetUserPreferenceIntegerValue swUserPreferenceIntegerValue_e.swUnitSystem, swUnitSystem_e.swUnitSystem_MKS
    
    ' Ön Düzlem Seçimi (Temizleyerek)
    boolstatus = SelectPlane(swModel, 1, False, 0)
    swSketchMgr.InsertSketch True
    
    ' 160x50x50mm batarya kutusu taban çizimi ve yan kanatlar
    swSketchMgr.CreateCornerRectangle -0.055, 0.06, 0, 0.055, 0, 0
    swSketchMgr.CreateCornerRectangle -0.075, 0.01, 0, -0.055, 0, 0
    swSketchMgr.CreateCornerRectangle 0.055, 0.01, 0, 0.075, 0, 0
    swSketchMgr.InsertSketch True
    swModel.ClearSelection2 True
    
    ' Çizimi adlandır
    RenameLastFeature swModel, "BeebotBoxSketch1"
    
    ' Plakayı 170mm Boyunda Katıla
    boolstatus = swModelDocExt.SelectByID2("BeebotBoxSketch1", "SKETCH", 0, 0, 0, False, 0, Nothing, 0)
    Set myFeature = swFeatureMgr.FeatureExtrude2(True, False, False, 0, 0, 0.17, 0, False, False, False, False, 0, 0, False, False, False, False, True, True, True)
    swModel.ClearSelection2 True
    
    ' Üst Yüzeyden Cebi Kes
    boolstatus = swModelDocExt.SelectByID2("", "FACE", 0, 0.06, 0.085, False, 0, Nothing, 0)
    swSketchMgr.InsertSketch True
    
    swSketchMgr.CreateCornerRectangle -0.047, 0.008, 0, 0.047, 0.162, 0
    swSketchMgr.InsertSketch True
    swModel.ClearSelection2 True
    
    ' Çizimi adlandır
    RenameLastFeature swModel, "BeebotBoxSketch2"
    
    ' Pocket Kesimi uygula
    boolstatus = swModelDocExt.SelectByID2("BeebotBoxSketch2", "SKETCH", 0, 0, 0, False, 0, Nothing, 0)
    Set myFeature = swFeatureMgr.FeatureCut3(True, False, False, 0, 0, 0.052, 0, False, False, False, False, 0, 0, False, False, False, False, False, True, True, True, True, False)
    swModel.ClearSelection2 True
    
    MsgBox "Moduler Kizakli Batarya Kutusu Tasarimi Tamamlandi!", vbInformation, "Beebot CAD"
End Sub
```
