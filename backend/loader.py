"""Load any supported file → list of PIL Images."""

import shutil
import tempfile
from pathlib import Path

from PIL import Image

from backend.config import IMAGE_EXTENSIONS, PDF_EXTENSIONS, OFFICE_EXTENSIONS


async def load_file(path: Path) -> list[Image.Image]:
    """Return a list of PIL Images for the given file."""
    ext = path.suffix.lower()

    if ext in IMAGE_EXTENSIONS:
        return _load_image(path)
    elif ext in PDF_EXTENSIONS:
        return _load_pdf(path)
    elif ext in OFFICE_EXTENSIONS:
        return await _load_office(path)
    else:
        raise ValueError(f"Unsupported file type: {ext}")


def _load_image(path: Path) -> list[Image.Image]:
    img = Image.open(path)
    frames: list[Image.Image] = []
    try:
        while True:
            frames.append(img.copy().convert("RGBA"))
            img.seek(img.tell() + 1)
    except EOFError:
        pass
    if not frames:
        frames = [img.convert("RGBA")]
    return frames


def _load_pdf(path: Path) -> list[Image.Image]:
    import fitz  # PyMuPDF

    doc = fitz.open(str(path))
    images: list[Image.Image] = []
    for page in doc:
        mat = fitz.Matrix(2.0, 2.0)  # 2x zoom → ~144 dpi
        pix = page.get_pixmap(matrix=mat, alpha=False)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        images.append(img.convert("RGBA"))
    doc.close()
    return images


async def _load_office(path: Path) -> list[Image.Image]:
    from backend.office import convert_to_pdf

    # Copy to a temp dir so LibreOffice output doesn't pollute the session dir
    tmp_dir = Path(tempfile.mkdtemp())
    try:
        tmp_src = tmp_dir / path.name
        shutil.copy2(path, tmp_src)
        pdf_path = await convert_to_pdf(tmp_src)
        return _load_pdf(pdf_path)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
