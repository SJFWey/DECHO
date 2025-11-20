from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from server.routers import audio, config
import os
from contextlib import asynccontextmanager
from backend.asr import get_asr_instance
import logging

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Preload ASR model
    logger.info("Preloading ASR model...")
    get_asr_instance()
    logger.info("ASR model loaded.")
    yield


app = FastAPI(title="Hearing API", version="1.0.0", lifespan=lifespan)

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


@app.get("/")
async def root():
    return {"message": "Hearing API is running"}
