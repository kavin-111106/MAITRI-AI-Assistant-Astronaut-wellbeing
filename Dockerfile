# ── Stage 1: dependency builder ───────────────────────────────────────────────
# Compiles wheels for packages that need C extensions (psycopg, librosa, opencv, etc.)
FROM python:3.11-slim AS builder
 
WORKDIR /build
 
# System libs needed to compile native deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    libffi-dev \
    libssl-dev \
    libpq-dev \
    libsndfile1-dev \
    libsm6 \
    libxext6 \
    libxrender-dev \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*
 
COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt
 
 
# ── Stage 2: runtime image ─────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime
 
WORKDIR /app
 
# Runtime-only system libs (no compilers)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    libsndfile1 \
    libsm6 \
    libxext6 \
    libxrender1 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*
 
# Copy pre-built wheels and install — no compiler needed
COPY --from=builder /wheels /wheels
COPY requirements.txt .
RUN pip install --no-cache-dir --no-index --find-links=/wheels -r requirements.txt \
    && rm -rf /wheels requirements.txt
 
# Copy application source
COPY . .
 
# Copy and permission the entrypoint script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
 
# Non-root user for security
RUN addgroup --system maitri && adduser --system --ingroup maitri maitri
USER maitri
 
EXPOSE 8000
 
# entrypoint runs: alembic upgrade head → uvicorn
ENTRYPOINT ["/entrypoint.sh"]