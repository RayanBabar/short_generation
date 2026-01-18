"""Video clipping service using FFmpeg."""

import subprocess
from pathlib import Path

import ffmpeg

from app.config import get_settings
from app.schemas.shorts import PotentialShort, GeneratedShort
from app.utils.file_manager import generate_short_id
from app.utils.time_utils import parse_timestamp, format_timestamp_ffmpeg
from app.utils.logging import get_logger

logger = get_logger(__name__)


class VideoClipperService:
    """Service for clipping video segments using FFmpeg."""

    def __init__(self):
        """Initialize the video clipper service."""
        self.settings = get_settings()
        self._verify_ffmpeg()
        logger.info("VideoClipperService initialized")

    def _verify_ffmpeg(self) -> None:
        """Verify FFmpeg is installed and accessible."""
        try:
            result = subprocess.run(
                ["ffmpeg", "-version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode != 0:
                raise RuntimeError("FFmpeg not available")
            logger.debug("FFmpeg verified")
        except FileNotFoundError:
            logger.error("FFmpeg is not installed")
            raise RuntimeError(
                "FFmpeg is not installed. Please install FFmpeg to use video clipping."
            )

    def clip_video(
        self,
        video_path: Path,
        start_time: str,
        end_time: str,
        output_path: Path,
        use_copy: bool = False,
    ) -> Path:
        """
        Clip a segment from a video.

        Args:
            video_path: Path to the source video
            start_time: Start timestamp (MM:SS or HH:MM:SS)
            end_time: End timestamp (MM:SS or HH:MM:SS)
            output_path: Path for the output file
            use_copy: Use stream copy for faster processing (may be less accurate)

        Returns:
            Path to the clipped video
        """
        start_seconds = parse_timestamp(start_time)
        end_seconds = parse_timestamp(end_time)
        duration = end_seconds - start_seconds

        start_ffmpeg = format_timestamp_ffmpeg(start_seconds)
        
        logger.info(f"✂️ Clipping: {start_time} - {end_time} ({duration}s)")
        logger.debug(f"   Output: {output_path.name}")

        try:
            if use_copy:
                # Fast mode: use stream copy (no re-encoding)
                logger.debug("Using stream copy mode (fast)")
                (
                    ffmpeg
                    .input(str(video_path), ss=start_ffmpeg)
                    .output(
                        str(output_path),
                        t=duration,
                        c="copy",
                        avoid_negative_ts="make_zero",
                    )
                    .overwrite_output()
                    .run(capture_stdout=True, capture_stderr=True)
                )
            else:
                # Accurate mode: re-encode for frame-accurate cutting
                logger.debug("Using re-encode mode (accurate)")
                (
                    ffmpeg
                    .input(str(video_path))
                    .output(
                        str(output_path),
                        ss=start_ffmpeg,
                        t=duration,
                        vcodec="libx264",
                        acodec="aac",
                        preset="fast",
                        crf=23,
                    )
                    .overwrite_output()
                    .run(capture_stdout=True, capture_stderr=True)
                )

            logger.debug(f"✅ Clip created: {output_path.name}")
            return output_path

        except ffmpeg.Error as e:
            # If copy mode fails, retry with re-encoding
            if use_copy:
                logger.warning("Stream copy failed, retrying with re-encoding...")
                return self.clip_video(
                    video_path, start_time, end_time, output_path, use_copy=False
                )
            logger.error(f"FFmpeg error: {e.stderr.decode()}")
            raise RuntimeError(f"FFmpeg error: {e.stderr.decode()}")

    def clip_short(
        self,
        video_path: Path,
        short: PotentialShort,
        video_id: str,
        short_index: int,
    ) -> GeneratedShort:
        """
        Generate a short clip from a video.

        Args:
            video_path: Path to the source video
            short: PotentialShort with timing information
            video_id: ID of the source video
            short_index: Index of this short

        Returns:
            GeneratedShort with file information
        """
        self.settings.ensure_directories()

        # Generate unique short ID
        short_id = generate_short_id(video_id, short_index)

        # Determine output format
        output_path = self.settings.output_dir / f"{short_id}.mp4"

        logger.info(f"📹 Generating short {short_index + 1}: {short.title[:40]}...")

        # Clip the video
        self.clip_video(
            video_path=video_path,
            start_time=short.start_time,
            end_time=short.end_time,
            output_path=output_path,
        )

        return GeneratedShort(
            short_id=short_id,
            title=short.title,
            file_path=str(output_path),
            duration_seconds=short.duration_seconds,
            download_url=f"/api/v1/shorts/{short_id}",
        )

    def generate_shorts(
        self,
        video_path: Path,
        shorts: list[PotentialShort],
        video_id: str,
        indices: list[int] | None = None,
    ) -> list[GeneratedShort]:
        """
        Generate multiple short clips from a video.

        Args:
            video_path: Path to the source video
            shorts: List of potential shorts
            video_id: ID of the source video
            indices: Optional list of indices to generate (None = all)

        Returns:
            List of generated shorts
        """
        logger.info(f"🎬 Starting shorts generation for video: {video_id}")
        generated = []

        if indices is None:
            indices = list(range(len(shorts)))

        total = len(indices)
        logger.info(f"   Generating {total} shorts...")

        for i, short in enumerate(shorts):
            if i not in indices:
                continue

            try:
                logger.info(f"   [{i+1}/{total}] Processing...")
                generated_short = self.clip_short(
                    video_path=video_path,
                    short=short,
                    video_id=video_id,
                    short_index=i,
                )
                generated.append(generated_short)
                logger.info(f"   ✅ Short {i+1} complete")
            except Exception as e:
                logger.error(f"   ❌ Failed to generate short {i+1}: {e}")
                continue

        logger.info(f"✅ Shorts generation complete: {len(generated)}/{total} successful")
        return generated

    def get_video_duration(self, video_path: Path) -> float:
        """
        Get the duration of a video file.

        Args:
            video_path: Path to the video file

        Returns:
            Duration in seconds
        """
        try:
            probe = ffmpeg.probe(str(video_path))
            duration = float(probe["format"]["duration"])
            logger.debug(f"Video duration: {duration:.1f}s")
            return duration
        except (ffmpeg.Error, KeyError):
            logger.warning("Could not determine video duration")
            return 0.0


# Singleton instance
_video_clipper: VideoClipperService | None = None


def get_video_clipper_service() -> VideoClipperService:
    """Get or create the video clipper service instance."""
    global _video_clipper
    if _video_clipper is None:
        _video_clipper = VideoClipperService()
    return _video_clipper
