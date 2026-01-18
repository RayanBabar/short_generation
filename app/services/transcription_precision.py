"""Precision transcription service using WhisperX (Faster-Whisper + Forced Alignment)."""

import logging
import gc
from pathlib import Path
from typing import List, Dict, Any
import asyncio
from concurrent.futures import ThreadPoolExecutor
import whisperx

from app.config import get_settings
from app.utils.logging import get_logger
from app.utils.audio import ensure_audio_exists

logger = get_logger(__name__)

class PrecisionTranscriptionService:
    def __init__(self):
        """
        Initialize the WhisperX transcription service.
        """
        self.settings = get_settings()
        self.model_path = self.settings.whisper_model_path
        self._executor = ThreadPoolExecutor(max_workers=1)
        logger.info(f"Initialized Precision Transcription Service (Model: {self.model_path})")

    def _transcribe_sync(self, audio_path: str) -> Dict[str, Any]:
        """Run blocking transcription + alignment in a separate thread."""
        device = "cpu"
        compute_type = "int8" # efficient on CPU
        batch_size = 4
        
        logger.info(f"⏳ Loading Whisper model '{self.model_path}'...")
        # 1. Transcribe with original whisper (faster_whisper backend)
        model = whisperx.load_model(
            self.model_path, 
            device, 
            compute_type=compute_type,
            threads=12 # Optimize for CPU 
        )
        
        audio = whisperx.load_audio(audio_path)
        logger.info("🎙️ Transcribing...")
        result = model.transcribe(audio, batch_size=batch_size)
        
        # Free up memory before alignment
        del model
        gc.collect()
        
        # 2. Align (The magic step)
        logger.info("📐 Aligning timestamps...")
        try:
            model_a, metadata = whisperx.load_align_model(
                language_code=result["language"], 
                device=device
            )
            result = whisperx.align(
                result["segments"], 
                model_a, 
                metadata, 
                audio, 
                device, 
                return_char_alignments=False
            )
            
            # Clean up alignment model
            del model_a
            gc.collect()
        except Exception as e:
            logger.warning(f"⚠️ Alignment failed, using base timestamps: {e}")

        # Structure the data for easy consumption
        transcript_data = {
            "language": result["language"],
            "language_probability": 1.0, # WhisperX output structure varies, simplifying
            "duration": 0.0, # Not always present in top level
            "text": "".join([s["text"] for s in result["segments"]]).strip(),
            "segments": [],
            "words": []
        }

        # Process segments and words
        for segment in result["segments"]:
            transcript_data["segments"].append({
                "start": segment["start"],
                "end": segment["end"],
                "text": segment["text"].strip()
            })
            
            # Add aligned words if available
            if "words" in segment:
                for word in segment["words"]:
                    # WhisperX logic: unaligned words might miss 'start'/'end'
                    if "start" in word and "end" in word:
                        transcript_data["words"].append({
                            "word": word["word"].strip(),
                            "start": word["start"],
                            "end": word["end"],
                            "probability": word.get("score", 0.0)
                        })
        
        if not transcript_data["words"]:
            logger.warning("⚠️ No word-level timestamps found after alignment!")

        return transcript_data

    async def transcribe(self, video_path: Path) -> Dict[str, Any]:
        """
        Transcribe video audio with high precision timestamps.
        
        Args:
            video_path: Path to the video file
            
        Returns:
            Dictionary containing segments and word-level timestamps
        """
        logger.info(f"🎙️ Starting precision transcription for: {video_path.name}")
        
        # Ensure we have the audio file
        audio_path = ensure_audio_exists(video_path)
        
        # Run CPU-bound transcription in thread pool
        loop = asyncio.get_event_loop()
        try:
            result = await loop.run_in_executor(
                self._executor, 
                self._transcribe_sync, 
                str(audio_path)
            )
            
            word_count = len(result["words"])
            logger.info(f"✅ Transcription complete: {word_count} words aligned")
            return result
            
        except Exception as e:
            logger.error(f"❌ Transcription failed: {str(e)}")
            raise

# Singleton instance
_service = None

def get_precision_transcriber() -> PrecisionTranscriptionService:
    global _service
    if _service is None:
        _service = PrecisionTranscriptionService()
    return _service
