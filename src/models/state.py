"""
State management models for the LangGraph workflow.
"""

from typing import Dict, List, Optional, TypedDict
from pydantic import BaseModel, Field
from datetime import datetime


class VideoSegment(BaseModel):
    """Represents a video segment with timing and content information."""
    start_time: float = Field(description="Start time in seconds")
    end_time: float = Field(description="End time in seconds")
    content: str = Field(description="Transcript content for this segment")
    score: float = Field(description="Engagement score (1-10)", ge=1, le=10)
    reasoning: str = Field(description="Why this segment was selected")
    segment_type: str = Field(description="Type of content (insight, funny, controversial, etc.)")


class ClipMetadata(BaseModel):
    """Metadata for a generated clip."""
    title: str = Field(description="Engaging title for the clip")
    description: str = Field(description="Description for social media")
    hashtags: List[str] = Field(description="Relevant hashtags")
    thumbnail_time: float = Field(description="Best timestamp for thumbnail")
    duration: float = Field(description="Actual duration of the clip")
    platform_specific: Dict[str, Dict] = Field(
        default_factory=dict,
        description="Platform-specific metadata (youtube, instagram, tiktok)"
    )


class ProcessingResult(BaseModel):
    """Result of processing a single clip or operation."""
    success: bool = Field(description="Whether the operation succeeded")
    output_path: Optional[str] = Field(default=None, description="Path to generated file")
    errors: List[str] = Field(default_factory=list, description="Any errors encountered")
    metadata: Optional[ClipMetadata] = Field(default=None, description="Generated metadata")
    processing_time: Optional[float] = Field(default=None, description="Time taken to process")


class TranscriptSegment(BaseModel):
    """A segment of transcript with timing information."""
    start_time: float
    end_time: float
    text: str
    confidence: Optional[float] = None


# TypedDict for LangGraph state - must be JSON serializable
class PodcastState(TypedDict):
    """Main state object passed between LangGraph nodes."""
    
    # Input
    url: str
    
    # Downloaded content
    video_path: Optional[str]
    audio_path: Optional[str]
    
    # Transcript data
    transcript: Optional[str]
    transcript_segments: List[Dict]  # List of TranscriptSegment.dict()
    transcript_source: Optional[str]  # "youtube" or "whisper"
    
    # Analysis results
    identified_clips: List[Dict]  # List of VideoSegment.dict()
    selected_clips: List[Dict]    # Filtered clips for processing
    
    # Processing results
    processed_clips: List[Dict]   # List of ProcessingResult.dict()
    metadata: List[Dict]          # List of ClipMetadata.dict()
    
    # Metadata
    video_title: Optional[str]
    video_duration: Optional[float]
    video_id: Optional[str]
    
    # Error handling
    errors: List[str]
    warnings: List[str]
    
    # Configuration
    config: Optional[Dict]
    
    # Processing status
    status: str  # "processing", "completed", "failed"
    created_at: Optional[str]
    completed_at: Optional[str] 