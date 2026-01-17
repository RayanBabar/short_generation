"""Common API response schemas."""

from pydantic import BaseModel, Field


class VideoUploadResponse(BaseModel):
    """Response model for video upload."""

    video_id: str = Field(description="Unique identifier for the uploaded video")
    filename: str = Field(description="Original filename")
    file_size: int = Field(description="File size in bytes")
    duration: str | None = Field(
        default=None, description="Video duration if available"
    )
    status: str = "uploaded"


class ErrorResponse(BaseModel):
    """Standard error response."""

    error: str = Field(description="Error message")
    detail: str | None = Field(default=None, description="Detailed error info")


class ProcessVideoRequest(BaseModel):
    """Request for full video processing pipeline."""

    video_id: str | None = Field(
        default=None, description="ID of previously uploaded video"
    )
    youtube_url: str | None = Field(
        default=None, description="YouTube URL to process directly"
    )
    max_shorts: int = Field(
        default=5, ge=1, le=20, description="Maximum shorts to generate"
    )
    generate_clips: bool = Field(
        default=True, description="Whether to generate video clips"
    )


class ProcessVideoResponse(BaseModel):
    """Response for full video processing pipeline."""

    video_id: str
    transcription_summary: str
    shorts_found: int
    shorts_generated: int
    download_urls: list[str]
    status: str = "completed"
