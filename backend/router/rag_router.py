"""
RAG Router (Admin-only)
───────────────────────
POST   /api/v1/rag/upload            — upload & index a file (admin JWT required)
GET    /api/v1/rag/documents         — list all documents
GET    /api/v1/rag/documents/{id}    — single document detail
DELETE /api/v1/rag/documents/{id}    — delete doc + all its chunks
POST   /api/v1/rag/query             — standalone RAG Q&A (admin JWT required)

Memory optimisations vs original:
  1. Upload bytes written to a temp file immediately; `content` freed before
     background task starts so FastAPI's BackgroundTasks arg-reference doesn't
     pin the buffer in the main process.
  2. Background task reads the temp file then deletes it from disk.
  3. PDF pages are streamed one at a time via extract_text_streaming().
  4. Embeddings are generated and flushed to DB in one interleaved loop —
     no separate "all chunks" + "all embeddings" lists held simultaneously.
  5. gc.collect() called after every page to keep RSS stable on large docs.
"""

from __future__ import annotations

import gc
import logging
import os
import tempfile
from urllib.parse import quote as url_quote

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from ..database import session_object, Admin, Document, DocumentChunk
from ..oauth2 import get_current_admin
from ..models import DocumentOut, DocumentListResponse, RAGQueryRequest, RAGQueryResponse
from ..rag_service import extract_text_streaming, chunk_text, embed_texts_batched, rag_query
from ..config import settings

logger = logging.getLogger("maitri.rag_router")
router = APIRouter(prefix="/api/v1/rag", tags=["RAG"])

ALLOWED_EXTENSIONS = {".pdf", ".txt", ".md", ".docx", ".rst", ".csv"}
MAX_FILE_BYTES     = 50 * 1024 * 1024  # 50 MB
DB_INSERT_BATCH    = 50                # flush to DB every N chunks


# ── Background indexing ───────────────────────────────────────────────────────

async def _index_document_from_path(doc_id: int, tmp_path: str, filename: str) -> None:
    """
    Read the temp file, delete it immediately, then index.
    Keeps the raw bytes alive only as long as needed.
    """
    try:
        with open(tmp_path, "rb") as f:
            content = f.read()
    except Exception as exc:
        logger.error(f"Could not read temp file for doc {doc_id}: {exc}")
        return
    finally:
        # Always remove the temp file whether the read succeeded or not
        try:
            os.unlink(tmp_path)
        except OSError:
            pass

    await _index_document(doc_id, content, filename)

    # Drop the local reference so GC can reclaim it even if the caller
    # accidentally keeps a reference to this coroutine frame alive.
    del content
    gc.collect()


async def _index_document(doc_id: int, content: bytes, filename: str) -> None:
    """
    Memory-optimised async background indexing pipeline:

        extract (streaming, page-by-page)
            → chunk
            → embed (batched generator, no full list in RAM)
            → flush to pgvector (every DB_INSERT_BATCH rows)
            → gc.collect() after each page

    Peak RAM ≈ one PDF page text  +  one embedding batch (≤100 × 768 floats).
    """
    pw = url_quote(settings.database_password)
    db_url = (
        f"postgresql+psycopg://{settings.database_username}:{pw}"
        f"@{settings.database_hostname}:{settings.database_port}/{settings.database_name}"
    )

    engine = create_async_engine(db_url, echo=False)
    SessionFactory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with SessionFactory() as db:
        try:
            doc = await db.get(Document, doc_id)
            if not doc:
                logger.error(f"Background indexing: document {doc_id} not found in DB")
                return

            logger.info(f"Indexing started  — doc_id:{doc_id} file:'{filename}'")

            total_chunks = 0
            global_idx   = 0
            freed_content = False

            # ── Stream one page / block at a time ────────────────────────────
            for page_num, page_text in extract_text_streaming(content, filename):

                # Free the raw bytes after the generator has opened the file
                # (pdfplumber holds its own handle; we no longer need `content`)
                if not freed_content:
                    del content
                    freed_content = True
                    gc.collect()

                page_chunks = chunk_text(page_text)
                del page_text
                gc.collect()

                if not page_chunks:
                    continue

                logger.info(
                    f"Page {page_num} — {len(page_chunks)} chunks — doc_id:{doc_id}"
                )

                # ── Embed + persist interleaved (no full embeddings list) ────
                for chunk_content, emb in embed_texts_batched(page_chunks):
                    db.add(DocumentChunk(
                        document_id=doc_id,
                        chunk_index=global_idx,
                        content=chunk_content,
                        embedding=emb,
                        token_count=len(chunk_content.split()),
                    ))
                    global_idx   += 1
                    total_chunks += 1

                    # Flush periodically so SQLAlchemy's identity map stays small
                    if global_idx % DB_INSERT_BATCH == 0:
                        await db.flush()
                        logger.info(
                            f"Flushed {global_idx} chunks so far — doc_id:{doc_id}"
                        )

                del page_chunks
                gc.collect()

            # ── Sanity check ─────────────────────────────────────────────────
            if total_chunks == 0:
                raise ValueError("No readable text found in the uploaded file")

            # ── Final flush + mark indexed ────────────────────────────────────
            await db.flush()
            doc.chunk_count = total_chunks
            doc.status      = "indexed"
            db.add(doc)
            await db.commit()

            logger.info(
                f"Indexing complete — doc_id:{doc_id} "
                f"chunks:{total_chunks} file:'{filename}'"
            )

        except Exception as exc:
            await db.rollback()
            import traceback
            err_msg = traceback.format_exc()
            print(
                f"\n[INDEXING FAILED] doc_id:{doc_id} file:'{filename}'\n{err_msg}",
                flush=True,
            )
            logger.error(
                f"Indexing FAILED — doc_id:{doc_id} file:'{filename}' error:{exc}",
                exc_info=True,
            )
            try:
                doc = await db.get(Document, doc_id)
                if doc:
                    doc.status        = "failed"
                    doc.error_message = str(exc)[:500]
                    db.add(doc)
                    await db.commit()
            except Exception as inner:
                logger.error(f"Could not write failure status for doc {doc_id}: {inner}")

    await engine.dispose()


# ── Upload ────────────────────────────────────────────────────────────────────

@router.post("/upload", status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: session_object = None,
    admin: Admin = Depends(get_current_admin),
):
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File type '{ext}' not allowed. Supported: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file")
    if len(content) > MAX_FILE_BYTES:
        raise HTTPException(status_code=413, detail="File exceeds 50 MB limit")

    # ── Write to temp file so BackgroundTasks doesn't pin `content` in RAM ──
    # FastAPI keeps a reference to every argument passed to add_task(), which
    # would hold the entire PDF buffer alive for the duration of indexing.
    # Passing a file path instead drops that reference immediately.
    try:
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
        tmp.write(content)
        tmp.close()
        file_size = len(content)
    finally:
        del content          # free upload buffer right away
        gc.collect()

    doc = Document(
        admin_id=admin.id,
        filename=file.filename,
        original_name=file.filename,
        file_type=ext,
        file_size=file_size,
        status="processing",
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    logger.info(
        f"Upload received   — doc_id:{doc.id} "
        f"file:'{file.filename}' size:{file_size}"
    )

    # Pass the temp-file PATH (not bytes) to the background task
    background_tasks.add_task(
        _index_document_from_path, doc.id, tmp.name, file.filename
    )

    return {
        "message": "File received. Indexing running in background.",
        "document": {
            "id":         doc.id,
            "filename":   doc.original_name,
            "file_size":  doc.file_size,
            "status":     doc.status,
            "created_at": doc.created_at,
        },
    }


# ── List documents ────────────────────────────────────────────────────────────

@router.get("/documents", response_model=DocumentListResponse)
async def list_documents(
    db: session_object,
    admin: Admin = Depends(get_current_admin),
):
    result = await db.exec(
        select(Document)
        .where(Document.admin_id == admin.id)
        .order_by(Document.created_at.desc())
    )
    docs = list(result.all())
    return DocumentListResponse(
        total=len(docs),
        documents=[
            DocumentOut(
                id=d.id,
                filename=d.original_name,
                file_type=d.file_type,
                file_size=d.file_size,
                chunk_count=d.chunk_count,
                status=d.status,
                error_message=d.error_message,
                created_at=d.created_at,
            )
            for d in docs
        ],
    )


# ── Single document ───────────────────────────────────────────────────────────

@router.get("/documents/{doc_id}", response_model=DocumentOut)
async def get_document(
    doc_id: int,
    db: session_object,
    admin: Admin = Depends(get_current_admin),
):
    doc = await db.get(Document, doc_id)
    if not doc or doc.admin_id != admin.id:
        raise HTTPException(status_code=404, detail="Document not found")

    return DocumentOut(
        id=doc.id,
        filename=doc.original_name,
        file_type=doc.file_type,
        file_size=doc.file_size,
        chunk_count=doc.chunk_count,
        status=doc.status,
        error_message=doc.error_message,
        created_at=doc.created_at,
    )


# ── Delete document ───────────────────────────────────────────────────────────

@router.delete("/documents/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    doc_id: int,
    db: session_object,
    admin: Admin = Depends(get_current_admin),
):
    doc = await db.get(Document, doc_id)
    if not doc or doc.admin_id != admin.id:
        raise HTTPException(status_code=404, detail="Document not found")

    chunks_result = await db.exec(
        select(DocumentChunk).where(DocumentChunk.document_id == doc_id)
    )
    for chunk in chunks_result.all():
        await db.delete(chunk)

    await db.delete(doc)
    await db.commit()
    logger.info(f"Admin {admin.id} deleted document {doc_id} ('{doc.original_name}')")


# ── Standalone RAG query ──────────────────────────────────────────────────────

@router.post("/query", response_model=RAGQueryResponse)
async def query_knowledge_base(
    req: RAGQueryRequest,
    db: session_object,
    admin: Admin = Depends(get_current_admin),
):
    if not settings.groq_api_key:
        raise HTTPException(status_code=500, detail="GROQ_API_KEY not configured")

    result = await rag_query(db, req.question, top_k=req.top_k)

    return RAGQueryResponse(
        answer=result["answer"],
        sources=result["sources"],
        timing=result["timing"],
        model=result["model"],
    )