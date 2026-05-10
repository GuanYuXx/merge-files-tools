"""LibreOffice headless wrapper — always use this module; never call subprocess in routes."""

import asyncio
import shutil
import subprocess
import tempfile
from pathlib import Path

from backend.config import MAX_PARALLEL_OFFICE

_semaphore: asyncio.Semaphore | None = None


def _get_semaphore() -> asyncio.Semaphore:
    global _semaphore
    if _semaphore is None:
        _semaphore = asyncio.Semaphore(MAX_PARALLEL_OFFICE)
    return _semaphore


def _find_libreoffice() -> str:
    for name in ("libreoffice", "soffice"):
        path = shutil.which(name)
        if path:
            return path
    raise FileNotFoundError(
        "LibreOffice not found. Install it (apt install libreoffice) or add it to PATH."
    )


async def convert_to_pdf(src: Path, timeout: int = 120) -> Path:
    """Convert an Office file to PDF using LibreOffice headless.

    Returns the path to the generated PDF (in a temp dir next to src).
    Caller is responsible for cleanup.
    """
    async with _get_semaphore():
        lo = _find_libreoffice()
        out_dir = src.parent
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None, _run_libreoffice, lo, str(src), str(out_dir), timeout
        )

    pdf_path = out_dir / (src.stem + ".pdf")
    if not pdf_path.exists():
        raise RuntimeError(f"LibreOffice did not produce {pdf_path}")
    return pdf_path


def _run_libreoffice(lo: str, src: str, out_dir: str, timeout: int) -> None:
    result = subprocess.run(
        [lo, "--headless", "--convert-to", "pdf", "--outdir", out_dir, src],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"LibreOffice exited with code {result.returncode}:\n{result.stderr}"
        )
