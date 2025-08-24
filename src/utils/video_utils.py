"""
Video download and processing utilities.
"""

import re
from typing import Dict, Optional
from pathlib import Path


def download_video_info(url: str) -> Dict:
    """
    Get video information without downloading the actual video.
    This is a placeholder for now - will be implemented when we add yt-dlp.
    """
    
    # Extract video ID
    video_id = extract_video_id_from_url(url)
    
    # For now, return basic info
    return {
        "video_id": video_id,
        "url": url,
        "title": "Unknown Title",  # Will be fetched from yt-dlp
        "duration": 0,  # Will be fetched from yt-dlp
        "uploader": "Unknown",  # Will be fetched from yt-dlp
        "upload_date": None,  # Will be fetched from yt-dlp
        "view_count": 0,  # Will be fetched from yt-dlp
        "description": "",  # Will be fetched from yt-dlp
    }


def extract_video_id_from_url(url: str) -> str:
    """Extract YouTube video ID from URL."""
    patterns = [
        r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([^&\n?#]+)',
        r'youtube\.com/watch\?.*v=([^&\n?#]+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    return url  # Assume it's already a video ID


def format_duration(seconds: int) -> str:
    """Format duration in seconds to human readable format."""
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60
    
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    else:
        return f"{minutes:02d}:{seconds:02d}"


def create_output_directory(video_id: str, base_output_dir: str = "outputs") -> Path:
    """Create and return the output directory for a video."""
    output_dir = Path(base_output_dir) / video_id
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Create subdirectories
    (output_dir / "clips").mkdir(exist_ok=True)
    (output_dir / "metadata").mkdir(exist_ok=True)
    (output_dir / "thumbnails").mkdir(exist_ok=True)
    
    return output_dir


def validate_youtube_url(url: str) -> bool:
    """Validate if the URL is a valid YouTube URL."""
    youtube_patterns = [
        r'https?://(?:www\.)?youtube\.com/watch\?v=[\w-]+',
        r'https?://youtu\.be/[\w-]+',
        r'https?://(?:www\.)?youtube\.com/embed/[\w-]+',
    ]
    
    return any(re.match(pattern, url) for pattern in youtube_patterns)


def sanitize_filename(filename: str) -> str:
    """Sanitize filename by removing invalid characters."""
    # Remove or replace invalid characters
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    
    # Remove leading/trailing spaces and dots
    filename = filename.strip(' .')
    
    # Limit length
    if len(filename) > 200:
        filename = filename[:200]
    
    return filename 