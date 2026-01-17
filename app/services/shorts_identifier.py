"""AI-powered shorts identification service."""

import json
from pathlib import Path

from google.genai import types

from app.config import get_settings
from app.services.gemini_client import get_gemini_client
from app.services.context_optimizer import optimize_segment_starts
from app.schemas.transcription import Transcription
from app.schemas.shorts import ShortsAnalysis, PotentialShort
from app.utils.time_utils import parse_timestamp, calculate_duration
from app.utils.audio import ensure_audio_exists
from app.utils.logging import get_logger

logger = get_logger(__name__)


# Schema for structured shorts identification output
SHORTS_SCHEMA = types.Schema(
    type=types.Type.OBJECT,
    properties={
        "video_summary": types.Schema(
            type=types.Type.STRING,
            description="Brief summary of the source content.",
        ),
        "shorts": types.Schema(
            type=types.Type.ARRAY,
            description="List of potential YouTube Shorts segments.",
            items=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "title": types.Schema(
                        type=types.Type.STRING,
                        description="Catchy, engaging title for the short (max 100 chars).",
                    ),
                    "start_time": types.Schema(
                        type=types.Type.STRING,
                        description="Start timestamp in HH:MM:SS format (e.g., 00:01:30).",
                    ),
                    "end_time": types.Schema(
                        type=types.Type.STRING,
                        description="End timestamp in HH:MM:SS format (e.g., 00:02:15).",
                    ),
                    "hook": types.Schema(
                        type=types.Type.STRING,
                        description="Description of the opening hook (first 3 seconds).",
                    ),
                    "content_summary": types.Schema(
                        type=types.Type.STRING,
                        description="Brief description of what happens in this segment.",
                    ),
                    "virality_score": types.Schema(
                        type=types.Type.NUMBER,
                        description="Virality potential score from 0 to 100.",
                    ),
                    "virality_reasons": types.Schema(
                        type=types.Type.ARRAY,
                        description="List of reasons why this could go viral.",
                        items=types.Schema(type=types.Type.STRING),
                    ),
                },
                required=[
                    "title",
                    "start_time",
                    "end_time",
                    "hook",
                    "content_summary",
                    "virality_score",
                    "virality_reasons",
                ],
            ),
        ),
    },
    required=["video_summary", "shorts"],
)


def get_shorts_identification_prompt(
    min_duration: int,
    max_duration: int,
    max_shorts: int,
) -> str:
    """Generate the prompt for shorts identification."""
    return f"""
Analyze this audio content and identify the best segments for YouTube Shorts.

## YouTube Shorts Requirements:
- Duration: {min_duration}-{max_duration} seconds (strictly enforced)
- Must have a strong opening hook in the first 3 seconds
- **MUST be completely self-contained with proper context**

## CRITICAL - Context Requirements:
Each short MUST:
- **Start with enough context** so viewers immediately understand the topic
- **Include the setup/premise** before any punchline or conclusion
- **Make complete sense on its own** without any prior knowledge of the video
- **NOT start mid-sentence or mid-thought**
- **NOT assume the viewer knows what was discussed before**
- **Have a clear beginning, middle, and end**

BAD examples (avoid these):
- Starting with "So as I was saying..." (no context)
- Starting with "This is why..." without explaining what "this" refers to
- Clips that reference something shown/said earlier in the video

GOOD examples (aim for these):
- Clips that introduce a topic, explain it, and conclude
- Self-explanatory statements with full context built-in
- Complete stories or thoughts from start to finish

## Strong Hooks (Critical):
- Provocative questions or bold statements
- Surprising facts or revelations
- Emotional moments (laughter, surprise, intensity)
- Dramatic or impactful statements that stand alone

## Content Quality:
- Complete thoughts or mini-stories with clear narrative arc
- Actionable tips or valuable insights with context
- Entertaining moments with setup AND payoff
- Quotable or shareable statements that need no explanation

## Virality Factors:
- Emotional resonance (makes viewers feel something)
- Relatability (viewers can connect personally)
- Shareability (content worth sharing - must make sense when shared!)
- Curiosity gap (makes viewers want to know more)

## Instructions:

1. Identify up to {max_shorts} potential shorts from the audio
2. Each short must be between {min_duration} and {max_duration} seconds
3. **Extend start time earlier if needed to capture context setup**
4. Provide PRECISE timestamps in HH:MM:SS format
5. Score each segment 0-100 based on viral potential
6. Rank shorts by virality_score (highest first)

## IMPORTANT:
- Timestamps must be accurate to the actual audio timing
- Ensure segments don't overlap
- **Prioritize context and comprehensibility over hook strength**
- Each short should be understandable by someone who hasn't seen the rest of the video
"""


class ShortsIdentifierService:
    """Service for identifying potential YouTube Shorts from videos."""

    def __init__(self):
        """Initialize the shorts identifier service."""
        self.client = get_gemini_client()
        self.settings = get_settings()
        logger.info("ShortsIdentifierService initialized")

    def identify_shorts_from_video(
        self,
        video_path: Path,
        max_shorts: int | None = None,
    ) -> ShortsAnalysis:
        """
        Identify potential shorts from a video file by analyzing its audio.

        Args:
            video_path: Path to the video file
            max_shorts: Maximum number of shorts to identify

        Returns:
            ShortsAnalysis with ranked potential shorts
        """
        max_shorts = max_shorts or self.settings.max_shorts_to_generate
        logger.info(f"🔍 Starting shorts identification for: {video_path.name}")
        logger.info(f"   Settings: max_shorts={max_shorts}, duration={self.settings.min_short_duration}-{self.settings.max_short_duration}s")

        # Extract audio from video (much smaller file = faster upload)
        logger.info("Step 1/4: Extracting audio from video...")
        audio_path = ensure_audio_exists(video_path)

        # Upload audio to Gemini
        logger.info("Step 2/4: Uploading audio to Gemini...")
        uploaded_file = self.client.upload_audio(audio_path)

        try:
            logger.info("Step 3/4: Analyzing audio for viral segments...")
            prompt = get_shorts_identification_prompt(
                min_duration=self.settings.min_short_duration,
                max_duration=self.settings.max_short_duration,
                max_shorts=max_shorts,
            )

            response = self.client.generate_content(
                prompt=prompt,
                file=uploaded_file,
                response_schema=SHORTS_SCHEMA,
                use_video_metadata=False,  # Audio doesn't need video metadata
            )

            logger.info("Step 4/5: Parsing and validating shorts...")
            data = json.loads(response)
            analysis = self._parse_shorts_analysis(data)
            
            # Step 5: Optimize start times to find sentence breaks
            # Reuse the already-uploaded audio file (no re-upload needed)
            if analysis.shorts:
                logger.info("Step 5/5: Optimizing start times for context...")
                segments = [
                    {"start_time": s.start_time, "end_time": s.end_time}
                    for s in analysis.shorts
                ]
                optimized = optimize_segment_starts(segments, uploaded_file)
                
                # Apply optimized start times back to shorts
                for short, opt_seg in zip(analysis.shorts, optimized):
                    if short.start_time != opt_seg["start_time"]:
                        short.start_time = opt_seg["start_time"]
                        short.duration_seconds = opt_seg.get(
                            "duration_seconds", 
                            calculate_duration(opt_seg["start_time"], short.end_time)
                        )
            
            logger.info(f"✅ Shorts identification complete: {len(analysis.shorts)} shorts found")
            for i, short in enumerate(analysis.shorts):
                logger.info(f"   [{i+1}] {short.start_time} - {short.end_time} | Score: {short.virality_score} | {short.title[:50]}...")
            
            return analysis

        finally:
            logger.debug("Cleaning up uploaded file...")
            self.client.delete_file(uploaded_file)

    def identify_shorts_from_transcription(
        self,
        transcription: Transcription,
        video_path: Path | None = None,
        max_shorts: int | None = None,
    ) -> ShortsAnalysis:
        """
        Identify potential shorts from a transcription.

        This method uses the transcription text to identify shorts,
        optionally cross-referencing with the original video's audio.

        Args:
            transcription: Transcription object
            video_path: Optional path to the original video
            max_shorts: Maximum number of shorts to identify

        Returns:
            ShortsAnalysis with ranked potential shorts
        """
        max_shorts = max_shorts or self.settings.max_shorts_to_generate
        logger.info(f"🔍 Identifying shorts from transcription ({len(transcription.segments)} segments)")

        # Format transcription for the prompt
        transcription_text = self._format_transcription(transcription)

        prompt = f"""
{get_shorts_identification_prompt(
    min_duration=self.settings.min_short_duration,
    max_duration=self.settings.max_short_duration,
    max_shorts=max_shorts,
)}

## Audio Transcription:

{transcription_text}
"""

        if video_path:
            # Use audio for context
            logger.info("Using audio file for context...")
            audio_path = ensure_audio_exists(video_path)
            uploaded_file = self.client.upload_audio(audio_path)
            try:
                response = self.client.generate_content(
                    prompt=prompt,
                    file=uploaded_file,
                    response_schema=SHORTS_SCHEMA,
                    use_video_metadata=False,
                )
            finally:
                self.client.delete_file(uploaded_file)
        else:
            # Text-only analysis
            logger.info("Using text-only analysis (no audio context)")
            response = self.client.generate_content(
                prompt=prompt,
                response_schema=SHORTS_SCHEMA,
            )

        data = json.loads(response)
        return self._parse_shorts_analysis(data)

    def _format_transcription(self, transcription: Transcription) -> str:
        """Format transcription for prompt inclusion."""
        lines = [f"Summary: {transcription.summary}", ""]

        for seg in transcription.segments:
            lines.append(
                f"[{seg.start_time} - {seg.end_time}] {seg.speaker}: {seg.content}"
            )

        return "\n".join(lines)

    def _parse_shorts_analysis(self, data: dict) -> ShortsAnalysis:
        """Parse raw data into ShortsAnalysis model."""
        shorts = []
        skipped = 0

        for short_data in data.get("shorts", []):
            try:
                start_time = short_data.get("start_time", "00:00:00")
                end_time = short_data.get("end_time", "00:00:00")
                duration = calculate_duration(start_time, end_time)

                # Validate duration
                if duration < self.settings.min_short_duration:
                    logger.debug(f"Skipping short: duration {duration}s < min {self.settings.min_short_duration}s")
                    skipped += 1
                    continue
                if duration > self.settings.max_short_duration:
                    logger.debug(f"Skipping short: duration {duration}s > max {self.settings.max_short_duration}s")
                    skipped += 1
                    continue

                shorts.append(
                    PotentialShort(
                        title=short_data.get("title", "Untitled Short"),
                        start_time=start_time,
                        end_time=end_time,
                        duration_seconds=duration,
                        hook=short_data.get("hook", ""),
                        content_summary=short_data.get("content_summary", ""),
                        virality_score=float(short_data.get("virality_score", 0)),
                        virality_reasons=short_data.get("virality_reasons", []),
                    )
                )
            except (ValueError, KeyError) as e:
                logger.warning(f"Failed to parse short: {e}")
                skipped += 1
                continue

        if skipped > 0:
            logger.info(f"   Skipped {skipped} shorts due to validation")

        # Sort by virality score (highest first)
        shorts.sort(key=lambda x: x.virality_score, reverse=True)

        return ShortsAnalysis(
            video_summary=data.get("video_summary", ""),
            total_shorts_found=len(shorts),
            shorts=shorts,
        )


# Singleton instance
_shorts_identifier: ShortsIdentifierService | None = None


def get_shorts_identifier_service() -> ShortsIdentifierService:
    """Get or create the shorts identifier service instance."""
    global _shorts_identifier
    if _shorts_identifier is None:
        _shorts_identifier = ShortsIdentifierService()
    return _shorts_identifier
