"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.config import get_settings
from app.api.routes import videos, shorts
from app.utils.logging import setup_logging, get_logger

# Initialize logging
setup_logging()
logger = get_logger(__name__)

# Frontend directory
FRONTEND_DIR = Path(__file__).parent.parent / "frontend"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup/shutdown events."""
    # Startup
    settings = get_settings()
    settings.ensure_directories()
    
    logger.info("=" * 60)
    logger.info("🚀 YouTube Shorts Generator API Starting...")
    logger.info("=" * 60)
    logger.info(f"📁 Upload directory: {settings.upload_dir.absolute()}")
    logger.info(f"📁 Output directory: {settings.output_dir.absolute()}")
    logger.info(f"🤖 Gemini model: {settings.gemini_model}")
    logger.info(f"⏱️ Short duration: {settings.min_short_duration}-{settings.max_short_duration}s")
    logger.info("=" * 60)
    logger.info("✅ API is ready!")
    logger.info("=" * 60)

    yield

    # Shutdown
    logger.info("👋 Shutting down...")


# Create FastAPI application
app = FastAPI(
    title="YouTube Shorts Generator API",
    description="""
## Overview

Generate YouTube Shorts from longer videos using AI-powered analysis.

### Features

- **Video Transcription**: Transcribe videos with speaker diarization and timestamps
- **Shorts Identification**: AI-powered identification of viral-worthy segments
- **Video Clipping**: Automatically clip identified segments

### Workflow

1. **Upload** a video file
2. **Identify** potential shorts with virality scoring
3. **Generate** video clips for the identified shorts
4. **Download** the generated short videos

### Technology

- **Faster-Whisper** for precision local transcription
- **Google Gemini API** for semantic analysis and virality scoring
- **FFmpeg** for high-quality video processing
- **FastAPI** for the REST API
    """,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(videos.router, prefix="/api/v1")
app.include_router(shorts.router, prefix="/api/v1")

# Serve frontend static files
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


@app.get("/", tags=["Frontend"])
async def serve_frontend():
    """Serve the frontend application."""
    index_file = FRONTEND_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {
        "name": "YouTube Shorts Generator API",
        "version": "1.0.0",
        "docs": "/docs",
        "frontend": "Not found - place frontend files in /frontend directory",
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}

