import os
from pathlib import Path

# Base directories
BASE_DIR = Path(__file__).parent.parent
SESSIONS_DIR = BASE_DIR / "sessions"
SESSIONS_DIR.mkdir(exist_ok=True)

# Auth
APP_PASSWORD: str = os.environ.get("APP_PASSWORD", "changeme")

# Server
HOST: str = os.environ.get("HOST", "0.0.0.0")
PORT: int = int(os.environ.get("PORT", "8000"))

# Upload limits
MAX_FILE_SIZE_MB: int = int(os.environ.get("MAX_FILE_SIZE_MB", "200"))
MAX_TOTAL_SIZE_MB: int = int(os.environ.get("MAX_TOTAL_SIZE_MB", "1024"))
MAX_FILE_SIZE_BYTES: int = MAX_FILE_SIZE_MB * 1024 * 1024
MAX_TOTAL_SIZE_BYTES: int = MAX_TOTAL_SIZE_MB * 1024 * 1024

# Session
SESSION_TTL_MINUTES: int = int(os.environ.get("SESSION_TTL_MINUTES", "60"))
CLEANUP_INTERVAL_SECONDS: int = int(os.environ.get("CLEANUP_INTERVAL_SECONDS", "3600"))

# LibreOffice concurrency
MAX_PARALLEL_OFFICE: int = int(os.environ.get("MAX_PARALLEL_OFFICE", "2"))

# CORS
ALLOWED_ORIGINS: list[str] = [
    o.strip()
    for o in os.environ.get("ALLOWED_ORIGINS", "").split(",")
    if o.strip()
]

# Supported file types
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".webp", ".tiff", ".tif", ".gif"}
PDF_EXTENSIONS = {".pdf"}
OFFICE_EXTENSIONS = {".docx", ".xlsx", ".pptx", ".doc", ".xls", ".ppt"}
ALL_EXTENSIONS = IMAGE_EXTENSIONS | PDF_EXTENSIONS | OFFICE_EXTENSIONS
