import os
import sys

# Try to import different PDF libraries
try:
    import pypdf
    reader_name = "pypdf"
except ImportError:
    try:
        import PyPDF2 as pypdf
        reader_name = "PyPDF2"
    except ImportError:
        try:
            import pdfplumber
            reader_name = "pdfplumber"
        except ImportError:
            reader_name = None

pdf_path = r"c:\Users\Şahakan\Desktop\aydede\2026_İnsansız_Deniz_Araci_Şartnamesi_TR_20_02_V2_0WyXP (1).pdf"

if not os.path.exists(pdf_path):
    print(f"Error: PDF not found at {pdf_path}")
    sys.exit(1)

if reader_name is None:
    print("No PDF parsing libraries found. Attempting to install pypdf...")
    # We can try to install pypdf via pip, but let's notify the user or run a quick pip command.
    import subprocess
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "pypdf"], check=True)
        import pypdf
        reader_name = "pypdf"
    except Exception as e:
        print(f"Failed to install pypdf: {e}")
        sys.exit(1)

print(f"Using {reader_name} to parse PDF...")
keywords = ["kumanda", "frekans", "acil", "stop", "durdurma", "mhz", "ghz", "telsiz", "verici", "alici", "rf"]

results = []

if reader_name in ["pypdf", "PyPDF2"]:
    reader = pypdf.PdfReader(pdf_path)
    for page_num, page in enumerate(reader.pages):
        text = page.extract_text()
        if not text:
            continue
        lines = text.split('\n')
        for line_num, line in enumerate(lines):
            line_lower = line.lower()
            for kw in keywords:
                if kw in line_lower:
                    results.append((page_num + 1, line_num + 1, kw, line.strip()))
                    break
elif reader_name == "pdfplumber":
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages):
            text = page.extract_text()
            if not text:
                continue
            lines = text.split('\n')
            for line_num, line in enumerate(lines):
                line_lower = line.lower()
                for kw in keywords:
                    if kw in line_lower:
                        results.append((page_num + 1, line_num + 1, kw, line.strip()))
                        break

print(f"Found {len(results)} matches:")
for r in results[:100]: # Print first 100 matches
    print(f"Page {r[0]} | Line {r[1]} | Keyword: {r[2]} | Text: {r[3]}")
