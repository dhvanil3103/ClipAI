from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, validator
import asyncio
import json
import os
import uuid
from typing import Dict, List
import sys
from pathlib import Path
import concurrent.futures

# Disable LangSmith tracing to prevent 403 errors
os.environ['LANGCHAIN_TRACING_V2'] = 'false'
os.environ['LANGSMITH_TRACING'] = 'false'

# Add current directory to Python path for imports
sys.path.append(str(Path(__file__).parent.parent))

from src.agents.podcast_agent import PodcastClipsAgent
from src.models.config import AppConfig

app = FastAPI(title="Podcast Clips Generator", version="1.0.0")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for serving video clips
app.mount("/clips", StaticFiles(directory="outputs"), name="clips")

# Initialize the agent
agent = PodcastClipsAgent()

# Global storage for processing status and WebSocket connections
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

class ProgressUpdate(BaseModel):
    status: str
    message: str
    clips: List = []

async def process_video_background(youtube_url: str, session_id: str, num_clips: int = 3, clip_duration: int = 60):
    """Background task to process video - simplified without complex progress tracking"""
    
    async def send_update(status: str, message: str, clips: List = None):
        update = {
            "status": status,
            "message": message,
            "clips": clips or []
        }
        processing_status[session_id] = update
        
        # Send to WebSocket if connected
        if session_id in active_sessions:
            try:
                await active_sessions[session_id].send_text(json.dumps(update))
            except:
                pass  # WebSocket might be disconnected
    
    try:
        # Initial processing state
        await send_update("processing", "Processing your video... This may take a few minutes.")
        
        # Set environment variables for processing
        os.environ['MAX_CLIPS_PER_VIDEO'] = str(num_clips)
        os.environ['TARGET_CLIP_DURATION'] = str(clip_duration)
        os.environ['MIN_CLIP_DURATION'] = str(max(25, clip_duration - 15))
        os.environ['MAX_CLIP_DURATION'] = str(clip_duration + 15)
        os.environ['API_RATE_LIMIT_DELAY'] = '5.0'
        
        def run_processing():
            try:
                result = agent.process_video(youtube_url)
                return result
            except Exception as e:
                raise e
        
        # Run the synchronous processing in a thread
        loop = asyncio.get_event_loop()
        with concurrent.futures.ThreadPoolExecutor() as executor:
            result = await loop.run_in_executor(executor, run_processing)
            
            print("=== PROCESSING COMPLETE ===")
            print(f"Result type: {type(result)}")
            print(f"Result keys: {list(result.keys()) if hasattr(result, 'keys') else 'Not a dict'}")
            
            # Extract clip information from result
            clips_info = []
            processed_clips = result.get("processed_clips", [])
            selected_clips = result.get("selected_clips", [])
            video_id = result.get('video_id', 'unknown')
            
            print(f"Processing {len(processed_clips)} clips for video {video_id}")
            print(f"Selected clips data: {len(selected_clips)} clips with metadata")
            
            for i, (processed_clip, selected_clip) in enumerate(zip(processed_clips, selected_clips), 1):
                try:
                    print(f"Processing clip {i}:")
                    print(f"  Processed: {list(processed_clip.keys()) if hasattr(processed_clip, 'keys') else type(processed_clip)}")
                    print(f"  Selected: {list(selected_clip.keys()) if hasattr(selected_clip, 'keys') else type(selected_clip)}")
                    
                    # Handle different clip data formats robustly
                    if hasattr(processed_clip, 'dict'):
                        proc_data = processed_clip.dict()
                    elif hasattr(processed_clip, '__dict__'):
                        proc_data = processed_clip.__dict__
                    else:
                        proc_data = processed_clip
                    
                    # Get metadata from selected_clips (contains scores, types, etc.)
                    if hasattr(selected_clip, 'dict'):
                        sel_data = selected_clip.dict()
                    elif hasattr(selected_clip, '__dict__'):
                        sel_data = selected_clip.__dict__
                    else:
                        sel_data = selected_clip
                    
                    # Extract clip info combining both data sources
                    start_time = sel_data.get('start_time', 0)
                    end_time = sel_data.get('end_time', start_time + 30)
                    duration = end_time - start_time
                    score = sel_data.get('score', 0)
                    clip_type = sel_data.get('segment_type', sel_data.get('type', 'unknown'))
                    
                    # Get actual file paths from processed clip
                    actual_video_path = proc_data.get('output_path', '')
                    actual_thumbnail_path = proc_data.get('thumbnail_path', '')
                    
                    # Convert absolute paths to relative URLs for the frontend
                    if actual_video_path:
                        # Extract just the filename from the absolute path
                        video_filename = actual_video_path.split('/')[-1] if '/' in actual_video_path else actual_video_path
                        video_path = f"/clips/{video_id}/clips/{video_filename}"
                    else:
                        # Fallback to expected filename
                        sanitized_type = clip_type.replace('|', '_').replace(' ', '_')
                        video_path = f"/clips/{video_id}/clips/clip_{i:02d}_{sanitized_type}.mp4"
                    
                    if actual_thumbnail_path:
                        # Use the actual thumbnail path
                        thumbnail_path = actual_thumbnail_path
                        # Ensure it's a relative path for serving
                        if thumbnail_path.startswith('/'):
                            thumbnail_path = thumbnail_path[1:]  # Remove leading slash
                    else:
                        # Fallback to expected thumbnail path
                        sanitized_type = clip_type.replace('|', '_').replace(' ', '_')
                        thumbnail_path = f"outputs/{video_id}/thumbnails/clip_{i:02d}_{sanitized_type}_thumb.jpg"
                    
                    clip_info = {
                        "id": f"clip_{i:02d}",
                        "title": f"Clip {i}",
                        "duration": f"{duration:.1f}s",
                        "score": score,
                        "type": clip_type,
                        "video_path": video_path,
                        "thumbnail_path": thumbnail_path
                    }
                    
                    clips_info.append(clip_info)
                    print(f"Added clip info: {clip_info}")
                    
                except Exception as e:
                    print(f"Error processing clip {i}: {e}")
                    print(f"  Processed clip data: {processed_clip}")
                    print(f"  Selected clip data: {selected_clip}")
                    continue
            
            # Send final completion update
            await send_update("completed", f"Successfully generated {len(clips_info)} clips!", clips_info)
            
    except Exception as e:
        print(f"❌ Error in background processing: {e}")
        await send_update("failed", f"Processing failed: {str(e)}")

@app.post("/api/process-video")
async def process_video(request: VideoRequest, background_tasks: BackgroundTasks):
    session_id = str(uuid.uuid4())
    
    # Initialize processing status
    processing_status[session_id] = {
        "status": "starting",
        "message": "Initializing...",
        "clips": []
    }
    
    # Start background processing
    background_tasks.add_task(process_video_background, request.youtube_url, session_id, request.num_clips, request.clip_duration)
    
    return {"session_id": session_id, "message": "Processing started"}

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await websocket.accept()
    active_sessions[session_id] = websocket
    
    try:
        # Send current status if available
        if session_id in processing_status:
            await websocket.send_text(json.dumps(processing_status[session_id]))
        
        # Keep connection alive
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        if session_id in active_sessions:
            del active_sessions[session_id]

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
    uvicorn.run(app, host="0.0.0.0", port=8000) 