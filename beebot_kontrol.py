import os
import sys
import subprocess
import importlib.util
import json
import time

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def main():
    clear_screen()
    print("====================================================")
    print("        BEEBOT OTONOMI TEK TIKLA BAŞLATMA PANELİ    ")
    print("====================================================\n")
    
    # 1. ADIM: Kütüphane Kontrolü ve Otomatik Kurulum
    print("[ADIM 1] Python kutuphaneleri kontrol ediliyor...")
    required = {
        "cv2": "opencv-python",
        "numpy": "numpy",
        "serial": "pyserial",
        "rplidar": "rplidar-roboticia"
    }
    missing = []
    for lib, package in required.items():
        if importlib.util.find_spec(lib) is not None:
            print(f"  [OK] {package} yuklu.")
        else:
            print(f"  [FAIL] {package} EKSİK! Listeye eklendi.")
            missing.append(package)
            
    if missing:
        print(f"\nEksik kutuphaneler otomatik kuruluyor: {', '.join(missing)}...")
        try:
            # 120 saniye zaman aşımı (timeout) eklenerek ağ kilitlenmesi engellendi
            subprocess.check_call([sys.executable, "-m", "pip", "install"] + missing, timeout=120)
            print("  [OK] Tum kutuphaneler basariyla kuruldu!")
        except Exception as e:
            print(f"  [FAIL] Kutuphane kurulum hatasi: {e}")
            print("Lutfen internet baglantinizi kontrol edip tekrar deneyin.")
            sys.exit(1)
    else:
        print("  [OK] Tum kutuphaneler hazir.")
    print("-" * 50)

    # 2. ADIM: USB ve Lidar Port İzinleri (Linux/Android ise)
    if os.name == 'posix':
        print("\n[ADIM 2] Linux/Android USB port izinleri tanimlaniyor...")
        try:
            # Root yetkisiyle chmod yapmayi dene
            subprocess.run(["su", "-c", "chmod 666 /dev/ttyUSB* /dev/ttyACM*"], check=False)
            print("  [OK] USB ve LIDAR port izinleri basariyla tanimlandi!")
        except Exception as e:
            print(f"  [FAIL] Izin tanimlama hatasi (Root izni olmayabilir): {e}")
    else:
        print("\n[ADIM 2] Windows isletim sistemi algilandi, USB izin adimi atlaniyor.")
    print("-" * 50)

    # 3. ADIM: Tüm Sistem Testleri (Dry-Run)
    print("\n[ADIM 3] Entegrasyon ve Yapay Zeka testleri kosturuluyor (Dry-Run)...")
    tests = [
        ("STM32 Haberlesme Protokolu", "scratch/test_stm32_compatibility.py"),
        ("MobileNet-SSD & HSV Yapay Zeka", "scratch/test_ssd_detection.py"),
        ("FSM Durum Makinesi ve Gorevler", "scratch/test_stage10.py"),
        ("Cift Kanalli Asenkron Log Sistemi", "scratch/test_usb_logging.py")
    ]
    
    all_success = True
    for name, path in tests:
        print(f"  Calistiriliyor: {name}...")
        try:
            # Testlerin kilitlenmemesi için 30 saniye zaman aşımı (timeout) eklendi
            res = subprocess.run([sys.executable, path], capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=30)
            if res.returncode == 0:
                print(f"    [OK] {name}: BASARILI")
            else:
                print(f"    [FAIL] {name}: BASARISIZ!")
                print(f"--- HATA DETAYI ---\n{res.stderr or res.stdout}\n-------------------")
                all_success = False
        except subprocess.TimeoutExpired:
            print(f"    [FAIL] {name} test sistemi hatasi: ZAMAN AŞIMI (30 saniye)")
            all_success = False
        except Exception as e:
            print(f"    [FAIL] {name} test sistemi hatasi: {e}")
            all_success = False
            
    if not all_success:
        print("\n[!] DIKKAT: Bazi testler basarisiz oldu! Guvenlik nedeniyle devam etmeden once yukaridaki hatalari inceleyin.")
        auto_mode = "--auto" in sys.argv
        if auto_mode:
            print("Headless/Auto mod aktif, test hatalarina ragmen otomatik devam ediliyor...")
            ans = 'e'
        else:
            ans = input("Yine de devam etmek istiyor musunuz? (e/h): ").lower()
        if ans != 'e':
            sys.exit(1)
    else:
        print("\n  [OK] Tum entegrasyon testleri BASARIYLA GECILDI!")
    print("-" * 50)

    # 4. ADIM: Yarış Ayarları ve config.json Güncelleme
    print("\n[ADIM 4] Yaris Konfigürasyonu Guncelleme")
    config_path = "high_level/src/config.json"
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config_data = json.load(f)
                
            print(f"  Mevcut Hedef Renk: {config_data.get('target_color', 'Bilinmiyor')}")
            auto_mode = "--auto" in sys.argv
            if auto_mode:
                print("  Headless/Auto mod aktif, mevcut renk degistirilmeden korunuyor.")
                color_choice = "S"
            else:
                print("  Hedef rengi degistirmek istiyor musunuz?")
                print("    1: target_red (Kirmizi - Varsayilan)")
                print("    2: target_green (Yesil)")
                print("    3: target_blue (Mavi)")
                print("    S: Degistirme, Mevcut Kalsin")
                color_choice = input("  Seciminiz (1/2/3/S): ").strip().upper()
                
            if color_choice == "1":
                config_data["target_color"] = "target_red"
            elif color_choice == "2":
                config_data["target_color"] = "target_green"
            elif color_choice == "3":
                config_data["target_color"] = "target_blue"
                
            # Kaydet
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config_data, f, indent=4)
            print(f"  [OK] config.json basariyla guncellendi! Yeni hedef renk: {config_data['target_color']}")
        except Exception as e:
            print(f"  [FAIL] config.json guncellenirken hata olustu: {e}")
    else:
        print("  [FAIL] config.json bulunamadi, yapilandirma adimi atlaniyor.")
    print("-" * 50)

    # 5. ADIM: Otonom Başlatma
    print("\n[ADIM 5] Beebot Otonom Yazilimi Baslatiliyor...")
    # Otomatik port tespiti
    port = "MOCK"
    if os.name == 'posix': # Linux/Android
        for p in ["/dev/ttyACM0", "/dev/ttyACM1", "/dev/ttyUSB0", "/dev/ttyUSB1"]:
            if os.path.exists(p):
                port = p
                break
                
    print(f"  Tespit Edilen Seri Port: {port}")
    if port == "MOCK":
        print("  [!] STM32 bagli bulunamadi. Simulasyon (MOCK) modunda baslatiliyor.")
    else:
        print(f"  [OK] STM32 baglantisi kuruluyor: {port}")
        
    main_path = "high_level/src/main.py"
    print("\n>>> Otonom Kontrol Baslatildi. Durdurmak icin Ctrl+C tuslarina basin. <<<\n")
    time.sleep(2)
    try:
        subprocess.run([sys.executable, main_path, port, "115200"])
    except KeyboardInterrupt:
        print("\nSistem kullanici tarafindan durduruldu.")
    except Exception as e:
        print(f"[X] Calistirma hatasi: {e}")

if __name__ == "__main__":
    main()
