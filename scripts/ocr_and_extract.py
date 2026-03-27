# scripts/ocr_and_extract.py
import os
from pathlib import Path
from pypdf import PdfReader
from pdf2image import convert_from_path
import pytesseract
from dotenv import load_dotenv
from tqdm import tqdm

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

load_dotenv()
print("PDF_DIR:", os.getenv("DATA_PDF_DIR"))
print("TEXT_DIR:", os.getenv("DATA_TEXT_DIR"))
print("TESSERACT_CMD:", os.getenv("TESSERACT_CMD"))
print("POPPLER_PATH:", os.getenv("POPPLER_PATH"))

TESSERACT_CMD = os.getenv("TESSERACT_CMD")
POPPLER_PATH = os.getenv("POPPLER_PATH")

if TESSERACT_CMD:
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD

def extract_text_direct(pdf_path: Path) -> str:
    try:
        reader = PdfReader(str(pdf_path))
        pages = [p.extract_text() or "" for p in reader.pages]
        return "\n".join(pages).strip()
    except Exception as e:
        print("Direct PDF extract failed:", e)
        return ""

def image_ocr(pdf_path: Path, languages="hin+mar+eng", dpi=300) -> str:
    poppler_path = POPPLER_PATH or None
    images = convert_from_path(str(pdf_path), dpi=dpi, poppler_path=poppler_path)
    results = []
    for img in tqdm(images, desc=f"OCR pages for {pdf_path.name}"):
        txt = pytesseract.image_to_string(img, lang=languages)
        results.append(txt)
    return "\n".join(results).strip()

def clean_text(txt: str) -> str:
    lines = [l.strip() for l in txt.splitlines() if l.strip()]
    return "\n".join(lines)

def ocr_and_extract_all(pdf_dir: str, out_text_dir: str):
    pdf_dir = Path(pdf_dir)
    out_text_dir = Path(out_text_dir)
    out_text_dir.mkdir(parents=True, exist_ok=True)
    for pdf in pdf_dir.glob("*.pdf"):
        print("\nProcessing:", pdf.name)
        text = extract_text_direct(pdf)
        if len(text) < 200:
            print("Direct extraction too small/empty — running image OCR...")
            text = image_ocr(pdf)
        text = clean_text(text)
        out_file = out_text_dir / (pdf.stem + ".txt")
        out_file.write_text(text, encoding="utf-8")
        print("Saved text:", out_file)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf_dir", default=os.getenv("DATA_PDF_DIR"))
    parser.add_argument("--out_dir", default=os.getenv("DATA_TEXT_DIR"))
    args = parser.parse_args()
    if not args.pdf_dir or not args.out_dir:
        raise SystemExit("Set DATA_PDF_DIR and DATA_TEXT_DIR in .env or pass args.")
    ocr_and_extract_all(args.pdf_dir, args.out_dir)
