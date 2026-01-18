"""AI-powered shorts identification service with Precision Timestamping."""

import json
from pathlib import Path
from typing import List, Dict, Any

from google.genai import types

from app.config import get_settings
from app.services.gemini_client import get_gemini_client
from app.services.transcription_precision import get_precision_transcriber
from app.schemas.shorts import ShortsAnalysis, PotentialShort
from app.utils.time_utils import format_timestamp_ffmpeg
from app.utils.logging import get_logger

logger = get_logger(__name__)


# Schema for structured shorts identification output
# Note: We now ask for QUOTES (start/end text) instead of timestamps
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
                        description="Catchy, engaging title for the short.",
                    ),
                    "start_text": types.Schema(
                        type=types.Type.STRING,
                        description="The EXACT first 5-10 words of the segment from the transcript.",
                    ),
                    "end_text": types.Schema(
                        type=types.Type.STRING,
                        description="The EXACT last 5-10 words of the segment from the transcript.",
                    ),
                    "hook": types.Schema(
                        type=types.Type.STRING,
                        description="Description of the opening hook.",
                    ),
                    "content_summary": types.Schema(
                        type=types.Type.STRING,
                        description="Brief description of content.",
                    ),
                    "virality_score": types.Schema(
                        type=types.Type.NUMBER,
                        description="Virality potential score from 0 to 100.",
                    ),
                    "virality_reasons": types.Schema(
                        type=types.Type.ARRAY,
                        description="List of reasons for virality.",
                        items=types.Schema(type=types.Type.STRING),
                    ),
                },
                required=[
                    "title",
                    "start_text",
                    "end_text",
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


class ShortsIdentifierService:
    """Service for identifying potential YouTube Shorts with acoustic precision."""

    def __init__(self):
        """Initialize the shorts identifier service."""
        self.client = get_gemini_client()
        self.settings = get_settings()
        self.transcriber = get_precision_transcriber()
        logger.info("ShortsIdentifierService (Precision) initialized")

    def _normalize_text(self, text: str) -> str:
        """Normalize text for comparison: lowercase, remove extra spaces."""
        return " ".join(text.lower().split())

    def _find_best_match_position(self, target_text: str, words: List[Dict]) -> tuple[int, float]:
        """
        Find the best matching position for target_text in the word list.
        Uses sliding window with fuzzy matching for robustness.
        
        Returns:
            Tuple of (best_start_index, confidence_score)
        """
        from difflib import SequenceMatcher
        
        target_normalized = self._normalize_text(target_text)
        target_word_count = len(target_text.split())
        
        # Sliding window size: target words + buffer for slight variations
        window_size = target_word_count + 3
        
        best_score = 0.0
        best_index = 0
        
        for i in range(max(1, len(words) - window_size + 1)):
            # Build window text from word list
            window_words = words[i:i + window_size]
            window_text = " ".join(w["word"] for w in window_words)
            window_normalized = self._normalize_text(window_text)
            
            # Calculate similarity score
            score = SequenceMatcher(None, target_normalized, window_normalized).ratio()
            
            if score > best_score:
                best_score = score
                best_index = i
                
            # Early exit on near-perfect match
            if score > 0.95:
                break
        
        return best_index, best_score

    def _find_timestamps_for_segment(
        self, 
        start_text: str, 
        end_text: str, 
        words: List[Dict]
    ) -> tuple[float, float, bool]:
        """
        Find precise start and end timestamps for a segment.
        
        Args:
            start_text: First 5-10 words of the segment
            end_text: Last 5-10 words of the segment
            words: Complete word list from Whisper
            
        Returns:
            Tuple of (start_time, end_time, success)
        """
        # Find START position
        start_idx, start_confidence = self._find_best_match_position(start_text, words)
        
        # Find END position - search from middle of transcript onwards for efficiency
        # But we must search the full list to find the actual end
        end_idx, end_confidence = self._find_best_match_position(end_text, words)
        
        # The end_idx is where the end text STARTS, but we need where it ENDS
        end_word_count = len(end_text.split())
        actual_end_idx = min(end_idx + end_word_count - 1, len(words) - 1)
        
        # Validate: end must come after start
        if actual_end_idx <= start_idx:
            logger.warning(f"⚠️ Invalid segment: end ({actual_end_idx}) <= start ({start_idx})")
            return 0.0, 0.0, False
        
        # Confidence check
        min_confidence = 0.6
        if start_confidence < min_confidence or end_confidence < min_confidence:
            logger.warning(
                f"⚠️ Low confidence match: start={start_confidence:.2f}, end={end_confidence:.2f}"
            )
            return 0.0, 0.0, False
        
        # Extract precise timestamps
        start_time = words[start_idx]["start"]
        end_time = words[actual_end_idx]["end"]
        
        logger.debug(
            f"   Match found: idx {start_idx}->{actual_end_idx}, "
            f"confidence: {start_confidence:.2f}/{end_confidence:.2f}"
        )
        
        return start_time, end_time, True

    async def identify_shorts_from_video(
        self,
        video_path: Path,
        max_shorts: int | None = None,
        min_duration: int | None = None,
        max_duration: int | None = None,
    ) -> ShortsAnalysis:
        """
        Identify shorts using Hybrid Precision Architecture.
        1. Whisper -> Exact timestamps & text
        2. Gemini -> Select viral text segments
        3. Match -> Deterministic timestamp lookup
        
        Args:
            video_path: Path to the video file
            max_shorts: Maximum shorts to find (None = use settings default, or find all if 0)
            min_duration: Minimum duration in seconds (None = use settings)
            max_duration: Maximum duration in seconds (None = use settings)
        """
        # Apply defaults from settings
        effective_max = max_shorts if max_shorts is not None else self.settings.max_shorts_to_generate
        effective_min_dur = min_duration if min_duration is not None else self.settings.min_short_duration
        effective_max_dur = max_duration if max_duration is not None else self.settings.max_short_duration
        
        # If max_shorts is 0 or None after settings, find "all" potential shorts
        shorts_instruction = f"the {effective_max} best" if effective_max and effective_max > 0 else "ALL potential"
        
        # Step 1: Precision Transcription
        logger.info("Step 1/3: Generating precision transcript with Faster-Whisper...")
        transcript_data = await self.transcriber.transcribe(video_path)
        full_text = transcript_data["text"]
        words = transcript_data["words"]
        
        # Step 2: Semantic Analysis with Gemini
        logger.info("Step 2/3: Analyzing text for viral segments...")
        
        prompt = f"""
        Analyze the following transcript and identify {shorts_instruction} segments for YouTube Shorts.

        ## Transcript:
        {full_text}

        ## CRITICAL RULES FOR PERFECT CUTS:
        
        1. **Duration**: Each segment MUST be {effective_min_dur}-{effective_max_dur} seconds.
        
        2. **START TEXT REQUIREMENTS**:
           - MUST begin at the START of a complete sentence
           - Look for capital letters after periods, question marks, or natural speech breaks
           - NEVER start mid-sentence or mid-thought
           - Copy the EXACT first 8-12 words into 'start_text'
           
        3. **END TEXT REQUIREMENTS**:
           - MUST end at the END of a complete sentence or thought
           - Look for periods, question marks, or natural conclusion points
           - NEVER cut off mid-sentence
           - Copy the EXACT last 8-12 words into 'end_text'
        
        4. **EXAMPLES OF GOOD vs BAD**:
           ❌ BAD start: "...is gonna destroy everything and that's why"
           ✅ GOOD start: "The reason this matters is because they want to control"
           
           ❌ BAD end: "and they ultimately just want to control over you and..."  
           ✅ GOOD end: "That is exactly why we need to fight back."
        
        5. **HOOK**: The segment should start with an attention-grabbing statement.
        
        6. **COMPLETE CONTEXT**: Viewer should understand the point without needing prior context.
        """
        
        response = self.client.generate_content(
            prompt=prompt,
            response_schema=SHORTS_SCHEMA,
        )
        
        # Step 3: Deterministic Timestamp Matching
        logger.info("Step 3/3: Aligning segments to acoustic boundaries...")
        data = json.loads(response)
        shorts = []
        
        for item in data.get("shorts", []):
            try:
                # Find exact times using robust fuzzy matching
                start_time, end_time, success = self._find_timestamps_for_segment(
                    start_text=item["start_text"],
                    end_text=item["end_text"],
                    words=words
                )
                
                if not success:
                    logger.warning(f"⚠️ Skipping short '{item['title'][:30]}...' - matching failed")
                    continue
                
                # Check duration constraints
                duration = end_time - start_time
                if duration < effective_min_dur or duration > effective_max_dur:
                    logger.warning(f"⚠️ Short duration {duration:.1f}s out of bounds ({effective_min_dur}-{effective_max_dur}s), skipping.")
                    continue
                
                # Create short with precise HH:MM:SS.mmm timestamps
                shorts.append(PotentialShort(
                    title=item["title"],
                    start_time=format_timestamp_ffmpeg(float(start_time)),
                    end_time=format_timestamp_ffmpeg(float(end_time)),
                    duration_seconds=round(float(duration)),
                    hook=item["hook"],
                    content_summary=item["content_summary"],
                    virality_score=float(item["virality_score"]),
                    virality_reasons=item["virality_reasons"]
                ))
                logger.info(f"   ✅ Matched: {format_timestamp_ffmpeg(start_time)} -> {format_timestamp_ffmpeg(end_time)} ({duration:.2f}s)")
                
            except Exception as e:
                logger.error(f"Error matching short: {e}")
                continue

        return ShortsAnalysis(
            video_summary=data.get("video_summary", ""),
            total_shorts_found=len(shorts),
            shorts=shorts
        )

# Singleton instance
_shorts_identifier: ShortsIdentifierService | None = None

def get_shorts_identifier_service() -> ShortsIdentifierService:
    global _shorts_identifier
    if _shorts_identifier is None:
        _shorts_identifier = ShortsIdentifierService()
    return _shorts_identifier
