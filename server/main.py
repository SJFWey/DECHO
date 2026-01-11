from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from server.routers import audio, config
from server.database import engine, Base
import os
from contextlib import asynccontextmanager
from backend.asr import get_asr_instance
import logging

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables if they don't exist
    Base.metadata.create_all(bind=engine)

    # Preload ASR model
    logger.info("Preloading ASR model...")
    get_asr_instance()
    logger.info("ASR model loaded.")
    yield


app = FastAPI(title="DECHO API", version="1.0.0", lifespan=lifespan)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for audio playback
os.makedirs("output/uploads", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="output/uploads"), name="uploads")

os.makedirs("output/user_recordings", exist_ok=True)
app.mount(
    "/user_recordings",
    StaticFiles(directory="output/user_recordings"),
    name="user_recordings",
)

# Include routers
app.include_router(audio.router, prefix="/api/audio", tags=["audio"])
app.include_router(config.router, prefix="/api/config", tags=["config"])

import sys
from fastapi.responses import FileResponse

# Determine base directory
if getattr(sys, "frozen", False):
    base_dir = os.path.dirname(sys.executable)
else:
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

frontend_dist_name = "web" if getattr(sys, "frozen", False) else "web/out"
frontend_path = os.path.join(base_dir, frontend_dist_name)

if os.path.exists(frontend_path):
    # Mount _next static files
    next_static_path = os.path.join(frontend_path, "_next")
    if os.path.exists(next_static_path):
        app.mount("/_next", StaticFiles(directory=next_static_path), name="next")

    @app.get("/")
    async def serve_index():
        return FileResponse(os.path.join(frontend_path, "index.html"))

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        file_path = os.path.join(frontend_path, full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)

        # Fallback to index.html for SPA routing
        return FileResponse(os.path.join(frontend_path, "index.html"))

else:
    logger.warning(f"Frontend not found at {frontend_path}")

    @app.get("/")
    async def root():
        return {"message": "DECHO API is running (Frontend not found)"}


if __name__ == "__main__":
    import uvicorn
    import webbrowser
    import socket
    import threading
    import time

    if getattr(sys, "frozen", False):
        os.chdir(base_dir)
        logger.info(f"Running in frozen mode. CWD set to: {base_dir}")

    def find_free_port():
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("", 0))
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            return s.getsockname()[1]

    port = 8000
    # Check if 8000 is free
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        if s.connect_ex(("localhost", port)) == 0:
            # Port is open (in use), find another
            port = find_free_port()

    def open_browser():
        time.sleep(1.5)
        webbrowser.open(f"http://localhost:{port}")

    print(f"Starting server at http://localhost:{port}")
    threading.Thread(target=open_browser, daemon=True).start()

    uvicorn.run(app, host="127.0.0.1", port=port)
