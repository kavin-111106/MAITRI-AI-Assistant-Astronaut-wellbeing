from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from .rate_limiter import limiter
from .router import auth, users, chat, admin,rag_router,health
import logging
import time

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("maitri")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Maitri backend starting up...")

    # Verify Gemini embedding SDK is configured
    try:
        from .rag_service import _configure_gemini, GEMINI_EMBED_MODEL
        _configure_gemini()
        logger.info(f"Gemini embedding model '{GEMINI_EMBED_MODEL}' — configured ✓")
    except Exception as e:
        logger.warning(f"Gemini embed probe failed (will surface on first embed call): {e}")

    yield
    logger.info("Maitri backend shutting down...")


app = FastAPI(lifespan=lifespan, title="Maitri AI", version="1.0.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── CORS — allow frontend dev servers to reach the API ────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",   # Vite default
        "http://localhost:3000",   # CRA / Next.js default
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(
        f"Unhandled error on {request.method} {request.url.path}: {exc}",
        exc_info=True,
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal server error occurred. Please try again later."},
    )


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = round((time.time() - start_time) * 1000, 2)
    logger.info(f"{request.method} {request.url.path} — {response.status_code} — {duration}ms")
    return response


app.include_router(users.router)
app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(admin.router)
app.include_router(rag_router.router)
app.include_router(health.router)

@app.get("/")
def root():
    return {"message": "Maitri AI — RAG-powered backend running"}


@app.get("/health")
def health():
    from .config import settings
    from .rag_service import GEMINI_EMBED_MODEL
    return {
        "status": "ok",
        "groq_model":    settings.groq_model,
        "embed_model":   GEMINI_EMBED_MODEL,
        "embed_backend": "Gemini API (cloud)",
    }