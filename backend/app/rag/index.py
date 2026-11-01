from __future__ import annotations

from pathlib import Path

import faiss
import numpy as np

from app.core.config import settings


def _index_path(document_id: int) -> Path:
    base = Path(settings.faiss_index_dir)
    base.mkdir(parents=True, exist_ok=True)
    return base / f"doc_{document_id}.faiss"


def build_index(embeddings: np.ndarray) -> faiss.Index:
    """Build a FAISS inner-product index (cosine similarity since vectors are normalized)."""
    if embeddings.size == 0:
        raise ValueError("Cannot build index from empty embeddings")
    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(embeddings)
    return index


def save_index(document_id: int, index: faiss.Index) -> str:
    path = _index_path(document_id)
    faiss.write_index(index, str(path))
    return str(path)


def load_index(document_id: int) -> faiss.Index:
    path = _index_path(document_id)
    if not path.is_file():
        raise FileNotFoundError(f"FAISS index not found for document {document_id}")
    return faiss.read_index(str(path))


def delete_index(document_id: int) -> None:
    path = _index_path(document_id)
    if path.is_file():
        path.unlink()