"""Export PIL Images to PNG / JPG / PDF."""

import io
import zipfile
from pathlib import Path

from PIL import Image


def export_images(
    images: list[Image.Image],
    names: list[str],
    fmt: str,  # "png" | "jpg"
    out_dir: Path,
) -> Path:
    """Save each image as a separate file, then zip them all.

    Returns path to the zip file.
    """
    ext = "jpg" if fmt == "jpg" else "png"
    pil_fmt = "JPEG" if fmt == "jpg" else "PNG"
    zip_path = out_dir / f"output.zip"

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for i, (img, name) in enumerate(zip(images, names)):
            stem = Path(name).stem
            filename = f"{stem}_{i + 1:03d}.{ext}"
            buf = io.BytesIO()
            if pil_fmt == "JPEG":
                img_rgb = img.convert("RGB")
                img_rgb.save(buf, format=pil_fmt, quality=95)
            else:
                img.save(buf, format=pil_fmt, optimize=True)
            zf.writestr(filename, buf.getvalue())

    return zip_path


def export_pdf(images: list[Image.Image], out_dir: Path) -> Path:
    """Merge all images into a single PDF using img2pdf (lossless for JPEG).

    Falls back to Pillow if img2pdf is not available.
    Returns path to the PDF.
    """
    pdf_path = out_dir / "output.pdf"

    try:
        import img2pdf

        # img2pdf needs JPEG or PNG bytes
        bufs: list[bytes] = []
        for img in images:
            buf = io.BytesIO()
            img.convert("RGB").save(buf, format="JPEG", quality=95)
            bufs.append(buf.getvalue())

        with open(pdf_path, "wb") as f:
            f.write(img2pdf.convert(bufs))

    except ImportError:
        # Fallback: Pillow PDF save
        rgb_images = [img.convert("RGB") for img in images]
        rgb_images[0].save(
            pdf_path,
            save_all=True,
            append_images=rgb_images[1:],
            format="PDF",
        )

    return pdf_path
