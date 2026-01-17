"""Gemini API client wrapper for video processing."""

import time
from pathlib import Path
from typing import Any

from google import genai
from google.genai import types

from app.config import get_settings
from app.utils.logging import get_logger

logger = get_logger(__name__)


class GeminiClient:
    """Client for interacting with the Gemini API."""

    def __init__(self):
        """Initialize the Gemini client."""
        settings = get_settings()
        self.client = genai.Client(api_key=settings.gemini_api_key)
        self.model = settings.gemini_model
        self.video_fps = settings.video_fps
        logger.info(f"Initialized Gemini client with model: {self.model}, FPS: {self.video_fps}")

    def upload_file(self, file_path: Path) -> types.File:
        """
        Upload a file (video or audio) to Gemini File API.

        Args:
            file_path: Path to the file

        Returns:
            Uploaded file object
        """
        logger.info(f"📤 Uploading file: {file_path.name}")
        
        # Determine MIME type based on extension
        extension = file_path.suffix.lower()
        mime_types = {
            # Video types
            ".mp4": "video/mp4",
            ".mov": "video/quicktime",
            ".avi": "video/x-msvideo",
            ".mkv": "video/x-matroska",
            ".webm": "video/webm",
            # Audio types
            ".mp3": "audio/mpeg",
            ".wav": "audio/wav",
            ".m4a": "audio/mp4",
            ".aac": "audio/aac",
            ".ogg": "audio/ogg",
            ".flac": "audio/flac",
        }
        mime_type = mime_types.get(extension, "application/octet-stream")
        logger.debug(f"MIME type: {mime_type}")

        # Get file size for logging
        file_size = file_path.stat().st_size / (1024 * 1024)  # MB
        logger.info(f"   File size: {file_size:.1f}MB")

        # Upload file
        start_time = time.time()
        uploaded_file = self.client.files.upload(
            file=file_path,
            config=types.UploadFileConfig(mime_type=mime_type),
        )
        logger.info(f"📤 Upload started, waiting for processing...")

        # Wait for file to be processed
        while uploaded_file.state == "PROCESSING":
            time.sleep(2)
            uploaded_file = self.client.files.get(name=uploaded_file.name)
            logger.debug(f"Processing state: {uploaded_file.state}")

        elapsed = time.time() - start_time
        
        if uploaded_file.state == "FAILED":
            logger.error(f"❌ File processing failed: {uploaded_file.name}")
            raise RuntimeError(f"File processing failed: {uploaded_file.name}")

        logger.info(f"✅ File uploaded successfully in {elapsed:.1f}s")
        return uploaded_file

    def upload_video(self, video_path: Path) -> types.File:
        """
        Upload a video file to Gemini File API.
        
        This is an alias for upload_file for backward compatibility.
        """
        return self.upload_file(video_path)

    def upload_audio(self, audio_path: Path) -> types.File:
        """
        Upload an audio file to Gemini File API.
        
        This is an alias for upload_file for clarity.
        """
        return self.upload_file(audio_path)

    def generate_content(
        self,
        prompt: str,
        file: types.File | None = None,
        response_schema: dict[str, Any] | None = None,
        use_video_metadata: bool = False,
    ) -> str:
        """
        Generate content using Gemini model.

        Args:
            prompt: Text prompt
            file: Optional uploaded file (video or audio)
            response_schema: Optional JSON schema for structured output
            use_video_metadata: Whether to use video metadata (FPS) for video files

        Returns:
            Generated content as string
        """
        logger.info(f"🤖 Generating content with {self.model}...")
        start_time = time.time()
        
        parts = []

        # Add file
        if file:
            if use_video_metadata:
                logger.debug(f"Adding video file with {self.video_fps} FPS sampling")
                parts.append(
                    types.Part(
                        file_data=types.FileData(file_uri=file.uri),
                        video_metadata=types.VideoMetadata(fps=self.video_fps),
                    )
                )
            else:
                logger.debug("Adding file without video metadata")
                parts.append(
                    types.Part(file_data=types.FileData(file_uri=file.uri))
                )

        # Add prompt
        parts.append(types.Part(text=prompt))

        # Configure response
        config = None
        if response_schema:
            logger.debug("Using structured JSON output")
            config = types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=response_schema,
            )

        # Generate content
        response = self.client.models.generate_content(
            model=self.model,
            contents=[types.Content(parts=parts)],
            config=config,
        )

        elapsed = time.time() - start_time
        logger.info(f"✅ Content generated in {elapsed:.1f}s")
        
        return response.text

    def delete_file(self, file: types.File) -> None:
        """
        Delete an uploaded file from Gemini.

        Args:
            file: File object to delete
        """
        try:
            self.client.files.delete(name=file.name)
            logger.debug(f"🗑️ Deleted file: {file.name}")
        except Exception as e:
            logger.warning(f"Failed to delete file: {e}")


# Singleton instance
_gemini_client: GeminiClient | None = None


def get_gemini_client() -> GeminiClient:
    """Get or create the Gemini client instance."""
    global _gemini_client
    if _gemini_client is None:
        _gemini_client = GeminiClient()
    return _gemini_client
