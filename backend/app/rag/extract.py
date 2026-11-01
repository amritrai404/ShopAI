from __future__ import annotations

from pathlib import Path

import fitz  # PyMuPDF


def extract_pages(pdf_path: str | Path) -> list[dict]:
    """
    Extract text page-by-page from a PDF.
    Returns [{"page": 1, "text": "..."}, ...] (1-indexed page numbers).
    """
    path = Path(pdf_path)
    if not path.is_file():
        raise FileNotFoundError(f"PDF not found: {path}")

    doc = fitz.open(path)
    pages: list[dict] = []
    try:
        for page_num, page in enumerate(doc, start=1):
            text = page.get_text("text").strip()
            if text:
                pages.append({"page": page_num, "text": text})
    finally:
        doc.close()

    if not pages:
        raise ValueError(f"No extractable text in {path.name}. Is it a scanned PDF?")

    return pages