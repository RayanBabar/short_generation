"""Video transcription service using Gemini API."""

import json
from pathlib import Path

from google.genai import types

from app.services.gemini_client import get_gemini_client
from app.schemas.transcription import Transcription, TranscriptionSegment
from app.utils.audio import ensure_audio_exists
from app.utils.logging import get_logger

logger = get_logger(__name__)


# Schema for structured transcription output
TRANSCRIPTION_SCHEMA = types.Schema(
    type=types.Type.OBJECT,
    properties={
        "summary": types.Schema(
            type=types.Type.STRING,
            description="A concise summary of the video/audio content.",
        ),
        "total_duration": types.Schema(
            type=types.Type.STRING,
            description="Total duration of the content in HH:MM:SS format.",
        ),
        "segments": types.Schema(
            type=types.Type.ARRAY,
            description="List of transcribed segments with speaker and timestamps.",
            items=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "speaker": types.Schema(
                        type=types.Type.STRING,
                        description="Speaker identifier (e.g., 'Speaker 1', 'Host', 'Guest').",
                    ),
                    "start_time": types.Schema(
                        type=types.Type.STRING,
                        description="Start timestamp in HH:MM:SS format.",
                    ),
                    "end_time": types.Schema(
                        type=types.Type.STRING,
                        description="End timestamp in HH:MM:SS format.",
                    ),
                    "content": types.Schema(
                        type=types.Type.STRING,
                        description="The transcribed text content.",
                    ),
                    "language": types.Schema(
                        type=types.Type.STRING,
                        description="Detected language name (e.g., 'English').",
                    ),
                    "language_code": types.Schema(
                        type=types.Type.STRING,
                        description="ISO language code (e.g., 'en').",
                    ),
                    "emotion": types.Schema(
                        type=types.Type.STRING,
                        enum=["happy", "sad", "angry", "neutral", "excited", "surprised"],
                        description="Primary emotion detected in the speech.",
                    ),
                },
                required=[
                    "speaker",
                    "start_time",
                    "end_time",
                    "content",
                    "language",
                    "language_code",
                    "emotion",
                ],
            ),
        ),
    },
    required=["summary", "total_duration", "segments"],
)


TRANSCRIPTION_PROMPT = """
Analyze and transcribe this audio with detailed accuracy. Follow these requirements:

1. **Speaker Identification**: Identify distinct speakers and label them consistently 
   (e.g., "Speaker 1", "Speaker 2", or use context clues like "Host", "Guest", "Interviewer").

2. **Precise Timestamps**: Provide PRECISE start and end timestamps for each speech segment.
   - Use HH:MM:SS format (e.g., "00:01:30" for 1 minute 30 seconds)
   - Be as accurate as possible to the exact second when speech starts and ends
   - Each segment should be between 5-30 seconds for natural grouping
   - Timestamps must accurately match the audio's actual timing

3. **Content Transcription**: Transcribe the speech accurately, including:
   - Important pauses or emphasis
   - Key phrases and statements
   - Any significant audio cues

4. **Language Detection**: Detect the primary language of each segment.

5. **Emotion Detection**: Identify the primary emotion conveyed:
   - happy, sad, angry, neutral, excited, or surprised

6. **Summary**: Provide a brief summary (2-3 sentences) of the entire content.

7. **Total Duration**: Provide the total audio duration in HH:MM:SS format.

Focus on creating segments that represent natural speech units - complete thoughts or 
sentences rather than arbitrary time divisions.
"""


class TranscriptionService:
    """Service for transcribing videos using Gemini API."""

    def __init__(self):
        """Initialize the transcription service."""
        self.client = get_gemini_client()
        logger.info("TranscriptionService initialized")

    def transcribe_video(self, video_path: Path) -> Transcription:
        """
        Transcribe a video file by extracting and analyzing its audio.

        Args:
            video_path: Path to the video file

        Returns:
            Transcription object with segments
        """
        logger.info(f"🎙️ Starting transcription for: {video_path.name}")
        
        # Extract audio from video (much smaller file = faster upload)
        logger.info("Step 1/4: Extracting audio from video...")
        audio_path = ensure_audio_exists(video_path)

        # Upload audio to Gemini
        logger.info("Step 2/4: Uploading audio to Gemini...")
        uploaded_file = self.client.upload_audio(audio_path)

        try:
            # Generate transcription
            logger.info("Step 3/4: Generating transcription with speaker diarization...")
            response = self.client.generate_content(
                prompt=TRANSCRIPTION_PROMPT,
                file=uploaded_file,
                response_schema=TRANSCRIPTION_SCHEMA,
                use_video_metadata=False,  # Audio doesn't need video metadata
            )

            # Parse response
            logger.info("Step 4/4: Parsing transcription response...")
            data = json.loads(response)
            transcription = self._parse_transcription(data)
            
            logger.info(f"✅ Transcription complete: {len(transcription.segments)} segments found")
            logger.info(f"   Duration: {transcription.total_duration}")
            
            return transcription

        finally:
            # Clean up uploaded file
            logger.debug("Cleaning up uploaded file...")
            self.client.delete_file(uploaded_file)

    def _parse_transcription(self, data: dict) -> Transcription:
        """Parse raw transcription data into Transcription model."""
        segments = [
            TranscriptionSegment(
                speaker=seg.get("speaker", "Unknown"),
                start_time=seg.get("start_time", "00:00:00"),
                end_time=seg.get("end_time", "00:00:00"),
                content=seg.get("content", ""),
                language=seg.get("language", "English"),
                language_code=seg.get("language_code", "en"),
                emotion=seg.get("emotion", "neutral"),
            )
            for seg in data.get("segments", [])
        ]

        return Transcription(
            summary=data.get("summary", ""),
            total_duration=data.get("total_duration", "00:00:00"),
            segments=segments,
        )


# Singleton instance
_transcription_service: TranscriptionService | None = None


def get_transcription_service() -> TranscriptionService:
    """Get or create the transcription service instance."""
    global _transcription_service
    if _transcription_service is None:
        _transcription_service = TranscriptionService()
    return _transcription_service
