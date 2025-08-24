"""
Clip selection node - simplified for single-pass analysis approach.
"""

from typing import List
from ..models.state import PodcastState, VideoSegment
from ..models.config import AppConfig


def select_clips_node(state: PodcastState) -> PodcastState:
    """
    LangGraph node to validate and finalize clip selection.
    
    Since the new analysis approach uses full transcript context to identify
    the optimal clips directly, this node primarily validates the results
    and ensures they meet our criteria.
    """
    
    identified_clips = state.get("identified_clips", [])
    errors = state.get("errors", [])
    warnings = state.get("warnings", [])
    
    if not identified_clips:
        warning_msg = "No clips identified by analysis"
        warnings.append(warning_msg)
        state["warnings"] = warnings
        state["selected_clips"] = []
        state["status"] = "no_clips_identified"
        return state
    
    try:
        # Load configuration
        app_config = AppConfig.from_env()
        
        print(f"🎯 Validating {len(identified_clips)} clips from full transcript analysis")
        
        # Convert back to VideoSegment objects
        clips = [VideoSegment(**clip_data) for clip_data in identified_clips]
        
        # Apply basic validation filters
        validated_clips = []
        
        for clip in clips:
            # Validate duration
            duration = clip.end_time - clip.start_time
            if duration < app_config.processing.min_clip_duration:
                print(f"⚠️  Skipping clip {clip.start_time:.1f}s-{clip.end_time:.1f}s: too short ({duration:.1f}s)")
                continue
            
            if duration > app_config.processing.max_clip_duration:
                print(f"⚠️  Skipping clip {clip.start_time:.1f}s-{clip.end_time:.1f}s: too long ({duration:.1f}s)")
                continue
            
            # Validate score (should already be high from analysis)
            if clip.score < app_config.processing.min_engagement_score:
                print(f"⚠️  Skipping clip {clip.start_time:.1f}s-{clip.end_time:.1f}s: low score ({clip.score:.1f})")
                continue
            
            validated_clips.append(clip)
        
        print(f"✅ {len(validated_clips)} clips passed validation")
        
        # Sort by score (highest first) - though they should already be optimal
        validated_clips.sort(key=lambda x: x.score, reverse=True)
        
        # Take the requested number of clips
        max_clips = app_config.processing.max_clips_per_video
        selected_clips = validated_clips[:max_clips]
        
        print(f"🎬 Selected {len(selected_clips)} final clips")
        
        # Display selection summary
        for i, clip in enumerate(selected_clips, 1):
            duration = clip.end_time - clip.start_time
            print(f"  🎯 Clip {i}: {clip.start_time:.1f}s-{clip.end_time:.1f}s "
                  f"({duration:.1f}s, score: {clip.score:.1f}, type: {clip.segment_type})")
            print(f"      Reasoning: {clip.reasoning[:100]}...")
        
        if not selected_clips:
            warning_msg = "No clips passed validation criteria"
            warnings.append(warning_msg)
            state["warnings"] = warnings
            state["selected_clips"] = []
            state["status"] = "no_clips_passed_validation"
            return state
        
        # Convert back to dictionaries for JSON serialization
        selected_clips_dict = [clip.dict() for clip in selected_clips]
        
        # Update state
        state["selected_clips"] = selected_clips_dict
        state["status"] = "clips_selected"
        state["warnings"] = warnings
        
        print(f"🎉 Clip selection complete - {len(selected_clips)} high-quality clips ready!")
        
    except Exception as e:
        error_msg = f"Clip selection failed: {str(e)}"
        errors.append(error_msg)
        print(f"❌ {error_msg}")
        state["errors"] = errors
        state["status"] = "selection_failed"
    
    return state 