"""Pydantic schemas for shorts identification."""

from pydantic import BaseModel, Field


class PotentialShort(BaseModel):
    """A potential YouTube Short identified from the video."""

    title: str = Field(description="Suggested title for the short")
    start_time: str = Field(description="Start timestamp in MM:SS format")
    end_time: str = Field(description="End timestamp in MM:SS format")
    duration_seconds: int = Field(description="Duration in seconds")
    hook: str = Field(description="Opening hook description (first 3 seconds)")
    content_summary: str = Field(description="Brief summary of what happens")
    virality_score: float = Field(
        ge=0, le=100, description="Virality potential score (0-100)"
    )
    virality_reasons: list[str] = Field(
        description="Reasons why this could go viral"
    )


class ShortsAnalysis(BaseModel):
    """Analysis result containing all potential shorts."""

    video_summary: str = Field(description="Summary of the source video")
    total_shorts_found: int = Field(description="Number of potential shorts found")
    shorts: list[PotentialShort] = Field(description="List of potential shorts")


class ShortsIdentificationRequest(BaseModel):
    """Request model for shorts identification."""

    video_id: str = Field(description="ID of the video to analyze")
    max_shorts: int = Field(
        default=5, ge=1, le=20, description="Maximum number of shorts to identify"
    )


class ShortsIdentificationResponse(BaseModel):
    """Response model for shorts identification."""

    video_id: str
    analysis: ShortsAnalysis
    status: str = "completed"


class GenerateShortsRequest(BaseModel):
    """Request model for generating shorts."""

    video_id: str = Field(description="ID of the source video")
    short_indices: list[int] | None = Field(
        default=None,
        description="Indices of shorts to generate (None = generate all)",
    )


class GeneratedShort(BaseModel):
    """Information about a generated short video."""

    short_id: str = Field(description="Unique ID of the generated short")
    title: str = Field(description="Title of the short")
    file_path: str = Field(description="Path to the generated video file")
    duration_seconds: int = Field(description="Duration in seconds")
    download_url: str = Field(description="URL to download the short")


class GenerateShortsResponse(BaseModel):
    """Response model for generated shorts."""

    video_id: str
    shorts: list[GeneratedShort]
    status: str = "completed"
