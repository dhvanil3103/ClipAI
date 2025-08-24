"""
Transcript fetching node for the LangGraph workflow.
"""

import time
from datetime import datetime
from typing import Dict

from ..models.state import PodcastState
from ..utils.transcript import fetch_youtube_transcript, get_video_metadata
from ..utils.video_utils import extract_video_id_from_url


def fetch_transcript_node(state: PodcastState) -> PodcastState:
    """
    LangGraph node to fetch transcript from YouTube.
    
    This node:
    1. Extracts video metadata
    2. Fetches transcript using multiple methods
    3. Processes and cleans the transcript
    4. Updates the state with transcript data
    """
    
    url = state["url"]
    errors = state.get("errors", [])
    warnings = state.get("warnings", [])
    
    try:
        # Extract video ID
        video_id = extract_video_id_from_url(url)
        
        print(f"🔍 Fetching transcript for video: {video_id}")
        
        # Get video metadata
        try:
            metadata = get_video_metadata(url)
            video_title = metadata.get("title", "Unknown Title")
            video_duration = metadata.get("length", 0)
            
            # Update state with video info
            state["video_title"] = video_title
            state["video_duration"] = float(video_duration) if video_duration else 0.0
            state["video_id"] = video_id
            
            print(f"📹 Video: {video_title} ({video_duration}s)")
            
        except Exception as e:
            warnings.append(f"Could not fetch video metadata: {e}")
            state["video_title"] = "Unknown Title"
            state["video_duration"] = 0.0
            state["video_id"] = video_id
        
        # Fetch transcript
        start_time = time.time()
        full_transcript, segments, source = fetch_youtube_transcript(url)
        fetch_time = time.time() - start_time
        
        print(f"✅ Transcript fetched in {fetch_time:.2f}s from {source}")
        print(f"📝 Transcript: {len(full_transcript)} characters, {len(segments)} segments")
        
        # Convert segments to dictionaries for JSON serialization
        segments_dict = [segment.dict() for segment in segments]
        
        # Update state
        state["transcript"] = full_transcript
        state["transcript_segments"] = segments_dict
        state["transcript_source"] = source
        state["status"] = "transcript_fetched"
        
        # Add timing info
        if state.get("created_at") is None:
            state["created_at"] = datetime.now().isoformat()
        
        return state
        
    except Exception as e:
        error_msg = f"Failed to fetch transcript: {str(e)}"
        print(f"❌ {error_msg}")
        
        errors.append(error_msg)
        state["errors"] = errors
        state["status"] = "failed"
        
        return state 