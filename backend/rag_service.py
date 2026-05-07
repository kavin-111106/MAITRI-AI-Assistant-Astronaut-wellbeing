from __future__ import annotations

import asyncio
import gc
import io
import time
import logging
from functools import lru_cache
from typing import Generator, Iterator, List, Tuple

import google.generativeai as genai
from groq import Groq
from sqlalchemy import text
from sqlmodel.ext.asyncio.session import AsyncSession

from .config import settings

logger = logging.getLogger("maitri.rag")

# ── Gemini embedding config ───────────────────────────────────────────────────

GEMINI_EMBED_MODEL = "models/gemini-embedding-001"
EMBED_DIMS         = 3072    # 768 for text-embedding-004; update if using specific 001 dims
EMBED_BATCH_SIZE   = 100    # Gemini allows up to 100 texts per batch_embed_contents call
EMBED_RATE_LIMIT   = 1_500  # free-tier daily cap (requests/day)
_RETRY_DELAYS      = [1, 2, 4]  # seconds — exponential back-off


# ── Singletons ────────────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def _groq_client() -> Groq:
    return Groq(api_key=settings.groq_api_key)


@lru_cache(maxsize=1)
def _configure_gemini() -> None:
    """Configure the Gemini SDK once."""
    api_key = getattr(settings, "gemini_api_key", None)
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is not set. Get a free key at "
            "https://aistudio.google.com/app/apikey"
        )
    genai.configure(api_key=api_key)
    logger.info("Gemini SDK configured — using model: %s", GEMINI_EMBED_MODEL)


# ── Embedding helpers ─────────────────────────────────────────────────────────

def _is_retryable(exc: Exception) -> bool:
    """Check if a Gemini API error is transient and worth retrying."""
    exc_str = str(exc).lower()
    retryable_signals = ["429", "500", "502", "503", "504", "quota",
                         "deadline", "unavailable", "resource_exhausted",
                         "internal", "timeout"]
    return any(sig in exc_str for sig in retryable_signals)


def _embed_batch_sync(texts: List[str], task_type: str = "RETRIEVAL_DOCUMENT") -> List[List[float]]:
    """
    Call Gemini batch_embed_contents for up to 100 texts at once.
    Retries up to 3 times on transient errors.
    """
    _configure_gemini()
    last_exc: Exception | None = None

    for attempt, delay in enumerate([0] + _RETRY_DELAYS):
        if delay:
            logger.warning("Gemini transient error — retrying in %ds (attempt %d) …", delay, attempt)
            time.sleep(delay)
        try:
            result = genai.embed_content(
                model=GEMINI_EMBED_MODEL,
                content=texts,
                task_type=task_type,
                request_options={"timeout": 120},
            )
            embeddings = result["embedding"]
            if isinstance(embeddings[0], float):
                embeddings = [embeddings]
            return [list(e) for e in embeddings]
        except Exception as exc:
            last_exc = exc
            if _is_retryable(exc):
                logger.warning("Gemini embedding error (retryable): %s", exc)
                continue
            logger.error("Gemini embedding error (non-retryable): %s", exc)
            raise

    raise RuntimeError(f"Gemini embedding failed after {len(_RETRY_DELAYS)+1} attempts: {last_exc}") from last_exc


def embed_texts(texts: List[str]) -> List[List[float]]:
    """Embed a list of document chunks."""
    if not texts:
        return []

    all_embeddings: List[List[float]] = []
    for start in range(0, len(texts), EMBED_BATCH_SIZE):
        batch = texts[start: start + EMBED_BATCH_SIZE]
        batch_embs = _embed_batch_sync(batch, task_type="RETRIEVAL_DOCUMENT")
        all_embeddings.extend(batch_embs)
        logger.info("Embedded batch %d (%d/%d chunks)", start // EMBED_BATCH_SIZE + 1, len(all_embeddings), len(texts))

    return all_embeddings


def embed_texts_batched(texts: List[str]) -> Generator[Tuple[str, List[float]], None, None]:
    """Memory-efficient generator version of embed_texts."""
    if not texts:
        return

    for start in range(0, len(texts), EMBED_BATCH_SIZE):
        batch = texts[start: start + EMBED_BATCH_SIZE]
        batch_embs = _embed_batch_sync(batch, task_type="RETRIEVAL_DOCUMENT")

        for chunk_text, emb in zip(batch, batch_embs):
            yield chunk_text, emb

        del batch_embs
        gc.collect()


def embed_query(query: str) -> List[float]:
    """Embed a single query string."""
    _configure_gemini()
    result = genai.embed_content(
        model=GEMINI_EMBED_MODEL,
        content=query,
        task_type="RETRIEVAL_QUERY",
        request_options={"timeout": 120},
    )
    emb = result["embedding"]
    if emb and isinstance(emb[0], list):
        emb = emb[0]
    return list(emb)


# ── Text extraction ───────────────────────────────────────────────────────────

def extract_text_streaming(content: bytes, filename: str) -> Iterator[Tuple[int, str]]:
    """Memory-efficient generator yielding (page_index, page_text)."""
    fname = filename.lower()

    if fname.endswith(".pdf"):
        try:
            import pdfplumber
            with pdfplumber.open(io.BytesIO(content)) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    page_text = page.extract_text() or ""
                    if page_text.strip():
                        yield page_num, page_text
                    del page_text
            return
        except ImportError:
            raise ValueError("pdfplumber not installed: pip install pdfplumber")

    if fname.endswith(".docx"):
        try:
            from docx import Document as DocxDoc
            doc = DocxDoc(io.BytesIO(content))
            full_text = "\n".join(p.text for p in doc.paragraphs).strip()
            if full_text:
                yield 0, full_text
            return
        except ImportError:
            raise ValueError("python-docx not installed: pip install python-docx")

    decoded = content.decode("utf-8", errors="ignore").strip()
    if decoded:
        yield 0, decoded


def chunk_text(text: str) -> List[str]:
    words = text.split()
    if not words:
        return []

    size, overlap = settings.chunk_size, settings.chunk_overlap
    chunks: List[str] = []
    i = 0
    while i < len(words):
        chunk = " ".join(words[i: i + size])
        if len(chunk) > 20:
            chunks.append(chunk)
        i += size - overlap
    return chunks


# ── pgvector retrieval ────────────────────────────────────────────────────────

async def vector_search(db: AsyncSession, query_embedding: List[float], top_k: int | None = None) -> List[dict]:
    k = top_k or settings.rag_top_k
    emb_str = "[" + ",".join(str(v) for v in query_embedding) + "]"

    sql = text("""
        SELECT
            dc.id AS chunk_id, dc.content, dc.chunk_index,
            d.original_name AS filename, d.id AS document_id,
            1 - (dc.embedding <=> CAST(:emb AS vector)) AS similarity
        FROM documentchunk dc
        JOIN document d ON d.id = dc.document_id
        WHERE d.status = 'indexed'
        ORDER BY dc.embedding <=> CAST(:emb AS vector)
        LIMIT :k
    """)

    rows = (await db.execute(sql, {"emb": emb_str, "k": k})).fetchall()

    return [
        {
            "chunk_id": row.chunk_id,
            "content": row.content,
            "chunk_index": row.chunk_index,
            "filename": row.filename,
            "document_id": row.document_id,
            "similarity": round(float(row.similarity), 4),
        }
        for row in rows
    ]


# ── Groq generation ───────────────────────────────────────────────────────────

_RAG_SYSTEM = """You are a precise assistant integrated into the Maitri knowledge base.
Answer ONLY from the provided context. Cite the source filename."""

_CHAT_SYSTEM = """You are Maitri, a compassionate AI companion supporting astronauts.
Never fabricate medical information. ALERT mission control if self-harm is detected."""


async def _call_groq(system: str, messages: List[dict], max_tokens: int = 1024) -> Tuple[str, int]:
    client = _groq_client()
    t0 = time.time()

    def _sync_call():
        return client.chat.completions.create(
            model=settings.groq_model,
            messages=[{"role": "system", "content": system}] + messages,
            temperature=0.2,
            max_tokens=max_tokens,
            stream=False,
        )

    resp = await asyncio.to_thread(_sync_call)
    return resp.choices[0].message.content, int((time.time() - t0) * 1000)


def _build_context_block(chunks: List[dict]) -> str:
    parts = [f"[Source {i} — {c['filename']} | relevance {c['similarity']}]\n{c['content']}"
             for i, c in enumerate(chunks, 1)]
    return "\n\n---\n\n".join(parts)


# ── Public API ────────────────────────────────────────────────────────────────

async def rag_query(db: AsyncSession, question: str, top_k: int | None = None) -> dict:
    t_total = time.time()
    q_emb = await asyncio.to_thread(embed_query, question)
    chunks = await vector_search(db, q_emb, top_k=top_k)
    
    context = _build_context_block(chunks) if chunks else "No relevant documents found."
    answer, gen_ms = await _call_groq(_RAG_SYSTEM, [{"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}"}])

    return {
        "answer": answer,
        "sources": chunks,
        "timing": {"total_ms": int((time.time() - t_total) * 1000)},
        "model": settings.groq_model,
    }

async def chat_with_rag(db: AsyncSession, user_message: str, conversation_history: List[dict], top_k: int | None = None) -> dict:
    t_total = time.time()
    q_emb = await asyncio.to_thread(embed_query, user_message)
    chunks = await vector_search(db, q_emb, top_k=top_k or settings.rag_top_k)

    system = f"{_CHAT_SYSTEM}\n\nContext:\n{_build_context_block(chunks)}" if chunks else _CHAT_SYSTEM
    messages = list(conversation_history) + [{"role": "user", "content": user_message}]
    response_text, gen_ms = await _call_groq(system, messages)

    return {
        "response": response_text,
        "sources": chunks,
        "timing": {"total_ms": int((time.time() - t_total) * 1000)},
    }