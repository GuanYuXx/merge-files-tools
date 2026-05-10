"""FastAPI application entry point."""

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend import api, session
from backend.config import ALLOWED_ORIGINS, HOST, PORT


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: clean stale session dirs left from previous runs
    session.startup_cleanup()
    # Start periodic cleanup task
    task = asyncio.create_task(session.background_cleanup_loop())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


app = FastAPI(title="Merge Files Tool", lifespan=lifespan)

# CORS — allow configured origins (empty = same-origin only)
origins = ALLOWED_ORIGINS or []
if origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(api.router)

# Serve frontend
frontend_dir = Path(__file__).parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.main:app", host=HOST, port=PORT, reload=False)
