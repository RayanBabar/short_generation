"""API route dependencies."""

from fastapi import Depends, HTTPException, status

from app.config import Settings, get_settings
from app.services.gemini_client import GeminiClient, get_gemini_client
from app.services.shorts_identifier import (
    ShortsIdentifierService,
    get_shorts_identifier_service,
)
from app.services.video_clipper import VideoClipperService, get_video_clipper_service
from app.utils.file_manager import get_upload_path


def get_config() -> Settings:
    """Dependency for getting application settings."""
    return get_settings()


def get_gemini() -> GeminiClient:
    """Dependency for getting Gemini client."""
    try:
        return get_gemini_client()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Gemini API not available: {str(e)}",
        )


def get_shorts_identifier() -> ShortsIdentifierService:
    """Dependency for getting shorts identifier service."""
    try:
        return get_shorts_identifier_service()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Shorts identifier not available: {str(e)}",
        )


def get_clipper() -> VideoClipperService:
    """Dependency for getting video clipper service."""
    try:
        return get_video_clipper_service()
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        )


def validate_video_id(video_id: str):
    """Validate that a video exists."""
    video_path = get_upload_path(video_id)
    if not video_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Video not found: {video_id}",
        )
    return video_path
