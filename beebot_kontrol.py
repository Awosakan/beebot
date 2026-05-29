import os
import sys
import subprocess
import importlib
import time

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def check_dependencies():
    print("=== GEREKSİNİM KONTROLLERİ ===")
    required = {
        "cv2": "opencv-python",
        "numpy": "numpy",
        "serial": "pyserial",
        "rplidar": "rplidar-roboticia"
    }
    missing = []
    for lib, package in required.items():
        try:
            importlib.import_module(lib)
            print(f"[✔] {package} yuklu.")
        except ImportError:
            print(f"[X] {package} EKSİK!")
            missing.append(package)
    return missing

def install_dependencies(missing):
    if not missing:
        print("Tum kutuphaneler zaten yuklu!")
        return True
    print(f"\nEksik kutuphaneler kuruluyor: {', '.join(missing)}...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install"] + missing)
        print("[✔] Kurulum basariyla tamamlandi!")
        return True
    except Exception as e:
        print(f"[X] Kurulum hatasi: {e}")
        return False

def run_all_tests():
    clear_screen()
    print("====================================================")
    print("          BEEBOT OTONOMI TEST PANELİ                ")
    print("====================================================\n")
    
    tests = [
        ("STM32 Haberlesme ve CRC Uyumlulugu", "scratch/test_stm32_compatibility.py"),
        ("MobileNet-SSD & HSV Renk Algilama", "scratch/test_ssd_detection.py"),
        ("Gorev Zaman Asimi ve FSM Senaryolari", "scratch/test_stage10.py"),
        ("Cift Kanalli Asenkron Log Sistemi", "scratch/test_usb_logging.py")
    ]
    
    all_success = True
    for name, path in tests:
        print(f"⌛ {name} calistiriliyor...")
        try:
            # Testleri alt surec olarak calistir
            res = subprocess.run([sys.executable, path], capture_output=True, text=True, encoding='utf-8', errors='ignore')
            if res.returncode == 0:
                print(f"[✔] {name}: BASARILI!")
            else:
                print(f"[X] {name}: HATA ALINDI!")
                print(f"--- HATA AYRINTISI ---\n{res.stderr or res.stdout}\n----------------------")
                all_success = False
        except Exception as e:
            print(f"[X] {name} calistirilirken sistem hatasi: {e}")
            all_success = False
        print("-" * 50)
        
    if all_success:
        print("\n🎉 TEBRİKLER: Tum sistem testleri basariyla tamamlandi! Beebot yarisa hazir.")
    else:
        print("\n⚠️ DIKKAT: Bazi testler basarisiz oldu. Yukaridaki hata ayrintilarini kontrol edin.")
    input("\nAna menuye donmek icin Enter'a basin...")

def start_autonomy():
    clear_screen()
    print("====================================================")
    print("          BEEBOT OTONOM SISTEMI BASLATILIYOR        ")
    print("====================================================\n")
    
    # Otomatik port tespiti
    port = "MOCK"
    if os.name == 'posix': # Linux/Android
        for p in ["/dev/ttyACM0", "/dev/ttyACM1", "/dev/ttyUSB0", "/dev/ttyUSB1"]:
            if os.path.exists(p):
                port = p
                break
    
    print(f"Tespit Edilen Seri Port: {port}")
    if port == "MOCK":
        print("STM32 bagli bulunamadi. Sistem simulasyon (MOCK) modunda baslatiliyor...")
    else:
        print(f"STM32 baglantisi kuruluyor: {port}...")
        
    main_path = "high_level/src/main.py"
    try:
        # main.py dosyasini calistir
        subprocess.run([sys.executable, main_path, port, "115200"])
    except KeyboardInterrupt:
        print("\nSistem kullanici tarafindan durduruldu.")
    except Exception as e:
        print(f"Baslatma hatasi: {e}")
    input("\nAna menuye donmek icin Enter'a basin...")

def set_permissions():
    if os.name != 'posix':
        print("Bu islem sadece Linux / Android (Termux) ortaminda gecerlidir!")
        input("\nDevam etmek icin Enter'a basin...")
        return
        
    print("USB port yetkileri tanimlaniyor (Root sifresi istenebilir)...")
    try:
        subprocess.run(["su", "-c", "chmod 666 /dev/ttyUSB* /dev/ttyACM*"])
        print("[✔] USB ve Lidar port izinleri basariyla tanimlandi!")
    except Exception as e:
        print(f"[X] Izin hatasi: {e}")
    input("\nDevam etmek icin Enter'a basin...")

def main():
    while True:
        clear_screen()
        print("====================================================")
        print("          BEEBOT TEK TUSLA KONTROL MERKEZİ          ")
        print("====================================================")
        print("  1) Kutuphane Kurulum Durumunu Kontrol Et / Eksikleri Yukle")
        print("  2) Tum Entegrasyon Testlerini Calistir (Dry-Run)")
        print("  3) Otonom Sistemi Baslat (Otomatik Cihaz Algilama)")
        print("  4) Linux/Android Seri Port Izinlerini Tanimla (Chmod)")
        print("  5) Cikis")
        print("====================================================")
        
        secim = input("Lutfen bir islem secin (1-5): ").strip()
        if secim == "1":
            clear_screen()
            missing = check_dependencies()
            if missing:
                ans = input("\nEksik kutuphaneler otomatik kurulsun mu? (e/h): ").lower()
                if ans == 'e':
                    install_dependencies(missing)
            else:
                print("\nHarika! Tum bagimliliklar yuklu.")
            input("\nDevam etmek icin Enter'a basin...")
        elif secim == "2":
            run_all_tests()
        elif secim == "3":
            start_autonomy()
        elif secim == "4":
            set_permissions()
        elif secim == "5":
            print("\nBeebot Kontrol Merkezi kapatiliyor. Basarilar!")
            break
        else:
            print("\nGecersiz secim! Lutfen 1 ile 5 arasinda bir deger girin.")
            time.sleep(1)

if __name__ == "__main__":
    main()
