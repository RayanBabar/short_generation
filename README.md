# YouTube Shorts Generator

Generate YouTube Shorts from longer videos using AI-powered analysis and automatic clipping.

## Features

- 🎙️ **Video Transcription** - Transcribe videos with speaker diarization and timestamps using Google Gemini
- 🔍 **Shorts Identification** - AI-powered identification of viral-worthy segments
- ✂️ **Video Clipping** - Automatically clip identified segments using FFmpeg

## Requirements

- Python 3.11+
- FFmpeg (must be installed on system)
- Google Gemini API key

## Installation

1. Install dependencies using uv:

```bash
uv sync
```

2. Create a `.env` file from the example:

```bash
cp .env.example .env
```

3. Add your Gemini API key to `.env`:

```
GEMINI_API_KEY=your_api_key_here
```

4. Ensure FFmpeg is installed:

```bash
# Ubuntu/Debian
sudo apt install ffmpeg

# macOS
brew install ffmpeg
```

## Running the Server

```bash
uv run uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/videos/upload` | Upload a video file |
| POST | `/api/v1/videos/{video_id}/transcribe` | Transcribe an uploaded video |
| POST | `/api/v1/shorts/identify/{video_id}` | Identify potential shorts |
| POST | `/api/v1/shorts/generate/{video_id}` | Generate short clips |
| GET | `/api/v1/shorts/{short_id}` | Download a generated short |

## Workflow

```bash
# 1. Upload video
curl -X POST -F "file=@video.mp4" http://localhost:8000/api/v1/videos/upload
# Returns: {"video_id": "abc123..."}

# 2. Identify shorts
curl -X POST "http://localhost:8000/api/v1/shorts/identify/abc123?max_shorts=5"

# 3. Generate clips
curl -X POST http://localhost:8000/api/v1/shorts/generate/abc123

# 4. Download
curl -O http://localhost:8000/api/v1/shorts/{short_id}
```

## Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `GEMINI_API_KEY` | Google Gemini API key | Required |
| `GEMINI_MODEL` | Gemini model to use | `gemini-2.5-flash` |
| `MIN_SHORT_DURATION` | Minimum short duration (seconds) | `15` |
| `MAX_SHORT_DURATION` | Maximum short duration (seconds) | `60` |

## License

MIT
