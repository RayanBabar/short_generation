"""Pydantic schemas for transcription data."""

from pydantic import BaseModel, Field


class TranscriptionSegment(BaseModel):
    """A single segment of transcribed content."""

    speaker: str = Field(description="Speaker identifier, e.g., 'Speaker 1'")
    start_time: str = Field(description="Start timestamp in MM:SS format")
    end_time: str = Field(description="End timestamp in MM:SS format")
    content: str = Field(description="Transcribed text content")
    language: str = Field(description="Detected language of the segment")
    language_code: str = Field(default="en", description="ISO language code")
    emotion: str = Field(
        description="Primary emotion: happy, sad, angry, or neutral"
    )


class Transcription(BaseModel):
    """Complete transcription of a video."""

    summary: str = Field(description="Brief summary of the video content")
    segments: list[TranscriptionSegment] = Field(
        description="List of transcribed segments"
    )
    total_duration: str = Field(
        default="00:00", description="Total video duration in MM:SS format"
    )


class TranscriptionRequest(BaseModel):
    """Request model for transcription endpoint."""

    video_id: str = Field(description="ID of the uploaded video")


class TranscriptionResponse(BaseModel):
    """Response model for transcription endpoint."""

    video_id: str
    transcription: Transcription
    status: str = "completed"
