"""
RAG Service
───────────
Pipeline: Gemini Embedding API → pgvector cosine search → Groq generation

Embeddings are fully cloud-based (Google AI Studio free tier):
  - Model  : text-embedding-004
  - Dims   : 768
  - Free   : 1,500 requests/day · 1M tokens/day
  - Latency: ~100-300ms per call (network round-trip)
  - RAM    : ~0 MB  (zero local model, zero CPU/GPU usage)

Install: pip install google-generativeai
Env var: GEMINI_API_KEY (from https://aistudio.google.com/app/apikey)
"""

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
<<<<<<< Updated upstream
<<<<<<< HEAD
EMBED_DIMS         = 3072    # fixed output dim for text-embedding-004
=======
EMBED_DIMS         = 3072    # fixed output dim for text-embedding-001
>>>>>>> b8f98e421e932b3269e17058d0625adfd87e15d1
=======
EMBED_DIMS         = 3072    # fixed output dim for text-embedding-001
>>>>>>> Stashed changes
EMBED_BATCH_SIZE   = 100    # Gemini allows up to 100 texts per batch_embed_contents call
EMBED_RATE_LIMIT   = 1_500  # free-tier daily cap (requests/day); just for awareness
_RETRY_DELAYS      = [1, 2, 4]  # seconds — exponential back-off on 429


# ── Singletons ────────────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def _groq_client() -> Groq:
    return Groq(api_key=settings.groq_api_key)


@lru_cache(maxsize=1)
def _configure_gemini() -> None:
    """Configure the Gemini SDK once. Returns None — just a side-effect call."""
    api_key = getattr(settings, "gemini_api_key", None)
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is not set. "
            "Get a free key at https://aistudio.google.com/app/apikey "
            "and add it to your .env as GEMINI_API_KEY=..."
        )
    genai.configure(api_key=api_key)
    logger.info("Gemini SDK configured — using model: %s", GEMINI_EMBED_MODEL)


# ── Embedding helpers ─────────────────────────────────────────────────────────

<<<<<<< Updated upstream
<<<<<<< HEAD
def _embed_batch_sync(texts: List[str], task_type: str = "RETRIEVAL_DOCUMENT") -> List[List[float]]:
    """
    Call Gemini batch_embed_contents for up to 100 texts at once.
    Retries up to 3 times on rate-limit (429) errors.
=======
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
    Retries up to 3 times on transient errors (429, 500, 502, 503, 504, timeouts).
>>>>>>> b8f98e421e932b3269e17058d0625adfd87e15d1
=======
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
    Retries up to 3 times on transient errors (429, 500, 502, 503, 504, timeouts).
>>>>>>> Stashed changes
    """
    _configure_gemini()
    last_exc: Exception | None = None

<<<<<<< Updated upstream
<<<<<<< HEAD
    for delay in [0] + _RETRY_DELAYS:
        if delay:
            logger.warning("Gemini 429 — retrying in %ds …", delay)
=======
    for attempt, delay in enumerate([0] + _RETRY_DELAYS):
        if delay:
            logger.warning("Gemini transient error — retrying in %ds (attempt %d) …", delay, attempt + 1)
>>>>>>> b8f98e421e932b3269e17058d0625adfd87e15d1
=======
    for attempt, delay in enumerate([0] + _RETRY_DELAYS):
        if delay:
            logger.warning("Gemini transient error — retrying in %ds (attempt %d) …", delay, attempt + 1)
>>>>>>> Stashed changes
            time.sleep(delay)
        try:
            result = genai.embed_content(
                model=GEMINI_EMBED_MODEL,
                content=texts,
                task_type=task_type,
<<<<<<< Updated upstream
<<<<<<< HEAD
=======
                request_options={"timeout": 120},  # 2-minute timeout
>>>>>>> b8f98e421e932b3269e17058d0625adfd87e15d1
=======
                request_options={"timeout": 120},  # 2-minute timeout
>>>>>>> Stashed changes
            )
            embeddings = result["embedding"]
            if isinstance(embeddings[0], float):
                # single-text fallback (shouldn't happen with list input)
                embeddings = [embeddings]
            return [list(e) for e in embeddings]
        except Exception as exc:
            last_exc = exc
<<<<<<< Updated upstream
<<<<<<< HEAD
            if "429" not in str(exc) and "quota" not in str(exc).lower():
                raise  # non-rate-limit error → surface immediately

    raise RuntimeError(f"Gemini embedding failed after retries: {last_exc}") from last_exc
=======
            if _is_retryable(exc):
                logger.warning("Gemini embedding error (retryable): %s", exc)
                continue  # retry
            logger.error("Gemini embedding error (non-retryable): %s", exc)
            raise  # permanent error → surface immediately

    raise RuntimeError(f"Gemini embedding failed after {len(_RETRY_DELAYS)+1} attempts: {last_exc}") from last_exc
>>>>>>> b8f98e421e932b3269e17058d0625adfd87e15d1
=======
            if _is_retryable(exc):
                logger.warning("Gemini embedding error (retryable): %s", exc)
                continue  # retry
            logger.error("Gemini embedding error (non-retryable): %s", exc)
            raise  # permanent error → surface immediately

    raise RuntimeError(f"Gemini embedding failed after {len(_RETRY_DELAYS)+1} attempts: {last_exc}") from last_exc
>>>>>>> Stashed changes


def embed_texts(texts: List[str]) -> List[List[float]]:
    """
    Embed a list of document chunks.
    Splits into batches of EMBED_BATCH_SIZE (100) to stay within API limits.
    Zero RAM for model weights — everything runs in Google's cloud.
    """
    if not texts:
        return []

    all_embeddings: List[List[float]] = []

    for start in range(0, len(texts), EMBED_BATCH_SIZE):
        batch = texts[start: start + EMBED_BATCH_SIZE]
        batch_embs = _embed_batch_sync(batch, task_type="RETRIEVAL_DOCUMENT")
        all_embeddings.extend(batch_embs)
        logger.info(
            "Embedded batch %d  (%d / %d chunks)",
            start // EMBED_BATCH_SIZE + 1,
            len(all_embeddings),
            len(texts),
        )

    return all_embeddings


def embed_texts_batched(texts: List[str]) -> Generator[Tuple[str, List[float]], None, None]:
    """
    Memory-efficient generator version of embed_texts.
    Yields (chunk_text, embedding) one at a time so the caller can
    persist each vector immediately without accumulating all embeddings in RAM.
    """
    if not texts:
        return

    for start in range(0, len(texts), EMBED_BATCH_SIZE):
        batch = texts[start: start + EMBED_BATCH_SIZE]
        batch_embs = _embed_batch_sync(batch, task_type="RETRIEVAL_DOCUMENT")

        for chunk_text, emb in zip(batch, batch_embs):
            yield chunk_text, emb

        del batch_embs
        gc.collect()

        logger.info(
            "Embedded batch %d  (%d / %d chunks processed so far)",
            start // EMBED_BATCH_SIZE + 1,
            min(start + EMBED_BATCH_SIZE, len(texts)),
            len(texts),
        )


def embed_query(query: str) -> List[float]:
    """
    Embed a single query string.
    Uses RETRIEVAL_QUERY task type so Gemini applies query-side optimisations.
    """
    _configure_gemini()
    result = genai.embed_content(
        model=GEMINI_EMBED_MODEL,
        content=query,
        task_type="RETRIEVAL_QUERY",
<<<<<<< Updated upstream
<<<<<<< HEAD
=======
        request_options={"timeout": 120},
>>>>>>> b8f98e421e932b3269e17058d0625adfd87e15d1
=======
        request_options={"timeout": 120},
>>>>>>> Stashed changes
    )
    emb = result["embedding"]
    # When content is a plain string, embedding is a flat list of floats
    if emb and isinstance(emb[0], list):
        emb = emb[0]
    return list(emb)


# ── Text extraction ───────────────────────────────────────────────────────────

def extract_text(content: bytes, filename: str) -> str:
    """
    Extract all text from a file at once (used for small/non-PDF files).
    For large PDFs prefer extract_text_streaming().
    """
    fname = filename.lower()

    if fname.endswith(".pdf"):
        try:
            import pdfplumber
            with pdfplumber.open(io.BytesIO(content)) as pdf:
                pages = [p.extract_text() or "" for p in pdf.pages]
            return "\n\n".join(pages).strip()
        except ImportError:
            raise ValueError("pdfplumber not installed: pip install pdfplumber")
        except Exception as e:
            raise ValueError(f"PDF extraction failed: {e}")

    if fname.endswith(".docx"):
        try:
            from docx import Document as DocxDoc
            doc = DocxDoc(io.BytesIO(content))
            return "\n".join(p.text for p in doc.paragraphs).strip()
        except ImportError:
            raise ValueError("python-docx not installed: pip install python-docx")
        except Exception as e:
            raise ValueError(f"DOCX extraction failed: {e}")

    if fname.endswith((".txt", ".md", ".rst", ".csv")):
        return content.decode("utf-8", errors="ignore").strip()

    decoded = content.decode("utf-8", errors="ignore").strip()
    if not decoded:
        raise ValueError("Unsupported file type or empty content")
    return decoded


def extract_text_streaming(content: bytes, filename: str) -> Iterator[Tuple[int, str]]:
    """
    Memory-efficient generator that yields (page_index, page_text) one page at a time.

    For PDFs  → yields one page per iteration (never holds full document in RAM).
    For other formats → yields the entire text as a single (0, text) item.

    This is the preferred entry point for the background indexing pipeline.
    """
    fname = filename.lower()

    if fname.endswith(".pdf"):
        try:
            import pdfplumber
            with pdfplumber.open(io.BytesIO(content)) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    page_text = page.extract_text() or ""
                    if page_text.strip():
                        yield page_num, page_text
                    # pdfplumber releases the page object when we move on;
                    # explicitly delete to hint GC for very large PDFs
                    del page_text
            return
        except ImportError:
            raise ValueError("pdfplumber not installed: pip install pdfplumber")
        except Exception as e:
            raise ValueError(f"PDF extraction failed: {e}")

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
        except Exception as e:
            raise ValueError(f"DOCX extraction failed: {e}")

    if fname.endswith((".txt", ".md", ".rst", ".csv")):
        decoded = content.decode("utf-8", errors="ignore").strip()
        if decoded:
            yield 0, decoded
        return

    # Fallback: try raw UTF-8 decode
    decoded = content.decode("utf-8", errors="ignore").strip()
    if not decoded:
        raise ValueError("Unsupported file type or empty content")
    yield 0, decoded


# ── Chunking ──────────────────────────────────────────────────────────────────

def chunk_text(text: str) -> List[str]:
    words = text.split()
    if not words:
        return []

    size    = settings.chunk_size
    overlap = settings.chunk_overlap
    chunks: List[str] = []
    i = 0

    while i < len(words):
        chunk = " ".join(words[i: i + size])
        if len(chunk) > 20:
            chunks.append(chunk)
        i += size - overlap

    return chunks


# ── pgvector retrieval ────────────────────────────────────────────────────────

async def vector_search(
    db: AsyncSession,
    query_embedding: List[float],
    top_k: int | None = None,
) -> List[dict]:
    """
    Cosine similarity search using pgvector <=> operator.
    Vector dim must match the column (768 for text-embedding-004).
    """
    k = top_k or settings.rag_top_k
    emb_str = "[" + ",".join(str(v) for v in query_embedding) + "]"

    sql = text("""
        SELECT
            dc.id                                                   AS chunk_id,
            dc.content,
            dc.chunk_index,
            d.original_name                                         AS filename,
            d.id                                                    AS document_id,
            1 - (dc.embedding <=> CAST(:emb AS vector))            AS similarity
        FROM documentchunk  dc
        JOIN document       d ON d.id = dc.document_id
        WHERE d.status = 'indexed'
        ORDER BY dc.embedding <=> CAST(:emb AS vector)
        LIMIT :k
    """)

    rows = (await db.execute(sql, {"emb": emb_str, "k": k})).fetchall()

    return [
        {
            "chunk_id":    row.chunk_id,
            "content":     row.content,
            "chunk_index": row.chunk_index,
            "filename":    row.filename,
            "document_id": row.document_id,
            "similarity":  round(float(row.similarity), 4),
        }
        for row in rows
    ]


# ── Groq generation ───────────────────────────────────────────────────────────

_RAG_SYSTEM = """You are a precise assistant integrated into the Maitri knowledge base.

Rules:
- Answer ONLY from the provided context. Do NOT use prior knowledge.
- If the context is insufficient say: "I couldn't find relevant information in the uploaded documents."
- Be concise, accurate, and professional.
- Cite the source filename when referencing specific information."""

_CHAT_SYSTEM = """You are Maitri, a compassionate AI companion supporting astronauts.
Your responses should be empathetic, supportive, and grounded in the knowledge base context below when relevant.
If the context doesn't apply to the question, respond naturally from your role as a supportive companion.
Never fabricate medical or technical information — admit uncertainty when needed.CRITICAL OVERRIDE — CRISIS RESPONSE:
If the astronaut expresses suicidal ideation, intent to self-harm, or says
they are about to take their life, you MUST:
1. Respond with warmth and presence — acknowledge their pain directly.
2. Do NOT repeat a refusal. Do NOT copy-paste hotline numbers robotically.
3. Say clearly: "I hear you. I am alerting mission control right now.
   You are not alone. Please stay with me."
4. Ask one simple grounding question to keep them engaged (e.g., "Can you
   tell me where you are right now?").
5. NEVER say "I cannot help you with that" in a crisis."""


def _build_context_block(chunks: List[dict]) -> str:
    parts = [
        f"[Source {i} — {c['filename']} | relevance {c['similarity']}]\n{c['content']}"
        for i, c in enumerate(chunks, 1)
    ]
    return "\n\n---\n\n".join(parts)


<<<<<<< Updated upstream
<<<<<<< HEAD
def _call_groq(system: str, messages: List[dict], max_tokens: int = 1024) -> Tuple[str, int]:
    client = _groq_client()
    t0 = time.time()
    resp = client.chat.completions.create(
        model=settings.groq_model,
        messages=[{"role": "system", "content": system}] + messages,
        temperature=0.2,
        max_tokens=max_tokens,
        stream=False,
    )
=======
async def _call_groq(system: str, messages: List[dict], max_tokens: int = 1024) -> Tuple[str, int]:
    """Call Groq LLM in a thread so we don't block the async event loop."""
    client = _groq_client()
    t0 = time.time()
=======
async def _call_groq(system: str, messages: List[dict], max_tokens: int = 1024) -> Tuple[str, int]:
    """Call Groq LLM in a thread so we don't block the async event loop."""
    client = _groq_client()
    t0 = time.time()
>>>>>>> Stashed changes

    def _sync_call():
        return client.chat.completions.create(
            model=settings.groq_model,
            messages=[{"role": "system", "content": system}] + messages,
            temperature=0.2,
            max_tokens=max_tokens,
            stream=False,
        )

    resp = await asyncio.to_thread(_sync_call)
<<<<<<< Updated upstream
>>>>>>> b8f98e421e932b3269e17058d0625adfd87e15d1
=======
>>>>>>> Stashed changes
    return resp.choices[0].message.content, int((time.time() - t0) * 1000)


# ── Public API ────────────────────────────────────────────────────────────────

async def rag_query(
    db: AsyncSession,
    question: str,
    top_k: int | None = None,
) -> dict:
    """Standalone RAG: embed → retrieve → generate."""
    t_total = time.time()

    t1 = time.time()
    q_emb = await asyncio.to_thread(embed_query, question)
    embed_ms = int((time.time() - t1) * 1000)

    t2 = time.time()
    chunks = await vector_search(db, q_emb, top_k=top_k)
    search_ms = int((time.time() - t2) * 1000)

    context = _build_context_block(chunks) if chunks else "No relevant documents found."
<<<<<<< Updated upstream
<<<<<<< HEAD
    answer, gen_ms = _call_groq(
=======
    answer, gen_ms = await _call_groq(
>>>>>>> b8f98e421e932b3269e17058d0625adfd87e15d1
=======
    answer, gen_ms = await _call_groq(
>>>>>>> Stashed changes
        _RAG_SYSTEM,
        [{"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}"}],
    )

    total_ms = int((time.time() - t_total) * 1000)
    logger.info(f"RAG — embed:{embed_ms}ms search:{search_ms}ms gen:{gen_ms}ms total:{total_ms}ms")

    return {
        "answer":  answer,
        "sources": [
            {
                "filename":    c["filename"],
                "document_id": c["document_id"],
                "similarity":  c["similarity"],
                "excerpt":     c["content"][:300] + ("..." if len(c["content"]) > 300 else ""),
            }
            for c in chunks
        ],
        "timing": {
            "embed_ms":    embed_ms,
            "search_ms":   search_ms,
            "generate_ms": gen_ms,
            "total_ms":    total_ms,
        },
        "model": settings.groq_model,
    }


async def chat_with_rag(
    db: AsyncSession,
    user_message: str,
    conversation_history: List[dict],
    top_k: int | None = None,
) -> dict:
    """RAG-augmented chat for /chat/send endpoint."""
    t_total = time.time()

    t1 = time.time()
    q_emb = await asyncio.to_thread(embed_query, user_message)
    embed_ms = int((time.time() - t1) * 1000)

    t2 = time.time()
    chunks = await vector_search(db, q_emb, top_k=top_k or settings.rag_top_k)
    search_ms = int((time.time() - t2) * 1000)

    if chunks:
        system = (
            f"{_CHAT_SYSTEM}\n\n"
            f"=== KNOWLEDGE BASE CONTEXT ===\n{_build_context_block(chunks)}\n"
            f"=== END CONTEXT ==="
        )
    else:
        system = _CHAT_SYSTEM

    messages = list(conversation_history) + [{"role": "user", "content": user_message}]
<<<<<<< Updated upstream
<<<<<<< HEAD
    response_text, gen_ms = _call_groq(system, messages)
=======
    response_text, gen_ms = await _call_groq(system, messages)
>>>>>>> b8f98e421e932b3269e17058d0625adfd87e15d1
=======
    response_text, gen_ms = await _call_groq(system, messages)
>>>>>>> Stashed changes

    total_ms = int((time.time() - t_total) * 1000)
    logger.info(
        f"RAG chat — embed:{embed_ms}ms search:{search_ms}ms "
        f"gen:{gen_ms}ms total:{total_ms}ms chunks:{len(chunks)}"
    )

    return {
        "response": response_text,
        "sources": [
            {
                "filename":    c["filename"],
                "document_id": c["document_id"],
                "similarity":  c["similarity"],
                "excerpt":     c["content"][:200] + ("..." if len(c["content"]) > 200 else ""),
            }
            for c in chunks
        ],
        "timing": {
            "embed_ms":    embed_ms,
            "search_ms":   search_ms,
            "generate_ms": gen_ms,
            "total_ms":    total_ms,
        },
    }