FROM python:3.11-slim

# ── System deps: LibreOffice + fonts ──────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
        libreoffice-writer \
        libreoffice-calc \
        libreoffice-impress \
        # CJK fonts (Traditional Chinese)
        fonts-noto-cjk \
        # Western fonts
        fonts-dejavu \
        fonts-liberation \
        # Misc
        curl \
    && fc-cache -f \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ── Python deps ───────────────────────────────────────────────────
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── App code ──────────────────────────────────────────────────────
COPY backend/ backend/
COPY frontend/ frontend/

# ── Session dir (overridden by volume in compose) ─────────────────
RUN mkdir -p sessions

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
