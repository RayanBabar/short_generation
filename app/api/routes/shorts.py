"""Shorts identification and generation API routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse

from app.api.dependencies import (
    get_shorts_identifier,
    get_clipper,
    validate_video_id,
)
from app.schemas.shorts import (
    ShortsIdentificationResponse,
    GenerateShortsResponse,
)
from app.services.shorts_identifier import ShortsIdentifierService
from app.services.video_clipper import VideoClipperService
from app.utils.file_manager import get_output_path

router = APIRouter(prefix="/shorts", tags=["Shorts"])


# In-memory storage for identified shorts (in production, use a database)
_shorts_cache: dict[str, list] = {}


@router.post(
    "/identify/{video_id}",
    response_model=ShortsIdentificationResponse,
    summary="Identify potential shorts",
    description="Analyze a video to identify the best segments for YouTube Shorts.",
)
async def identify_shorts(
    video_id: str,
    max_shorts: int = 5,
    shorts_service: ShortsIdentifierService = Depends(get_shorts_identifier),
) -> ShortsIdentificationResponse:
    """Identify potential shorts from an uploaded video."""
    video_path = validate_video_id(video_id)

    try:
        analysis = shorts_service.identify_shorts_from_video(
            video_path=video_path,
            max_shorts=max_shorts,
        )

        # Cache the shorts for later generation
        _shorts_cache[video_id] = analysis.shorts

        return ShortsIdentificationResponse(
            video_id=video_id,
            analysis=analysis,
            status="completed",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Shorts identification failed: {str(e)}",
        )


@router.post(
    "/generate/{video_id}",
    response_model=GenerateShortsResponse,
    summary="Generate short clips",
    description="Generate video clips for identified shorts.",
)
async def generate_shorts(
    video_id: str,
    short_indices: list[int] | None = None,
    clipper_service: VideoClipperService = Depends(get_clipper),
) -> GenerateShortsResponse:
    """Generate short video clips from identified segments."""
    video_path = validate_video_id(video_id)

    # Get cached shorts
    if video_id not in _shorts_cache:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No shorts identified for this video. Call /identify first.",
        )

    shorts = _shorts_cache[video_id]

    if not shorts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No shorts available to generate.",
        )

    try:
        generated = clipper_service.generate_shorts(
            video_path=video_path,
            shorts=shorts,
            video_id=video_id,
            indices=short_indices,
        )

        return GenerateShortsResponse(
            video_id=video_id,
            shorts=generated,
            status="completed",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Shorts generation failed: {str(e)}",
        )


@router.get(
    "/{short_id}",
    summary="Download a generated short",
    description="Download a generated short video file.",
)
async def download_short(short_id: str) -> FileResponse:
    """Download a generated short video."""
    short_path = get_output_path(short_id)

    if not short_path or not short_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Short not found: {short_id}",
        )

    return FileResponse(
        path=short_path,
        media_type="video/mp4",
        filename=f"{short_id}.mp4",
    )


@router.get(
    "/cache/{video_id}",
    summary="Get cached shorts for a video",
    description="Retrieve previously identified shorts for a video.",
)
async def get_cached_shorts(video_id: str):
    """Get cached shorts identification results."""
    if video_id not in _shorts_cache:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No cached shorts for this video.",
        )

    return {
        "video_id": video_id,
        "shorts_count": len(_shorts_cache[video_id]),
        "shorts": [s.model_dump() for s in _shorts_cache[video_id]],
    }
