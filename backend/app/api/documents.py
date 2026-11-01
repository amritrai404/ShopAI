from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.config import settings
from app.models.document import Document, DocumentChunk
from app.rag.chunk import chunk_pages
from app.rag.embed import embed_texts
from app.rag.extract import extract_pages
from app.rag.index import build_index, delete_index, save_index
from app.rag.retrieve import retrieve

router = APIRouter(prefix="/documents", tags=["documents"])

MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB


class DocumentSummary(BaseModel):
    id: int
    filename: str
    page_count: int
    chunk_count: int
    uploaded_at: datetime

    class Config:
        from_attributes = True


class SearchRequest(BaseModel):
    document_id: int
    query: str
    top_k: int = 5


class SearchHit(BaseModel):
    page: int
    chunk_index: int
    text: str
    score: float


class SearchResponse(BaseModel):
    document_id: int
    query: str
    hits: list[SearchHit]


def _upload_dir() -> Path:
    p = Path(settings.upload_dir)
    p.mkdir(parents=True, exist_ok=True)
    return p


@router.post("/upload", response_model=DocumentSummary)
async def upload_document(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File too large (max 10 MB).")
    if not content:
        raise HTTPException(status_code=400, detail="Empty file.")

    dest = _upload_dir() / f"{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}_{file.filename}"
    dest.write_bytes(content)

    try:
        pages = extract_pages(dest)
        chunks = chunk_pages(pages)
        if not chunks:
            raise ValueError("No chunks extracted from PDF.")

        texts = [c["text"] for c in chunks]
        embeddings = embed_texts(texts)
        index = build_index(embeddings)

        doc = Document(
            filename=file.filename,
            page_count=len(pages),
            chunk_count=len(chunks),
            uploaded_at=datetime.now(timezone.utc),
        )
        db.add(doc)
        db.flush()

        idx_path = save_index(doc.id, index)
        doc.index_path = idx_path

        db.add_all(
            [
                DocumentChunk(
                    document_id=doc.id,
                    page=c["page"],
                    chunk_index=c["chunk_index"],
                    text=c["text"],
                )
                for c in chunks
            ]
        )
        db.commit()
        db.refresh(doc)

        return DocumentSummary(
            id=doc.id,
            filename=doc.filename,
            page_count=doc.page_count,
            chunk_count=doc.chunk_count,
            uploaded_at=doc.uploaded_at,
        )

    except Exception as exc:
        db.rollback()
        if dest.is_file():
            dest.unlink()
        raise HTTPException(status_code=500, detail=f"Failed to process PDF: {exc}") from exc


@router.get("", response_model=list[DocumentSummary])
def list_documents(db: Session = Depends(get_db)):
    docs = db.execute(select(Document).order_by(Document.uploaded_at.desc())).scalars().all()
    return docs


@router.delete("/{document_id}")
def delete_document(document_id: int, db: Session = Depends(get_db)):
    doc = db.get(Document, document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found.")
    try:
        delete_index(doc.id)
    except Exception:
        pass
    db.delete(doc)
    db.commit()
    return {"status": "deleted", "id": document_id}


@router.post("/search", response_model=SearchResponse)
def search_documents(payload: SearchRequest, db: Session = Depends(get_db)):
    doc = db.get(Document, payload.document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found.")

    chunks = (
        db.query(DocumentChunk)
        .filter(DocumentChunk.document_id == doc.id)
        .order_by(DocumentChunk.id.asc())
        .all()
    )
    chunks_meta = [{"page": c.page, "chunk_index": c.chunk_index, "text": c.text} for c in chunks]

    try:
        hits = retrieve(doc.id, payload.query, chunks_meta, top_k=payload.top_k)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return SearchResponse(
        document_id=doc.id,
        query=payload.query,
        hits=[SearchHit(**h) for h in hits],
    )