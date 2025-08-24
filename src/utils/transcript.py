"""
Transcript fetching and processing utilities.
"""

import re
from typing import Dict, List, Optional, Tuple
from youtube_transcript_api import YouTubeTranscriptApi
from langchain_community.document_loaders import YoutubeLoader

from ..models.state import TranscriptSegment


def extract_video_id(url: str) -> str:
    """Extract video ID from YouTube URL."""
    patterns = [
        r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([^&\n?#]+)',
        r'youtube\.com/watch\?.*v=([^&\n?#]+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    # If no pattern matches, assume it's already a video ID
    return url


def fetch_youtube_transcript(url: str, prefer_manual: bool = True) -> Tuple[str, List[TranscriptSegment], str]:
    """
    Fetch transcript from YouTube using youtube-transcript-api directly.
    
    Returns:
        Tuple of (full_transcript, segments_with_timing, source)
    """
    video_id = extract_video_id(url)
    
    try:
        # Use youtube-transcript-api directly (more reliable than LangChain)
        from youtube_transcript_api import YouTubeTranscriptApi
        
        # Create API instance
        api = YouTubeTranscriptApi()
        
        # Try to get transcript list for this video
        transcript_list = api.list(video_id)
        
        # Try to get manual transcript first, then auto-generated
        transcript = None
        source = "youtube_manual"
        
        if prefer_manual:
            try:
                transcript = transcript_list.find_manually_created_transcript(['en'])
                source = "youtube_manual"
            except:
                try:
                    transcript = transcript_list.find_generated_transcript(['en'])
                    source = "youtube_auto"
                except:
                    pass
        
        if transcript is None:
            # Get any available transcript
            for t in transcript_list:
                if t.language_code.startswith('en'):
                    transcript = t
                    source = "youtube_auto" if t.is_generated else "youtube_manual"
                    break
        
        if transcript is None:
            raise Exception("No English transcript available for this video")
        
        # Fetch the actual transcript
        transcript_data = transcript.fetch()
        
        if not transcript_data:
            raise Exception("Transcript data is empty")
        
        # Convert to our format
        segments = []
        full_text_parts = []
        
        # transcript_data is a FetchedTranscript object, need to iterate through it
        for item in transcript_data:
            transcript_segment = TranscriptSegment(
                start_time=float(item.start),
                end_time=float(item.start) + float(item.duration),
                text=item.text.strip(),
                confidence=0.95  # High confidence for YouTube transcripts
            )
            segments.append(transcript_segment)
            full_text_parts.append(item.text.strip())
        
        full_transcript = " ".join(full_text_parts)
        
        if len(full_transcript.strip()) < 50:
            raise Exception("Transcript is too short or empty")
        
        return full_transcript, segments, source
            
    except Exception as e:
        raise Exception(f"No transcript found for video {video_id}: {str(e)}")


def get_video_metadata(url: str) -> Dict:
    """Get video metadata using LangChain YoutubeLoader."""
    try:
        loader = YoutubeLoader.from_youtube_url(url, add_video_info=True)
        documents = loader.load()
        
        if documents:
            return documents[0].metadata
        else:
            return {}
            
    except Exception as e:
        print(f"Could not fetch video metadata: {e}")
        return {}


def clean_transcript_text(text: str) -> str:
    """Clean transcript text by removing artifacts and normalizing."""
    # Remove music notation
    text = re.sub(r'\[♪♪♪\]', '', text)
    text = re.sub(r'♪[^♪]*♪', '', text)
    
    # Remove speaker labels if present
    text = re.sub(r'^\s*[A-Z][A-Z\s]+:', '', text, flags=re.MULTILINE)
    
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    
    return text


# Chunking functionality removed - now using single-pass full transcript analysis 