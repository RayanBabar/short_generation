import asyncio
import sys
import os
from pathlib import Path

# Add project root to python path
sys.path.append(os.getcwd())

from app.services.transcription_precision import get_precision_transcriber

async def main():
    service = get_precision_transcriber()
    # Use one of the uploaded videos
    video_path = Path("uploads/c3595e0f-c568-4540-9835-ff0957c113e3.mp4")
    
    if not video_path.exists():
        # Fallback to finding any mp4
        uploads = list(Path("uploads").glob("*.mp4"))
        if uploads:
            video_path = uploads[0]
        else:
            print("❌ No video found in uploads/ directory for testing")
            return

    print(f"🎬 Testing WhisperX on: {video_path.name}")
    print("⏳ This might take a minute (loading models + aligning)...")
    
    try:
        result = await service.transcribe(video_path)
        
        word_count = len(result['words'])
        print(f"\n✅ Success! Transcription complete.")
        print(f"📊 Total words: {word_count}")
        
        if result['words']:
            first = result['words'][0]
            last = result['words'][-1]
            print(f"🔷 First word: '{first['word']}' ({first['start']:.3f}s - {first['end']:.3f}s)")
            print(f"🔶 Last word:  '{last['word']}' ({last['start']:.3f}s - {last['end']:.3f}s)")
            
            # Check for high precision (millisecond granularity)
            is_precise = (first['start'] != int(first['start'])) or (first['end'] != int(first['end']))
            print(f"🎯 High precision timestamps: {'Yes' if is_precise else 'Maybe (all integers?)'}")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
