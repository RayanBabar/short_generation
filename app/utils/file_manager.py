"""File management utilities for video uploads and outputs."""

import uuid
import aiofiles
from pathlib import Path
from fastapi import UploadFile

from app.config import get_settings


async def save_upload_file(upload_file: UploadFile) -> tuple[str, Path]:
    """
    Save an uploaded file to the uploads directory.

    Args:
        upload_file: FastAPI UploadFile object

    Returns:
        Tuple of (video_id, file_path)
    """
    settings = get_settings()
    settings.ensure_directories()

    # Generate unique video ID
    video_id = str(uuid.uuid4())

    # Get file extension from original filename
    original_name = upload_file.filename or "video.mp4"
    extension = Path(original_name).suffix or ".mp4"

    # Create file path
    file_path = settings.upload_dir / f"{video_id}{extension}"

    # Save file
    async with aiofiles.open(file_path, "wb") as f:
        content = await upload_file.read()
        await f.write(content)

    return video_id, file_path


def get_upload_path(video_id: str) -> Path | None:
    """
    Get the file path for an uploaded video by its ID.

    Args:
        video_id: The video's unique identifier

    Returns:
        Path to the video file, or None if not found
    """
    settings = get_settings()

    # Video extensions to prioritize (in order)
    video_extensions = [".mp4", ".mov", ".avi", ".mkv", ".webm", ".mpeg"]
    
    # First, search for video files (prioritize over audio)
    for ext in video_extensions:
        video_path = settings.upload_dir / f"{video_id}{ext}"
        if video_path.is_file():
            return video_path

    # Fallback: search for any matching file
    for file_path in settings.upload_dir.glob(f"{video_id}.*"):
        if file_path.is_file():
            return file_path

    return None


def get_output_path(short_id: str) -> Path | None:
    """
    Get the file path for a generated short by its ID.

    Args:
        short_id: The short's unique identifier

    Returns:
        Path to the short file, or None if not found
    """
    settings = get_settings()

    for file_path in settings.output_dir.glob(f"{short_id}.*"):
        if file_path.is_file():
            return file_path

    return None


def generate_short_id(video_id: str, index: int) -> str:
    """
    Generate a unique ID for a short video.

    Args:
        video_id: Source video ID
        index: Short index number

    Returns:
        Unique short ID
    """
    short_uuid = str(uuid.uuid4())[:8]
    return f"{video_id[:8]}_short_{index}_{short_uuid}"


def get_file_size(file_path: Path) -> int:
    """Get file size in bytes."""
    return file_path.stat().st_size if file_path.exists() else 0


def cleanup_video(video_id: str) -> bool:
    """
    Remove uploaded video and its generated shorts.

    Args:
        video_id: The video's unique identifier

    Returns:
        True if cleanup was successful
    """
    settings = get_settings()
    cleaned = False

    # Remove uploaded video
    upload_path = get_upload_path(video_id)
    if upload_path and upload_path.exists():
        upload_path.unlink()
        cleaned = True

    # Remove generated shorts
    for short_path in settings.output_dir.glob(f"{video_id[:8]}_short_*"):
        short_path.unlink()
        cleaned = True

    return cleaned
