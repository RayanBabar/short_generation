"""Context optimization using Gemini to find optimal start points."""

import json
from pathlib import Path

from google.genai import types

from app.services.gemini_client import get_gemini_client
from app.utils.logging import get_logger

logger = get_logger(__name__)


# Schema for context optimization output
CONTEXT_SCHEMA = types.Schema(
    type=types.Type.OBJECT,
    properties={
        "optimized_segments": types.Schema(
            type=types.Type.ARRAY,
            description="List of segments with optimized start times.",
            items=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "original_start": types.Schema(
                        type=types.Type.STRING,
                        description="Original start timestamp in HH:MM:SS format.",
                    ),
                    "optimized_start": types.Schema(
                        type=types.Type.STRING,
                        description="Optimized start timestamp at previous sentence break in HH:MM:SS format.",
                    ),
                    "context_added": types.Schema(
                        type=types.Type.STRING,
                        description="Brief description of what context was added.",
                    ),
                },
                required=["original_start", "optimized_start", "context_added"],
            ),
        ),
    },
    required=["optimized_segments"],
)


def get_context_optimization_prompt(segments: list[dict]) -> str:
    """Generate prompt for context optimization."""
    segments_text = "\n".join([
        f"- Segment {i+1}: starts at {seg['start_time']}, ends at {seg['end_time']}"
        for i, seg in enumerate(segments)
    ])
    
    return f"""
Analyze this audio and optimize the start times for the following video segments.

## Segments to Optimize:
{segments_text}

## Your Task:
For EACH segment above:
1. Listen to the audio starting from about 10 seconds BEFORE the given start time
2. Find the nearest COMPLETE SENTENCE BREAK before the start time
3. The goal is to ensure the clip doesn't start mid-sentence or mid-thought

## Rules for Finding the Optimal Start:
- The optimized start should be at the START of a sentence (after a pause, period, or natural break)
- Do NOT go back more than 10 seconds from the original start
- If the original start is already at a sentence break, keep it the same
- The optimized start should NEVER be after the original start

## Example:
If original_start is "00:05:30" and at "00:05:25" there's a sentence like:
"...that's why this is important. [PAUSE] Now let me explain..."
Then optimized_start should be "00:05:25" (right before "Now let me explain")

Return the optimized start times for each segment.
"""


def optimize_segment_starts(
    segments: list[dict],
    uploaded_file: types.File,
) -> list[dict]:
    """
    Use Gemini to find optimal start times for segments.
    
    Args:
        segments: List of segments with start_time and end_time
        uploaded_file: Already uploaded Gemini file (to avoid re-uploading)
        
    Returns:
        List of segments with optimized start times
    """
    if not segments:
        return segments
    
    logger.info(f"🎯 Optimizing start times for {len(segments)} segments...")
    
    client = get_gemini_client()
    
    try:
        prompt = get_context_optimization_prompt(segments)
        
        response = client.generate_content(
            prompt=prompt,
            file=uploaded_file,
            response_schema=CONTEXT_SCHEMA,
            use_video_metadata=False,
        )
        
        data = json.loads(response)
        optimized = data.get("optimized_segments", [])
        
        # Create lookup for original -> optimized
        optimization_map = {
            opt["original_start"]: opt 
            for opt in optimized
        }
        
        # Apply optimizations
        for segment in segments:
            original_start = segment["start_time"]
            if original_start in optimization_map:
                opt = optimization_map[original_start]
                new_start = opt["optimized_start"]
                context = opt.get("context_added", "")
                
                logger.info(f"   {original_start} → {new_start} ({context})")
                segment["start_time"] = new_start
                
                # Recalculate duration
                from app.utils.time_utils import calculate_duration
                segment["duration_seconds"] = calculate_duration(
                    new_start, segment["end_time"]
                )
        
        logger.info(f"✅ Context optimization complete")
        return segments
        
    except Exception as e:
        logger.warning(f"Context optimization failed: {e}, using original timestamps")
        return segments
