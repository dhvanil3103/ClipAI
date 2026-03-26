"""
Pydantic models and LangGraph state types for the podcast clips generator.
"""

import os
from typing import Dict, List, Optional, Tuple
from pydantic import BaseModel, Field, validator
from dotenv import load_dotenv

load_dotenv()


# ---------------------------------------------------------------------------
# Transcript / Video segment models
# ---------------------------------------------------------------------------

class TranscriptSegment(BaseModel):
    start_time: float
    end_time: float
    text: str
    confidence: Optional[float] = None


class VideoSegment(BaseModel):
    start_time: float = Field(description="Start time in seconds")
    end_time: float = Field(description="End time in seconds")
    content: str = Field(description="Transcript content for this segment")
    score: float = Field(description="Engagement score (1-10)", ge=1, le=10)
    reasoning: str = Field(description="Why this segment was selected")
    segment_type: str = Field(description="Type of content (insight, funny, controversial, etc.)")
    # Optional extra fields populated by the analysis node
    engagement_factors: Optional[str] = Field(default="", description="Hook / engagement factor summary")
    transcript_segments: Optional[List[Dict]] = Field(default_factory=list, description="Raw transcript segments in this range")


class ClipMetadata(BaseModel):
    title: str = Field(description="Engaging title for the clip")
    description: str = Field(description="Description for social media")
    hashtags: List[str] = Field(description="Relevant hashtags")
    thumbnail_time: float = Field(description="Best timestamp for thumbnail")
    duration: float = Field(description="Actual duration of the clip")
    platform_specific: Dict[str, Dict] = Field(default_factory=dict)


class ProcessingResult(BaseModel):
    success: bool
    output_path: Optional[str] = None
    errors: List[str] = Field(default_factory=list)
    metadata: Optional[ClipMetadata] = None
    processing_time: Optional[float] = None


# ---------------------------------------------------------------------------
# Configuration models
# ---------------------------------------------------------------------------

class VideoConfig(BaseModel):
    resolution: Tuple[int, int] = Field(default=(1080, 1920))
    aspect_ratio: str = Field(default="original")
    fps: int = Field(default=30)
    bitrate: str = Field(default="6M")
    codec: str = Field(default="libx264")

    @validator('aspect_ratio')
    def validate_aspect_ratio(cls, v):
        valid_ratios = ["original", "16:9", "9:16", "4:3"]
        if v not in valid_ratios:
            raise ValueError(f"Aspect ratio must be one of: {valid_ratios}")
        return v


class TranscriptionConfig(BaseModel):
    primary_source: str = Field(default="youtube")
    language: str = Field(default="en")


class LLMConfig(BaseModel):
    model_name: str = Field(default="gemini-2.5-flash")
    temperature: float = Field(default=0.8, ge=0, le=2)
    max_tokens: int = Field(default=100000)
    api_key: Optional[str] = Field(default=None)
    rate_limit_rpm: int = Field(default=30)

    @validator('api_key', always=True)
    def get_api_key(cls, v):
        return v or os.getenv('GOOGLE_API_KEY')


class ProcessingConfig(BaseModel):
    max_clips_per_video: int = Field(default=3)
    min_clip_duration: int = Field(default=25)
    max_clip_duration: int = Field(default=35)
    target_clip_duration: int = Field(default=30)
    min_engagement_score: float = Field(default=7.5, ge=1, le=10)
    overlap_tolerance: float = Field(default=5.0)
    max_video_duration: int = Field(default=10800)
    api_rate_limit_delay: float = Field(default=5.0)


class AppConfig(BaseModel):
    output_directory: str = Field(default="outputs")
    temp_directory: str = Field(default="temp")
    video: VideoConfig = Field(default_factory=VideoConfig)
    transcription: TranscriptionConfig = Field(default_factory=TranscriptionConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    processing: ProcessingConfig = Field(default_factory=ProcessingConfig)
    enable_parallel_processing: bool = Field(default=True)
    log_level: str = Field(default="INFO")
    log_file: Optional[str] = None
    ffmpeg_path: Optional[str] = None

    @validator('output_directory', 'temp_directory')
    def create_directories(cls, v):
        os.makedirs(v, exist_ok=True)
        return v

    @classmethod
    def from_env(cls) -> "AppConfig":
        return cls(
            output_directory=os.getenv('OUTPUT_DIRECTORY', 'outputs'),
            temp_directory=os.getenv('TEMP_DIRECTORY', 'temp'),
            processing=ProcessingConfig(
                max_clips_per_video=int(os.getenv('MAX_CLIPS_PER_VIDEO', '3')),
                min_clip_duration=int(os.getenv('MIN_CLIP_DURATION', '25')),
                max_clip_duration=int(os.getenv('MAX_CLIP_DURATION', '90')),
                target_clip_duration=int(os.getenv('TARGET_CLIP_DURATION', '60')),
                api_rate_limit_delay=float(os.getenv('API_RATE_LIMIT_DELAY', '5.0'))
            ),
            video=VideoConfig(
                aspect_ratio=os.getenv('DEFAULT_ASPECT_RATIO', 'original')
            ),
            transcription=TranscriptionConfig(),
            llm=LLMConfig(api_key=os.getenv('GOOGLE_API_KEY'))
        )


# ---------------------------------------------------------------------------
# LangGraph state (TypedDict - must remain JSON-serializable)
# ---------------------------------------------------------------------------

from typing import TypedDict


class PodcastState(TypedDict):
    url: str
    video_path: Optional[str]
    audio_path: Optional[str]
    transcript: Optional[str]
    transcript_segments: List[Dict]
    transcript_source: Optional[str]
    identified_clips: List[Dict]
    selected_clips: List[Dict]
    processed_clips: List[Dict]
    metadata: List[Dict]
    video_title: Optional[str]
    video_duration: Optional[float]
    video_id: Optional[str]
    errors: List[str]
    warnings: List[str]
    config: Optional[Dict]
    status: str
    created_at: Optional[str]
    completed_at: Optional[str]
