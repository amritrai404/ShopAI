from __future__ import annotations

import numpy as np
from functools import lru_cache
from sentence_transformers import SentenceTransformer

from app.core.config import settings


@lru_cache(maxsize=1)
def _get_model() -> SentenceTransformer:
    return SentenceTransformer(settings.embedding_model)


def get_embedding_dim() -> int:
    return _get_model().get_sentence_embedding_dimension()


def embed_texts(texts: list[str]) -> np.ndarray:
    """Returns float32 array shape (n, dim), L2-normalized for cosine similarity via FAISS."""
    if not texts:
        return np.zeros((0, get_embedding_dim()), dtype=np.float32)

    model = _get_model()
    embeddings = model.encode(
        texts,
        batch_size=32,
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    return embeddings.astype(np.float32)