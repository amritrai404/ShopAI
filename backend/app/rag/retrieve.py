from __future__ import annotations

from app.rag.embed import embed_texts
from app.rag.index import load_index


def retrieve(document_id: int, query: str, chunks_meta: list[dict], top_k: int = 5) -> list[dict]:
    """
    Retrieve top-k chunks for a query.
    chunks_meta: ordered list of {"page", "chunk_index", "text"} matching FAISS insertion order.
    Returns [{"page", "chunk_index", "text", "score"}, ...].
    """
    if not query.strip():
        raise ValueError("Query cannot be empty")
    if not chunks_meta:
        return []

    index = load_index(document_id)
    q_emb = embed_texts([query])  # (1, dim) normalized

    k = min(top_k, len(chunks_meta))
    scores, indices = index.search(q_emb, k)

    results: list[dict] = []
    for score, idx in zip(scores[0], indices[0]):
        if idx < 0 or idx >= len(chunks_meta):
            continue
        meta = chunks_meta[idx]
        results.append(
            {
                "page": meta["page"],
                "chunk_index": meta["chunk_index"],
                "text": meta["text"],
                "score": float(score),
            }
        )

    return results