import os
import sys
import pypdf

# Set standard output encoding to UTF-8
sys.stdout.reconfigure(encoding='utf-8')

pdf_path = r"c:\Users\Şahakan\Desktop\aydede\2026_İnsansız_Deniz_Araci_Şartnamesi_TR_20_02_V2_0WyXP (1).pdf"

if not os.path.exists(pdf_path):
    print("PDF not found")
    sys.exit(1)

reader = pypdf.PdfReader(pdf_path)

for page_num in range(11, 15):  # Pages 12, 13, 14, 15 (0-indexed 11, 12, 13, 14)
    print(f"\n--- PAGE {page_num + 1} ---")
    page = reader.pages[page_num]
    text = page.extract_text()
    if text:
        print(text)
    else:
        print("[No text extracted]")
