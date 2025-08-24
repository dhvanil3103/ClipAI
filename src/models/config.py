"""
Configuration models for the podcast clips generator.
"""

import os
from typing import Optional, List, Tuple
from pydantic import BaseModel, Field, validator
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class VideoConfig(BaseModel):
    """Configuration for video processing."""
    resolution: Tuple[int, int] = Field(default=(1080, 1920), description="Output resolution (width, height) - Portrait only")
    aspect_ratio: str = Field(default="original", description="Keep original aspect ratio")
    fps: int = Field(default=30, description="Frames per second - optimized for web")
    bitrate: str = Field(default="6M", description="Video bitrate - balanced quality/size")
    codec: str = Field(default="libx264", description="Video codec")
    
    @validator('aspect_ratio')
    def validate_aspect_ratio(cls, v):
        valid_ratios = ["original", "16:9", "9:16", "4:3"]
        if v not in valid_ratios:
            raise ValueError(f"Aspect ratio must be one of: {valid_ratios}")
        return v


class TranscriptionConfig(BaseModel):
    """Configuration for transcription services."""
    primary_source: str = Field(default="youtube", description="Primary transcription source")
    language: str = Field(default="en", description="Primary language for transcription")


class LLMConfig(BaseModel):
    """Configuration for LLM services."""
    model_name: str = Field(default="gemini-2.5-flash", description="LLM model to use")
    temperature: float = Field(default=0.8, description="Temperature for LLM responses", ge=0, le=2)
    max_tokens: int = Field(default=100000, description="Maximum tokens for LLM responses")
    api_key: Optional[str] = Field(default=None, description="API key for LLM service")
    rate_limit_rpm: int = Field(default=30, description="Rate limit requests per minute")
    
    @validator('api_key', always=True)
    def get_api_key(cls, v):
        return v or os.getenv('GOOGLE_API_KEY')


class ProcessingConfig(BaseModel):
    """Configuration for clip processing."""
    max_clips_per_video: int = Field(default=3, description="Maximum clips to generate per video")
    min_clip_duration: int = Field(default=25, description="Minimum clip duration in seconds")
    max_clip_duration: int = Field(default=35, description="Maximum clip duration in seconds")
    target_clip_duration: int = Field(default=30, description="Target clip duration in seconds")
    min_engagement_score: float = Field(default=7.5, description="Minimum engagement score for clips", ge=1, le=10)
    overlap_tolerance: float = Field(default=5.0, description="Allowed overlap between clips in seconds")
    max_video_duration: int = Field(default=10800, description="Maximum video duration in seconds (3 hours)")
    api_rate_limit_delay: float = Field(default=5.0, description="Delay between API calls in seconds")
    
    @validator('min_clip_duration')
    def validate_min_duration(cls, v, values):
        if 'max_clip_duration' in values and v >= values['max_clip_duration']:
            raise ValueError("min_clip_duration must be less than max_clip_duration")
        return v



class AppConfig(BaseModel):
    """Main application configuration."""
    
    # Directory settings
    output_directory: str = Field(default="outputs", description="Directory for output files")
    temp_directory: str = Field(default="temp", description="Directory for temporary files")
    
    # Component configurations
    video: VideoConfig = Field(default_factory=VideoConfig)
    transcription: TranscriptionConfig = Field(default_factory=TranscriptionConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    processing: ProcessingConfig = Field(default_factory=ProcessingConfig)
    
    # Feature flags
    enable_parallel_processing: bool = Field(default=True, description="Enable parallel processing")
    
    # Logging
    log_level: str = Field(default="INFO", description="Logging level")
    log_file: Optional[str] = Field(default=None, description="Log file path")
    
    # External tools
    ffmpeg_path: Optional[str] = Field(default=None, description="Path to FFmpeg executable")
    
    @validator('output_directory', 'temp_directory')
    def create_directories(cls, v):
        """Create directories if they don't exist."""
        os.makedirs(v, exist_ok=True)
        return v
    
    @classmethod
    def from_env(cls) -> "AppConfig":
        """Create configuration from environment variables."""
        return cls(
            output_directory=os.getenv('OUTPUT_DIRECTORY', 'outputs'),
            temp_directory=os.getenv('TEMP_DIRECTORY', 'temp'),
            processing=ProcessingConfig(
                max_clips_per_video=int(os.getenv('MAX_CLIPS_PER_VIDEO')),
                min_clip_duration=int(os.getenv('MIN_CLIP_DURATION')),
                max_clip_duration=int(os.getenv('MAX_CLIP_DURATION')),
                api_rate_limit_delay=float(os.getenv('API_RATE_LIMIT_DELAY', '5.0'))
            ),
            video=VideoConfig(
                aspect_ratio=os.getenv('DEFAULT_ASPECT_RATIO', 'original')
            ),
            transcription=TranscriptionConfig(),
            llm=LLMConfig(
                api_key=os.getenv('GOOGLE_API_KEY')
            )
        ) 