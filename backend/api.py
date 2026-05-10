"""REST API endpoints."""

import asyncio
import io
import json
import shutil
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from PIL import Image

from backend import session as sess
from backend.config import (
    ALL_EXTENSIONS,
    APP_PASSWORD,
    MAX_FILE_SIZE_BYTES,
    MAX_TOTAL_SIZE_BYTES,
)
from backend.exporter import export_images, export_pdf
from backend.loader import load_file
from backend.resize import resize_all

router = APIRouter()


# ─── Auth ─────────────────────────────────────────────────────────────────────

@router.post("/api/auth")
async def auth(password: str = Form(...)):
    if password != APP_PASSWORD:
        raise HTTPException(status_code=401, detail="Wrong password")
    sid = sess.create_session()
    return {"session_id": sid}


# ─── Session guard ─────────────────────────────────────────────────────────────

def _require_session(session_id: str) -> str:
    if not sess.session_exists(session_id):
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    sess.touch_session(session_id)
    return session_id


# ─── File metadata helper ──────────────────────────────────────────────────────

def _meta_path(session_dir: Path) -> Path:
    return session_dir / "_meta.json"


def _load_meta(session_dir: Path) -> list[dict]:
    p = _meta_path(session_dir)
    if not p.exists():
        return []
    return json.loads(p.read_text())


def _save_meta(session_dir: Path, meta: list[dict]) -> None:
    _meta_path(session_dir).write_text(json.dumps(meta, ensure_ascii=False))


# ─── Upload ───────────────────────────────────────────────────────────────────

@router.post("/api/upload")
async def upload(
    files: list[UploadFile] = File(...),
    session_id: str = Form(...),
):
    sid = _require_session(session_id)
    s_dir = sess.session_dir(sid)
    meta = _load_meta(s_dir)

    total_existing = sum(
        (s_dir / m["stored_name"]).stat().st_size
        for m in meta
        if (s_dir / m["stored_name"]).exists()
    )

    results = []
    for f in files:
        ext = Path(f.filename or "").suffix.lower()
        if ext not in ALL_EXTENSIONS:
            results.append({"filename": f.filename, "error": "Unsupported file type"})
            continue

        data = await f.read()
        if len(data) > MAX_FILE_SIZE_BYTES:
            results.append({
                "filename": f.filename,
                "error": f"File exceeds {MAX_FILE_SIZE_BYTES // 1024 // 1024} MB limit",
            })
            continue

        if total_existing + len(data) > MAX_TOTAL_SIZE_BYTES:
            results.append({"filename": f.filename, "error": "Total upload size limit exceeded"})
            break

        # Save with a collision-safe name
        import uuid as _uuid
        stored_name = f"{_uuid.uuid4().hex}{ext}"
        file_path = s_dir / stored_name
        file_path.write_bytes(data)
        total_existing += len(data)

        entry = {
            "id": _uuid.uuid4().hex,
            "original_name": f.filename,
            "stored_name": stored_name,
            "rotation": 0,  # degrees CW
            "size": len(data),
        }
        meta.append(entry)
        results.append({"filename": f.filename, "id": entry["id"], "ok": True})

    _save_meta(s_dir, meta)
    return {"files": results, "file_list": meta}


# ─── File list ────────────────────────────────────────────────────────────────

@router.get("/api/files")
async def list_files(session_id: str):
    sid = _require_session(session_id)
    return {"file_list": _load_meta(sess.session_dir(sid))}


# ─── Reorder ──────────────────────────────────────────────────────────────────

@router.post("/api/reorder")
async def reorder(session_id: str = Form(...), order: str = Form(...)):
    """order is a JSON array of file IDs in the new sequence."""
    sid = _require_session(session_id)
    s_dir = sess.session_dir(sid)
    meta = _load_meta(s_dir)
    id_to_entry = {m["id"]: m for m in meta}
    new_order = json.loads(order)
    reordered = [id_to_entry[fid] for fid in new_order if fid in id_to_entry]
    _save_meta(s_dir, reordered)
    return {"file_list": reordered}


# ─── Rotate ───────────────────────────────────────────────────────────────────

@router.post("/api/rotate")
async def rotate(session_id: str = Form(...), file_id: str = Form(...), degrees: int = Form(...)):
    sid = _require_session(session_id)
    s_dir = sess.session_dir(sid)
    meta = _load_meta(s_dir)
    for m in meta:
        if m["id"] == file_id:
            m["rotation"] = (m["rotation"] + degrees) % 360
            break
    _save_meta(s_dir, meta)
    return {"file_list": meta}


# ─── Delete single file ───────────────────────────────────────────────────────

@router.post("/api/delete")
async def delete_file(session_id: str = Form(...), file_id: str = Form(...)):
    sid = _require_session(session_id)
    s_dir = sess.session_dir(sid)
    meta = _load_meta(s_dir)
    new_meta = []
    for m in meta:
        if m["id"] == file_id:
            f = s_dir / m["stored_name"]
            if f.exists():
                f.unlink()
        else:
            new_meta.append(m)
    _save_meta(s_dir, new_meta)
    return {"file_list": new_meta}


# ─── Thumbnail ───────────────────────────────────────────────────────────────

@router.get("/api/thumbnail/{session_id}/{file_id}")
async def thumbnail(session_id: str, file_id: str):
    sid = _require_session(session_id)
    s_dir = sess.session_dir(sid)
    meta = _load_meta(s_dir)
    entry = next((m for m in meta if m["id"] == file_id), None)
    if entry is None:
        raise HTTPException(status_code=404, detail="File not found")

    file_path = s_dir / entry["stored_name"]
    thumb_path = s_dir / f"_thumb_{file_id}.jpg"

    if not thumb_path.exists():
        try:
            pages = await load_file(file_path)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
        img = pages[0]
        rotation = entry.get("rotation", 0)
        if rotation:
            img = img.rotate(-rotation, expand=True)
        img.thumbnail((200, 200), Image.Resampling.LANCZOS)
        img.convert("RGB").save(thumb_path, "JPEG", quality=80)

    return FileResponse(thumb_path, media_type="image/jpeg")


# ─── Convert + Download ───────────────────────────────────────────────────────

@router.post("/api/convert")
async def convert(
    session_id: str = Form(...),
    output_format: str = Form("pdf"),   # "png" | "jpg" | "pdf"
    size_mode: str = Form("max"),       # "max" | "min" | "manual" | "none"
    algorithm: str = Form("lanczos"),
    manual_px: int = Form(0),
):
    sid = _require_session(session_id)
    s_dir = sess.session_dir(sid)
    meta = _load_meta(s_dir)

    if not meta:
        raise HTTPException(status_code=400, detail="No files uploaded")

    # Load all files → images
    all_images: list[Image.Image] = []
    all_names: list[str] = []
    for m in meta:
        file_path = s_dir / m["stored_name"]
        try:
            pages = await load_file(file_path)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to load {m['original_name']}: {e}")

        rotation = m.get("rotation", 0)
        if rotation:
            pages = [p.rotate(-rotation, expand=True) for p in pages]

        for i, page in enumerate(pages):
            all_images.append(page)
            all_names.append(m["original_name"])

    # Resize
    manual = manual_px if size_mode == "manual" else None
    try:
        all_images = resize_all(all_images, size_mode, algorithm, manual)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Clean previous output
    for p in s_dir.glob("output.*"):
        p.unlink(missing_ok=True)

    # Export
    fmt = output_format.lower()
    if fmt in ("png", "jpg"):
        result_path = export_images(all_images, all_names, fmt, s_dir)
        media_type = "application/zip"
        filename = "output.zip"
    elif fmt == "pdf":
        result_path = export_pdf(all_images, s_dir)
        media_type = "application/pdf"
        filename = "output.pdf"
    else:
        raise HTTPException(status_code=400, detail=f"Unknown output format: {fmt}")

    return {"download_url": f"/api/download/{sid}", "filename": filename}


@router.get("/api/download/{session_id}")
async def download(session_id: str):
    sid = _require_session(session_id)
    s_dir = sess.session_dir(sid)

    for ext in ("zip", "pdf"):
        p = s_dir / f"output.{ext}"
        if p.exists():
            media = "application/zip" if ext == "zip" else "application/pdf"
            return FileResponse(
                p,
                media_type=media,
                filename=p.name,
                headers={"Content-Disposition": f'attachment; filename="{p.name}"'},
            )

    raise HTTPException(status_code=404, detail="No output file found. Run /api/convert first.")
