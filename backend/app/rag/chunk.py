from __future__ import annotations


def chunk_pages(
    pages: list[dict],
    chunk_size: int = 500,
    overlap: int = 50,
) -> list[dict]:
    """
    Split page text into overlapping word chunks.
    chunk_size and overlap are in WORDS (not tokens — good enough for embeddings).
    Returns [{"page": 1, "chunk_index": 0, "text": "..."}, ...].
    """
    if chunk_size <= overlap:
        raise ValueError("chunk_size must be greater than overlap")

    chunks: list[dict] = []
    for page in pages:
        text = page["text"]
        words = text.split()
        if not words:
            continue

        step = chunk_size - overlap
        for start in range(0, len(words), step):
            end = start + chunk_size
            chunk_words = words[start:end]
            if not chunk_words:
                break
            chunk_text = " ".join(chunk_words).strip()
            if chunk_text:
                chunks.append(
                    {
                        "page": page["page"],
                        "chunk_index": len([c for c in chunks if c["page"] == page["page"]]),
                        "text": chunk_text,
                    }
                )
            if end >= len(words):
                break

    return chunks