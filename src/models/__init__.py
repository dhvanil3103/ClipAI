"""
Core data models for the podcast clips generator.
"""

from .state import PodcastState, VideoSegment, ClipMetadata, ProcessingResult
from .config import VideoConfig, TranscriptionConfig, LLMConfig, AppConfig

__all__ = [
    "PodcastState",
    "VideoSegment", 
    "ClipMetadata",
    "ProcessingResult",
    "VideoConfig",
    "TranscriptionConfig", 
    "LLMConfig",
    "AppConfig"
] 