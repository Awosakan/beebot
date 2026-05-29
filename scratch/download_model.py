import urllib.request
import tarfile
import os
import shutil

def download_model():
    print("=== MobileNetV3-SSD Model Dosyaları İndiriliyor ===")
    
    # Hedef dizin
    target_dir = os.path.join(os.path.dirname(__file__), "..", "high_level", "src")
    os.makedirs(target_dir, exist_ok=True)
    
    pb_dest = os.path.join(target_dir, "en_iyi_duba_modeli.pb")
    pbtxt_dest = os.path.join(target_dir, "en_iyi_duba_modeli.pbtxt")
    
    # 1. TensorFlow Model Zoo'dan model ağırlıklarını (.tar.gz) indir
    tar_url = "http://download.tensorflow.org/models/object_detection/ssd_mobilenet_v3_large_coco_2020_01_14.tar.gz"
    tar_tmp = os.path.join(os.path.dirname(__file__), "model.tar.gz")
    
    print(f"1. Model ağırlıkları indiriliyor (tar.gz)... \nKaynak: {tar_url}")
    try:
        urllib.request.urlretrieve(tar_url, tar_tmp)
        print("Model paketi başarıyla indirildi.")
    except Exception as e:
        print(f"Hata: Model indirilemedi! {e}")
        return False
        
    # 2. tar.gz paketinden frozen_inference_graph.pb dosyasını çıkar
    print("2. Paketten 'frozen_inference_graph.pb' çıkarılıyor...")
    try:
        with tarfile.open(tar_tmp, "r:gz") as tar:
            # Arşivdeki frozen_inference_graph.pb yolunu bul
            pb_member = None
            for member in tar.getmembers():
                if "frozen_inference_graph.pb" in member.name:
                    pb_member = member
                    break
                    
            if pb_member:
                # Geçici olarak dışarı çıkart
                tar.extract(pb_member, path=os.path.dirname(__file__))
                pb_extracted_path = os.path.join(os.path.dirname(__file__), pb_member.name)
                # Doğru konuma kopyala ve yeniden adlandır
                shutil.move(pb_extracted_path, pb_dest)
                print(f"-> Model ağırlıkları yerleştirildi: {pb_dest}")
                
                # Temizlik
                extracted_dir = os.path.join(os.path.dirname(__file__), pb_member.name.split("/")[0])
                if os.path.exists(extracted_dir):
                    shutil.rmtree(extracted_dir)
            else:
                print("Hata: Arşiv içerisinde 'frozen_inference_graph.pb' bulunamadı!")
                return False
    except Exception as e:
        print(f"Hata: Arşiv açılırken hata oluştu: {e}")
        return False
    finally:
        if os.path.exists(tar_tmp):
            os.remove(tar_tmp)
            
    # 3. OpenCV DNN uyumlu .pbtxt konfigürasyonunu indir
    pbtxt_url = "https://raw.githubusercontent.com/ankityddv/ObjectDetector-OpenCV/main/ssd_mobilenet_v3_large_coco_2020_01_14.pbtxt"
    print(f"\n3. OpenCV uyumlu .pbtxt konfigürasyon dosyası indiriliyor...\nKaynak: {pbtxt_url}")
    try:
        urllib.request.urlretrieve(pbtxt_url, pbtxt_dest)
        print(f"-> Konfigürasyon dosyası yerleştirildi: {pbtxt_dest}")
    except Exception as e:
        print(f"Hata: .pbtxt dosyası indirilemedi! {e}")
        return False
        
    print("\n=== Model Entegrasyonu Başarıyla Tamamlandı! ===")
    return True

if __name__ == "__main__":
    download_model()
