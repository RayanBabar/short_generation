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
