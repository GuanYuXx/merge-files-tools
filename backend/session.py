import asyncio
import time
import uuid
from pathlib import Path

from backend.config import SESSIONS_DIR, SESSION_TTL_MINUTES, CLEANUP_INTERVAL_SECONDS

# session_id -> last_active timestamp
_sessions: dict[str, float] = {}
_lock = asyncio.Lock()


def create_session() -> str:
    sid = str(uuid.uuid4())
    session_dir(sid).mkdir(parents=True, exist_ok=True)
    _sessions[sid] = time.time()
    return sid


def session_dir(sid: str) -> Path:
    return SESSIONS_DIR / sid


def touch_session(sid: str) -> bool:
    """Update last-active time. Return False if session does not exist."""
    if sid not in _sessions:
        return False
    _sessions[sid] = time.time()
    return True


def session_exists(sid: str) -> bool:
    return sid in _sessions and session_dir(sid).exists()


async def cleanup_expired() -> int:
    """Remove sessions inactive longer than SESSION_TTL_MINUTES. Return count removed."""
    import shutil

    now = time.time()
    ttl = SESSION_TTL_MINUTES * 60
    to_remove: list[str] = []

    async with _lock:
        for sid, last in list(_sessions.items()):
            if now - last > ttl:
                to_remove.append(sid)
        for sid in to_remove:
            del _sessions[sid]

    for sid in to_remove:
        d = session_dir(sid)
        if d.exists():
            shutil.rmtree(d, ignore_errors=True)

    return len(to_remove)


def startup_cleanup() -> None:
    """Synchronous scan at startup to remove stale directories not in memory."""
    import shutil

    if not SESSIONS_DIR.exists():
        return
    for d in SESSIONS_DIR.iterdir():
        if d.is_dir() and d.name not in _sessions:
            shutil.rmtree(d, ignore_errors=True)


async def background_cleanup_loop() -> None:
    """Periodically clean expired sessions."""
    while True:
        await asyncio.sleep(CLEANUP_INTERVAL_SECONDS)
        n = await cleanup_expired()
        if n:
            print(f"[session] Removed {n} expired session(s).")
