# Podcast Clips Generator

Turn long YouTube videos into short clips using transcripts, Google Gemini, LangGraph, yt-dlp, and MoviePy. The main runnable surface is a **FastAPI** backend; an optional **React** frontend can submit jobs and show results.

## Features

- **Transcripts** — Fetches captions via the YouTube Transcript API (manual or auto-generated English when available).
- **Analysis** — Single-pass Gemini prompt over the full transcript to propose clip timestamps, scores, and reasoning.
- **Selection** — Validates duration and score, then keeps the top N clips (configurable per request).
- **Download** — yt-dlp with Android / mweb-style client settings to reduce DRM and playback-format breakage as YouTube changes behavior.
- **Rendering** — MoviePy cuts segments, writes MP4s, and saves JPEG thumbnails under `outputs/<video_id>/`.
- **Metadata** — Optional Gemini pass for titles, descriptions, and hashtags per clip.
- **HTTP API** — REST + WebSocket for job status; static files served at `/clips` for generated media.

## Requirements

- Python 3.10+ (3.11 recommended; matches typical venv setups)
- [FFmpeg](https://ffmpeg.org/) on `PATH` (used by MoviePy / imageio-ffmpeg)
- **Google AI API key** with Gemini access ([Google AI Studio](https://aistudio.google.com/app/apikey))

## Quick start (backend only)

From the **repository root** (so `outputs/` and `temp/` resolve correctly):

```bash
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r backend/requirements.txt

cp env.template .env
# Edit .env and set GOOGLE_API_KEY

uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

- Health: `GET http://localhost:8000/api/health`
- Interactive docs: `http://localhost:8000/docs`
- Start processing: `POST /api/process-video` with JSON body, for example:

```json
{
  "youtube_url": "https://www.youtube.com/watch?v=VIDEO_ID",
  "num_clips": 3,
  "clip_duration": 60
}
```

Poll `GET /api/status/{session_id}` or connect to `WebSocket /ws/{session_id}` for updates. Clips appear under `outputs/` and are exposed as URLs under `/clips/...`.

## Full stack (backend + React)

```bash
pip install -r backend/requirements.txt
cd frontend && npm install && cd ..
python start_app.py
```

- Frontend: `http://localhost:3000`
- API: `http://localhost:8000`

`start_app.py` installs backend requirements, runs Uvicorn with `backend.main:app`, then starts the CRA dev server. See `WEBAPP_README.md` for more UI-oriented notes (some paths there may still mention the old `src/` layout).

## Configuration

Copy `env.template` to `.env`. Common variables:

| Variable | Purpose |
|----------|---------|
| `GOOGLE_API_KEY` | Required for Gemini (analysis + metadata). |
| `OUTPUT_DIRECTORY` | Where clips and thumbnails are written (default `outputs`). |
| `TEMP_DIRECTORY` | Where full downloads are stored before cutting (default `temp`). |
| `MAX_CLIPS_PER_VIDEO`, `MIN_CLIP_DURATION`, `MAX_CLIP_DURATION`, `TARGET_CLIP_DURATION` | Defaults used when building `AppConfig` from the environment. |
| `API_RATE_LIMIT_DELAY` | Seconds between Gemini calls in the metadata step. |
| `LANGCHAIN_TRACING_V2` | Set `false` if you do not use LangSmith (backend also disables tracing in code). |

The HTTP API can override clip count and target duration per job via `num_clips` and `clip_duration` on `POST /api/process-video`.

Default Gemini model name is set in `backend/models.py` (`LLMConfig.model_name`, e.g. `gemini-2.5-flash`). Change it there or extend config loading if you need env-based overrides.

## Project structure

```
podcast_to_shortvideos/
├── backend/
│   ├── main.py          # FastAPI app, WebSocket, static /clips mount
│   ├── agent.py         # LangGraph workflow (PodcastClipsAgent)
│   ├── nodes.py         # Transcript, analysis, selection, download, clips, metadata
│   ├── models.py        # Pydantic models, AppConfig, PodcastState
│   └── requirements.txt # Server + pipeline dependencies
├── frontend/            # Create React App UI (optional)
├── start_app.py         # Launches backend + frontend
├── env.template         # Example environment file
├── requirements.txt     # Broader / legacy deps (CLI-era); backend list is authoritative for the API
└── main.py              # Legacy entry point (imports removed `src.cli`; use Uvicorn for the app)
```

## How the pipeline works

1. **Fetch transcript** — Resolve video id, pull English transcript segments, optional metadata via yt-dlp.
2. **Analyze** — Send cleaned transcript + targets to Gemini; parse JSON clip list.
3. **Select** — Filter by duration and minimum score; cap at `max_clips_per_video`.
4. **Download** — yt-dlp writes a full video under `TEMP_DIRECTORY`.
5. **Generate clips** — MoviePy subclips, encode MP4, write thumbnails.
6. **Metadata** — Per-clip Gemini calls for social-style text (with rate limiting).

Graph routing stops early if a step fails (e.g. no transcript, download error).

## Troubleshooting

**Google API key errors**  
Ensure `.env` exists at the project root, contains `GOOGLE_API_KEY`, and the process cwd is the repo root so `python-dotenv` can load it (models call `load_dotenv()`).

**YouTube: DRM / “video is DRM protected” / nsig warnings**  
YouTube changes players and clients often. Upgrade yt-dlp regularly:

```bash
pip install -U yt-dlp
```

The code prefers Android / mweb extractor settings; some videos still need a very new yt-dlp build or may be restricted.

**MoviePy: missing methods (e.g. `subclipped`)**  
Use `moviepy>=2.1.0` as in `backend/requirements.txt`; reinstall if an older pin was installed:

```bash
pip install -U "moviepy>=2.1.0"
```

**FFmpeg not found**  
Install system FFmpeg and ensure it is on `PATH` (e.g. `brew install ffmpeg` on macOS).

**No transcript**  
The video must expose an English transcript (manual or auto-generated). Private, age-restricted, or transcript-disabled videos will fail at the transcript step.

**Import / module errors when starting the server**  
Run Uvicorn from the repository root: `uvicorn backend.main:app ...` so `backend` is importable as a package.

## Cost notes

- YouTube transcripts: no extra API cost beyond normal YouTube access.
- Gemini: billed per your Google AI / Cloud plan; this project uses multiple text calls per video (one large analysis + optional metadata per clip).
- Compute: local CPU/GPU for download and encoding; no required cloud runtime beyond the Gemini API.

## License

MIT License — see LICENSE if present in the repository.

## Contributing

Fork the repository, create a branch, make focused changes, and open a pull request with a clear description of behavior and any new configuration.
