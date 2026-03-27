import asyncio
import concurrent.futures
import glob
import json
import os
import uuid
from pathlib import Path
from typing import Dict, List

from fastapi import BackgroundTasks, FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, validator

from .agent import PodcastClipsAgent

# Disable LangSmith tracing to prevent 403 errors
os.environ['LANGCHAIN_TRACING_V2'] = 'false'
os.environ['LANGSMITH_TRACING'] = 'false'

app = FastAPI(title="Podcast Clips Generator", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("FRONTEND_URL")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Project root is two levels up from this file (backend/main.py → backend/ → project root)
project_root = Path(__file__).parent.parent
outputs_dir = project_root / "outputs"
outputs_dir.mkdir(exist_ok=True)

# Serve generated clip files at /clips
app.mount("/clips", StaticFiles(directory=str(outputs_dir)), name="clips")

# Initialise the agent once at startup
agent = PodcastClipsAgent()

processing_status: Dict[str, dict] = {}
active_sessions: Dict[str, WebSocket] = {}


class VideoRequest(BaseModel):
    youtube_url: str
    num_clips: int = 3
    clip_duration: int = 60

    @validator('num_clips')
    def validate_num_clips(cls, v):
        if v < 1 or v > 10:
            raise ValueError('num_clips must be between 1 and 10')
        return v

    @validator('clip_duration')
    def validate_clip_duration(cls, v):
        if v < 15 or v > 120:
            raise ValueError('clip_duration must be between 15 and 120 seconds')
        return v


async def _send_update(session_id: str, status: str, message: str, clips: List = None):
    """Persist the latest status and push it over WebSocket if the client is connected."""
    update = {"status": status, "message": message, "clips": clips or []}
    processing_status[session_id] = update
    if session_id in active_sessions:
        try:
            await active_sessions[session_id].send_text(json.dumps(update))
        except Exception:
            pass


async def process_video_background(
    youtube_url: str,
    session_id: str,
    num_clips: int = 3,
    clip_duration: int = 60,
):
    """Run the agent in a thread pool and relay progress via WebSocket."""

    print(f"[{session_id}] Starting — {num_clips} clips × {clip_duration}s")

    await _send_update(session_id, "processing", "Processing your video… This may take a few minutes.")

    custom_config = {
        'max_clips_per_video': num_clips,
        'target_clip_duration': clip_duration,
        'min_clip_duration': max(10, clip_duration - 10),
        'max_clip_duration': clip_duration + 15,
        'api_rate_limit_delay': 5.0,
    }

    def run_agent():
        return agent.process_video(youtube_url, config=custom_config)

    try:
        loop = asyncio.get_running_loop()
        with concurrent.futures.ThreadPoolExecutor() as executor:
            result = await loop.run_in_executor(executor, run_agent)

        video_id = result.get('video_id', 'unknown')
        processed_clips = result.get("processed_clips", [])
        selected_clips = result.get("selected_clips", [])
        successful = [c for c in processed_clips if c.get("success", False)]

        print(f"[{session_id}] Done — {len(successful)} successful clips for video {video_id}")

        clips_info = []
        for i, (proc, sel) in enumerate(zip(successful, selected_clips[:len(successful)]), 1):
            try:
                sel_data = sel.model_dump() if hasattr(sel, 'model_dump') else (sel.__dict__ if hasattr(sel, '__dict__') else sel)
                proc_data = proc.model_dump() if hasattr(proc, 'model_dump') else (proc.__dict__ if hasattr(proc, '__dict__') else proc)

                start_time = sel_data.get('start_time', 0)
                end_time = sel_data.get('end_time', start_time + 30)
                score = sel_data.get('score', 0)
                clip_type = sel_data.get('segment_type', sel_data.get('type', 'unknown'))

                # --- Video URL ---
                actual_video_path = proc_data.get('output_path', '')
                if actual_video_path and os.path.exists(actual_video_path):
                    video_filename = os.path.basename(actual_video_path)
                    video_url = f"/clips/{video_id}/clips/{video_filename}"
                else:
                    clips_dir = outputs_dir / video_id / "clips"
                    pattern = str(clips_dir / f"clip_{i:02d}_*.mp4")
                    matches = glob.glob(pattern)
                    if matches:
                        video_url = f"/clips/{video_id}/clips/{os.path.basename(matches[0])}"
                    else:
                        sanitized = clip_type.replace('|', '_').replace(' ', '_')
                        video_url = f"/clips/{video_id}/clips/clip_{i:02d}_{sanitized}.mp4"

                # --- Thumbnail URL ---
                actual_thumb_path = proc_data.get('thumbnail_path', '')
                if actual_thumb_path and os.path.exists(actual_thumb_path):
                    # Convert absolute filesystem path → /clips/... URL
                    thumb_str = str(actual_thumb_path)
                    outputs_str = str(outputs_dir)
                    if thumb_str.startswith(outputs_str):
                        rel = thumb_str[len(outputs_str):].lstrip('/')
                        thumbnail_url = f"/clips/{rel}"
                    else:
                        thumbnail_url = f"/clips/{video_id}/thumbnails/{os.path.basename(thumb_str)}"
                else:
                    sanitized = clip_type.replace('|', '_').replace(' ', '_')
                    thumbnail_url = f"/clips/{video_id}/thumbnails/clip_{i:02d}_{sanitized}_thumb.jpg"

                clips_info.append({
                    "id": f"clip_{i:02d}",
                    "title": f"Clip {i}",
                    "duration": f"{end_time - start_time:.1f}s",
                    "score": score,
                    "type": clip_type,
                    "video_path": video_url,
                    "thumbnail_path": thumbnail_url,
                })

            except Exception as e:
                print(f"[{session_id}] Error building clip {i} info: {e}")

        await _send_update(
            session_id,
            "completed",
            f"Successfully generated {len(clips_info)} clip{'s' if len(clips_info) != 1 else ''}!",
            clips_info,
        )

    except Exception as e:
        print(f"[{session_id}] Processing error: {e}")
        await _send_update(session_id, "failed", f"Processing failed: {e}")


@app.post("/api/process-video")
async def process_video(request: VideoRequest, background_tasks: BackgroundTasks):
    session_id = str(uuid.uuid4())
    processing_status[session_id] = {"status": "starting", "message": "Initialising…", "clips": []}
    background_tasks.add_task(
        process_video_background,
        request.youtube_url,
        session_id,
        request.num_clips,
        request.clip_duration,
    )
    return {"session_id": session_id, "message": "Processing started"}


@app.websocket("/wss/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await websocket.accept()
    active_sessions[session_id] = websocket
    try:
        if session_id in processing_status:
            await websocket.send_text(json.dumps(processing_status[session_id]))
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        active_sessions.pop(session_id, None)


@app.get("/api/status/{session_id}")
async def get_status(session_id: str):
    if session_id not in processing_status:
        raise HTTPException(status_code=404, detail="Session not found")
    return processing_status[session_id]


@app.get("/api/health")
async def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=False)
