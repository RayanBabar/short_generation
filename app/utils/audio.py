"""Audio extraction utilities using FFmpeg."""

import subprocess
from pathlib import Path
import tempfile

from app.utils.logging import get_logger

logger = get_logger(__name__)


def extract_audio(video_path: Path, output_path: Path | None = None) -> Path:
    """
    Extract audio from a video file.

    Args:
        video_path: Path to the video file
        output_path: Optional path for the output audio file.
                     If not provided, creates a temp file.

    Returns:
        Path to the extracted audio file
    """
    # Generate output path if not provided
    if output_path is None:
        output_path = video_path.with_suffix(".mp3")

    logger.info(f"🎵 Extracting audio from: {video_path.name}")

    try:
        # Extract audio using FFmpeg
        # -vn: no video
        # -acodec mp3: use MP3 codec
        # -ab 128k: bitrate 128kbps (good quality, small size)
        # -ar 44100: sample rate 44.1kHz
        result = subprocess.run(
            [
                "ffmpeg",
                "-i", str(video_path),
                "-vn",  # No video
                "-acodec", "libmp3lame",
                "-ab", "128k",
                "-ar", "44100",
                "-y",  # Overwrite output
                str(output_path),
            ],
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout
        )

        if result.returncode != 0:
            logger.error(f"FFmpeg error: {result.stderr}")
            raise RuntimeError(f"Audio extraction failed: {result.stderr}")

        # Get file sizes for comparison
        video_size = video_path.stat().st_size / (1024 * 1024)  # MB
        audio_size = output_path.stat().st_size / (1024 * 1024)  # MB
        reduction = (1 - audio_size / video_size) * 100

        logger.info(f"✅ Audio extracted: {audio_size:.1f}MB (reduced by {reduction:.0f}% from {video_size:.1f}MB)")

        return output_path

    except subprocess.TimeoutExpired:
        logger.error("Audio extraction timed out")
        raise RuntimeError("Audio extraction timed out")
    except FileNotFoundError:
        logger.error("FFmpeg not found")
        raise RuntimeError("FFmpeg is not installed")


def get_audio_path(video_path: Path) -> Path:
    """
    Get the expected audio path for a video file.

    Args:
        video_path: Path to the video file

    Returns:
        Path where the audio file would be stored
    """
    return video_path.with_suffix(".mp3")


def ensure_audio_exists(video_path: Path) -> Path:
    """
    Ensure audio file exists for a video, extracting if necessary.

    Args:
        video_path: Path to the video file

    Returns:
        Path to the audio file
    """
    audio_path = get_audio_path(video_path)

    if audio_path.exists():
        logger.debug(f"Audio already exists: {audio_path.name}")
        return audio_path

    return extract_audio(video_path, audio_path)
