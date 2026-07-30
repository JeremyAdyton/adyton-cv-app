"""
extract_cv.py — Extraction de texte depuis PDF ou DOCX
"""

import io
from pathlib import Path


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extrait le texte brut d'un PDF via PyMuPDF."""
    import fitz  # PyMuPDF
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    pages = []
    for page in doc:
        pages.append(page.get_text())
    doc.close()
    return "\n".join(pages)


def extract_text_from_docx(file_bytes: bytes) -> str:
    """Extrait le texte brut d'un DOCX via python-docx."""
    from docx import Document
    doc = Document(io.BytesIO(file_bytes))
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return "\n".join(paragraphs)


def extract_text(file_bytes: bytes, filename: str) -> str:
    """Détecte le format et extrait le texte."""
    ext = Path(filename).suffix.lower()
    if ext == ".pdf":
        return extract_text_from_pdf(file_bytes)
    elif ext in (".docx", ".doc"):
        return extract_text_from_docx(file_bytes)
    else:
        raise ValueError(f"Format non supporté : {ext} (acceptés : .pdf, .docx)")
