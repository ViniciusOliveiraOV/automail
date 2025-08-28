import io
try:
    from pdfminer.high_level import extract_text
except Exception:
    extract_text = None

from typing import Union

def pdf_to_text(path_or_bytes: Union[str, bytes, bytearray, memoryview]):
    if extract_text is None:
        raise RuntimeError("pdfminer.six não instalado")
    if isinstance(path_or_bytes, (bytes, bytearray, memoryview)):
        return extract_text(io.BytesIO(path_or_bytes))
    return extract_text(path_or_bytes)

def extract_text_from_pdf(pdf_path: str):
    from PyPDF2 import PdfReader

    text = ""
    try:
        reader = PdfReader(pdf_path)
        for page in reader.pages:
            text += page.extract_text() + "\n"
    except Exception as e:
        print(f"Error reading {pdf_path}: {e}")
    
    return text.strip()