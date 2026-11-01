from __future__ import annotations

from pathlib import Path

import pytest
import fitz

from app.rag.chunk import chunk_pages
from app.rag.extract import extract_pages


def _make_test_pdf(path: Path, pages_text: list[str]):
    doc = fitz.open()
    for text in pages_text:
        page = doc.new_page()
        page.insert_text((72, 72), text)
    doc.save(path)
    doc.close()


def test_extract_and_chunk(tmp_path):
    pdf_path = tmp_path / "test.pdf"
    _make_test_pdf(
        pdf_path,
        [
            "Supplier Price List 2026. Product P001 Rice 5kg costs 240 rupees.",
            "Product P002 Cooking Oil 1L costs 110 rupees. Product P003 Sugar 1kg costs 38 rupees.",
        ],
    )

    pages = extract_pages(pdf_path)
    assert len(pages) == 2
    assert "P001" in pages[0]["text"]
    assert "P002" in pages[1]["text"]

    chunks = chunk_pages(pages, chunk_size=20, overlap=5)
    assert len(chunks) > 0
    assert all("page" in c and "text" in c and "chunk_index" in c for c in chunks)


def test_chunk_rejects_bad_params():
    with pytest.raises(ValueError):
        chunk_pages([{"page": 1, "text": "abc"}], chunk_size=10, overlap=10)


def test_extract_missing_file():
    with pytest.raises(FileNotFoundError):
        extract_pages("does_not_exist.pdf")