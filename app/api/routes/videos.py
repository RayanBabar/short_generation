"""Video upload and transcription API routes."""

from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.api.dependencies import (
    get_transcriber,
    validate_video_id,
)
from app.schemas.responses import VideoUploadResponse
from app.schemas.transcription import TranscriptionResponse
from app.services.transcription import TranscriptionService
from app.services.video_clipper import get_video_clipper_service
from app.utils.file_manager import save_upload_file, get_file_size

router = APIRouter(prefix="/videos", tags=["Videos"])


# Allowed video MIME types
ALLOWED_MIME_TYPES = {
    "video/mp4",
    "video/quicktime",
    "video/x-msvideo",
    "video/x-matroska",
    "video/webm",
    "video/mpeg",
}


@router.post(
    "/upload",
    response_model=VideoUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a video file",
    description="Upload a video file for processing. Returns a unique video ID.",
)
async def upload_video(
    file: Annotated[UploadFile, File(description="Video file to upload")],
) -> VideoUploadResponse:
    """Upload a video file for processing."""
    # Validate file type
    content_type = file.content_type or ""
    if content_type not in ALLOWED_MIME_TYPES:
        # Check by extension as fallback
        if file.filename:
            ext = Path(file.filename).suffix.lower()
            if ext not in {".mp4", ".mov", ".avi", ".mkv", ".webm", ".mpeg"}:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Unsupported file type: {content_type}. Allowed: {ALLOWED_MIME_TYPES}",
                )

    # Save the uploaded file
    video_id, file_path = await save_upload_file(file)

    # Get file size
    file_size = get_file_size(file_path)

    # Try to get video duration
    duration = None
    try:
        clipper = get_video_clipper_service()
        duration_seconds = clipper.get_video_duration(file_path)
        if duration_seconds > 0:
            minutes = int(duration_seconds // 60)
            seconds = int(duration_seconds % 60)
            duration = f"{minutes:02d}:{seconds:02d}"
    except Exception:
        pass

    return VideoUploadResponse(
        video_id=video_id,
        filename=file.filename or "video.mp4",
        file_size=file_size,
        duration=duration,
    )


@router.post(
    "/{video_id}/transcribe",
    response_model=TranscriptionResponse,
    summary="Transcribe an uploaded video",
    description="Transcribe a previously uploaded video with speaker diarization and timestamps.",
)
async def transcribe_video(
    video_id: str,
    transcription_service: Annotated[TranscriptionService, Depends(get_transcriber)],
) -> TranscriptionResponse:
    """Transcribe an uploaded video."""
    video_path = validate_video_id(video_id)

    try:
        transcription = transcription_service.transcribe_video(video_path)

        return TranscriptionResponse(
            video_id=video_id,
            transcription=transcription,
            status="completed",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Transcription failed: {str(e)}",
        )
