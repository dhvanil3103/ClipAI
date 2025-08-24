"""
Video download node using yt-dlp.
"""

import os
import time
from pathlib import Path
from typing import Dict
import yt_dlp

from ..models.state import PodcastState
from ..models.config import AppConfig
from ..utils.video_utils import extract_video_id_from_url, sanitize_filename


def download_video_node(state: PodcastState) -> PodcastState:
    """
    LangGraph node to download video using yt-dlp.
    
    This node:
    1. Downloads the video in high quality
    2. Extracts metadata (duration, title, etc.)
    3. Validates video duration (warn if >3 hours)
    4. Updates state with paths and metadata
    """
    
    url = state["url"]
    video_id = state.get("video_id")
    errors = state.get("errors", [])
    warnings = state.get("warnings", [])
    
    if not video_id:
        video_id = extract_video_id_from_url(url)
        state["video_id"] = video_id
    
    try:
        # Load configuration
        app_config = AppConfig.from_env()
        
        # Create output directories
        output_dir = Path(app_config.output_directory) / video_id
        output_dir.mkdir(parents=True, exist_ok=True)
        temp_dir = Path(app_config.temp_directory)
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"📥 Downloading video: {video_id}")
        
        # Configure yt-dlp options
        video_output_path = temp_dir / f"{video_id}.%(ext)s"
        
        ydl_opts = {
            # High-quality format selection: prefer 720p+ H.264 with audio, merge if needed
            'format': 'bestvideo[height>=720][ext=mp4][vcodec^=avc1]+bestaudio[ext=m4a]/bestvideo[height>=480][ext=mp4]+bestaudio/best[height>=720]/best[height>=480]/best',
            'outtmpl': str(video_output_path),
            'noplaylist': True,
            'extract_flat': False,
            'writeinfojson': True,
            'writethumbnail': True,
            'writedescription': False,
            # Quality and format options
            'merge_output_format': 'mp4',  # Ensure MP4 output
            'postprocessor_args': ['-movflags', '+faststart'],  # Enable fast seeking
            'prefer_ffmpeg': True,  # Use ffmpeg for better merging
        }
        
        start_time = time.time()
        video_info = None
        actual_video_path = None
        
        # Download video and extract info
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # First, extract info without downloading
            info = ydl.extract_info(url, download=False)
            video_info = info
            
            # Check video duration (warn if >3 hours)
            duration = info.get('duration', 0)
            if duration > app_config.processing.max_video_duration:
                warning_msg = f"Video is {duration/3600:.1f} hours long (>{app_config.processing.max_video_duration/3600:.1f}h limit). Processing may take a very long time."
                warnings.append(warning_msg)
                print(f"⚠️  {warning_msg}")
            
            # Download the video
            print(f"📹 Video: {info.get('title', 'Unknown')} ({duration//60}:{duration%60:02d})")
            ydl.download([url])
            
            # Find the actual downloaded file
            for ext in ['mp4', 'webm', 'mkv']:
                potential_path = temp_dir / f"{video_id}.{ext}"
                if potential_path.exists():
                    actual_video_path = str(potential_path)
                    break
        
        download_time = time.time() - start_time
        
        if not actual_video_path:
            raise Exception("Video download completed but file not found")
        
        # Verify file exists and has content
        if not os.path.exists(actual_video_path) or os.path.getsize(actual_video_path) == 0:
            raise Exception("Downloaded video file is empty or corrupted")
        
        file_size_mb = os.path.getsize(actual_video_path) / (1024 * 1024)
        
        print(f"✅ Video downloaded in {download_time:.1f}s ({file_size_mb:.1f}MB)")
        
        # Update state with video information
        state["video_path"] = actual_video_path
        state["video_title"] = video_info.get('title', 'Unknown Title')
        state["video_duration"] = float(video_info.get('duration', 0))
        
        # Store additional metadata
        state["video_metadata"] = {
            "uploader": video_info.get('uploader', 'Unknown'),
            "upload_date": video_info.get('upload_date'),
            "view_count": video_info.get('view_count', 0),
            "like_count": video_info.get('like_count', 0),
            "description": video_info.get('description', ''),
            "file_size_mb": file_size_mb,
            "format": video_info.get('ext', 'mp4'),
            "resolution": f"{video_info.get('width', 0)}x{video_info.get('height', 0)}",
            "fps": video_info.get('fps', 30)
        }
        
        state["warnings"] = warnings
        state["status"] = "video_downloaded"
        
        return state
        
    except Exception as e:
        error_msg = f"Video download failed: {str(e)}"
        print(f"❌ {error_msg}")
        
        errors.append(error_msg)
        state["errors"] = errors
        state["status"] = "failed"
        
        return state


def get_video_info_only(url: str) -> Dict:
    """
    Get video information without downloading the video.
    Used for metadata extraction before deciding to download.
    """
    
    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            return {
                "title": info.get('title', 'Unknown'),
                "duration": info.get('duration', 0),
                "uploader": info.get('uploader', 'Unknown'),
                "upload_date": info.get('upload_date'),
                "view_count": info.get('view_count', 0),
                "description": info.get('description', ''),
                "thumbnail": info.get('thumbnail'),
                "formats_available": len(info.get('formats', [])),
                "has_subtitles": bool(info.get('subtitles', {})),
                "video_id": info.get('id', ''),
                "webpage_url": info.get('webpage_url', url)
            }
            
    except Exception as e:
        raise Exception(f"Could not extract video info: {str(e)}")


def cleanup_video_file(video_path: str):
    """Clean up downloaded video file to save space."""
    try:
        if os.path.exists(video_path):
            os.remove(video_path)
            print(f"🗑️  Cleaned up video file: {os.path.basename(video_path)}")
    except Exception as e:
        print(f"⚠️  Could not clean up video file: {e}") 