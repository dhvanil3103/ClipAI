from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import asyncio
import json
import os
import uuid
from typing import Dict, List
import sys
from pathlib import Path

# Add current directory to Python path for imports
sys.path.append(str(Path(__file__).parent.parent))

from src.agents.podcast_agent import PodcastClipsAgent
from src.models.config import AppConfig

app = FastAPI(title="Podcast Clips Generator", version="1.0.0")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files (generated clips)
app.mount("/clips", StaticFiles(directory="outputs"), name="clips")

# In-memory storage for active sessions
active_sessions: Dict[str, WebSocket] = {}
processing_status: Dict[str, Dict] = {}

class VideoRequest(BaseModel):
    youtube_url: str

class ProgressUpdate(BaseModel):
    session_id: str
    status: str
    progress: int
    message: str
    clips: List[Dict] = []

agent = PodcastClipsAgent()

@app.post("/api/process-video")
async def process_video(request: VideoRequest, background_tasks: BackgroundTasks):
    """Start video processing and return session ID"""
    session_id = str(uuid.uuid4())
    
    # Initialize processing status
    processing_status[session_id] = {
        "status": "starting",
        "progress": 0,
        "message": "Initializing...",
        "clips": []
    }
    
    # Start background processing
    background_tasks.add_task(process_video_background, session_id, request.youtube_url)
    
    return {"session_id": session_id}

async def process_video_background(session_id: str, youtube_url: str):
    """Background task to process video and send progress updates"""
    
    async def send_progress(status: str, progress: int, message: str, clips: List = None):
        update = {
            "status": status,
            "progress": progress,
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
        await send_progress("fetching", 10, "Fetching transcript...")
        
        # Set environment variables for this processing
        os.environ['MAX_CLIPS_PER_VIDEO'] = '3'
        os.environ['API_RATE_LIMIT_DELAY'] = '1.0'
        
        # Use a sync function and run it in thread pool
        import asyncio
        import concurrent.futures
        
        def run_processing():
            try:
                result = agent.process_video(youtube_url)
                return result
            except Exception as e:
                raise e
        
        # Send progress updates while processing
        await send_progress("analyzing", 30, "Analyzing content...")
        
        # Run the synchronous processing in a thread
        loop = asyncio.get_event_loop()
        with concurrent.futures.ThreadPoolExecutor() as executor:
            # Start processing in background
            future = loop.run_in_executor(executor, run_processing)
            
            # Simulate progress updates while processing
            progress_steps = [
                (40, "Analyzing chunks..."),
                (50, "Selecting best clips..."),
                (60, "Downloading video..."),
                (75, "Generating clips..."),
                (90, "Creating metadata...")
            ]
            
            # Update progress every few seconds
            for i, (prog, msg) in enumerate(progress_steps):
                await asyncio.sleep(3)  # Wait 3 seconds between updates
                if not future.done():
                    await send_progress("processing", prog, msg)
            
            # Wait for completion
            result = await future
        
                # Process successful result
        if result and result.get("status") != "failed":
                        clips_data = []
            
            # Extract clips from processed_clips or selected_clips
            clips_source = result.get("processed_clips") or result.get("selected_clips", [])
            
            if clips_source:
                    video_id = result.get("video_id", "unknown")
                    print(f"Processing {len(clips_source)} clips for video {video_id}")
                    
                    for i, clip in enumerate(clips_source, 1):
                        try:
                            # Handle both dictionary and object formats
                            if hasattr(clip, 'dict'):
                                clip_dict = clip.dict()
                            elif hasattr(clip, '__dict__'):
                                clip_dict = clip.__dict__
                            else:
                                clip_dict = clip
                            
                            print(f"Processing clip {i}: {clip_dict}")
                            
                            # Extract clip information with safe fallbacks
                            start_time = clip_dict.get('start_time') or clip_dict.get('start') or 0
                            end_time = clip_dict.get('end_time') or clip_dict.get('end') or start_time + 30
                            
                            # Handle segment_data
                            segment_data = clip_dict.get('segment_data', {})
                            if not segment_data and 'reasoning' in clip_dict:
                                # Create segment_data from direct clip properties
                                segment_data = {
                                    'segment_type': clip_dict.get('segment_type', 'highlight'),
                                    'score': clip_dict.get('score', 8.0),
                                    'reasoning': clip_dict.get('reasoning', ''),
                                    'title': f"Clip {i}"
                                }
                            
                            # Use output_path if available, otherwise construct
                            output_path = clip_dict.get('output_path', '')
                            if output_path and os.path.exists(output_path):
                                # Extract filename from actual path
                                filename = os.path.basename(output_path)
                                video_path = f"/clips/{video_id}/clips/{filename}"
                                thumb_path = f"/clips/{video_id}/thumbnails/{filename.replace('.mp4', '_thumb.jpg')}"
                            else:
                                # Construct expected paths
                                clip_type = segment_data.get('segment_type', 'clip')
                                video_path = f"/clips/{video_id}/clips/clip_{i:02d}_{clip_type}.mp4"
                                thumb_path = f"/clips/{video_id}/thumbnails/clip_{i:02d}_{clip_type}_thumb.jpg"
                            
                            clip_info = {
                                "id": f"clip_{i:02d}",
                                "title": segment_data.get('title', f"Clip {i}"),
                                "duration": f"{end_time - start_time:.1f}s",
                                "score": segment_data.get('score', 8.0),
                                "type": segment_data.get('segment_type', 'highlight'),
                                "video_path": video_path,
                                "thumbnail_path": thumb_path
                            }
                            clips_data.append(clip_info)
                            print(f"Added clip info: {clip_info}")
                            
                        except Exception as clip_error:
                            print(f"Error processing clip {i}: {clip_error}")
                            continue
            
            if clips_data:
                await send_progress("completed", 100, f"Successfully generated {len(clips_data)} clips!", clips_data)
            else:
                await send_progress("completed", 100, "Processing completed but no clips were generated.", [])
        else:
            error_msg = "Processing completed but failed to generate clips"
            if result and result.get("errors"):
                error_msg = f"Processing failed: {result['errors'][-1]}"
            await send_progress("error", 0, error_msg)
        
    except Exception as e:
        error_msg = f"Processing error: {str(e)}"
        print(f"Backend error: {error_msg}")  # Debug logging
        await send_progress("error", 0, error_msg)

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for real-time progress updates"""
    await websocket.accept()
    active_sessions[session_id] = websocket
    
    # Send current status if available
    if session_id in processing_status:
        await websocket.send_text(json.dumps(processing_status[session_id]))
    
    try:
        while True:
            # Keep connection alive
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        if session_id in active_sessions:
            del active_sessions[session_id]

@app.get("/api/status/{session_id}")
async def get_status(session_id: str):
    """Get current processing status"""
    if session_id not in processing_status:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return processing_status[session_id]

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 