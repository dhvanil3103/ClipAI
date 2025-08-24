"""
Clip generation node using MoviePy for video processing.
"""

import os
import time
from pathlib import Path
from typing import List
from moviepy import VideoFileClip, CompositeVideoClip, ColorClip
import moviepy.config as mp_config

from ..models.state import PodcastState, VideoSegment, ProcessingResult
from ..models.config import AppConfig
from ..utils.video_utils import sanitize_filename


def generate_clips_node(state: PodcastState) -> PodcastState:
    """
    LangGraph node to generate video clips from selected segments.
    
    This node:
    1. Loads the main video file
    2. Extracts each selected clip segment
    3. Converts to portrait format (9:16)
    4. Saves clips with proper naming
    5. Generates thumbnails
    """
    
    video_path = state.get("video_path")
    selected_clips = state.get("selected_clips", [])
    video_id = state.get("video_id")
    errors = state.get("errors", [])
    warnings = state.get("warnings", [])
    
    if not video_path or not os.path.exists(video_path):
        error_msg = "No video file available for clip generation"
        errors.append(error_msg)
        state["errors"] = errors
        return state
    
    if not selected_clips:
        warning_msg = "No clips selected for generation"
        warnings.append(warning_msg)
        state["warnings"] = warnings
        state["processed_clips"] = []
        state["status"] = "no_clips_to_generate"
        return state
    
    try:
        # Load configuration
        app_config = AppConfig.from_env()
        
        # Apply custom configuration overrides from state
        custom_config = state.get("config", {})
        if custom_config:
            # Override specific values if provided
            if "max_clips_per_video" in custom_config:
                app_config.processing.max_clips_per_video = custom_config["max_clips_per_video"]
            if "target_clip_duration" in custom_config:
                app_config.processing.target_clip_duration = custom_config["target_clip_duration"]
            if "min_clip_duration" in custom_config:
                app_config.processing.min_clip_duration = custom_config["min_clip_duration"]
            if "max_clip_duration" in custom_config:
                app_config.processing.max_clip_duration = custom_config["max_clip_duration"]
        
        # Create output directories
        output_dir = Path(app_config.output_directory) / video_id
        clips_dir = output_dir / "clips"
        thumbnails_dir = output_dir / "thumbnails"
        clips_dir.mkdir(parents=True, exist_ok=True)
        thumbnails_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"🎬 Generating {len(selected_clips)} video clips")
        
        # Load the main video
        print("📹 Loading video file...")
        main_video = VideoFileClip(video_path)
        
        processed_clips = []
        total_generation_time = 0
        
        # Convert selected clips back to VideoSegment objects
        clips = [VideoSegment(**clip_data) for clip_data in selected_clips]
        
        for i, clip in enumerate(clips, 1):
            try:
                start_time = time.time()
                
                print(f"🎯 Processing clip {i}/{len(clips)}: {clip.start_time:.1f}s-{clip.end_time:.1f}s")
                
                # Extract clip segment
                clip_segment = main_video.subclipped(clip.start_time, clip.end_time)
                
                # Keep original format or apply conversion if needed
                if app_config.video.aspect_ratio == "original":
                    final_clip = clip_segment  # Keep original format for speed
                else:
                    final_clip = convert_to_portrait(clip_segment, app_config.video.resolution)
                
                # Generate filename
                clip_title = sanitize_filename(f"clip_{i:02d}_{clip.segment_type}")
                clip_filename = f"{clip_title}.mp4"
                clip_path = clips_dir / clip_filename
                
                # Save the clip with web-optimized settings
                final_clip.write_videofile(
                    str(clip_path),
                    codec=app_config.video.codec,
                    audio_codec='aac',
                    temp_audiofile='temp-audio.m4a',
                    remove_temp=True,
                    fps=app_config.video.fps,
                    bitrate=app_config.video.bitrate,
                    preset='faster',  # Good quality/speed balance
                    ffmpeg_params=[
                        '-movflags', '+faststart',  # Enable fast seeking
                        '-profile:v', 'main',      # Better web compatibility
                        '-level', '4.0',           # H.264 level for web
                        '-pix_fmt', 'yuv420p',     # Ensure web compatibility
                        '-g', '30',                # Keyframe every 30 frames for seeking
                    ]
                )
                
                # Generate thumbnail
                thumbnail_path = generate_thumbnail(final_clip, thumbnails_dir, clip_title)
                
                # Clean up clip objects
                if final_clip != clip_segment:
                    final_clip.close()
                clip_segment.close()
                
                generation_time = time.time() - start_time
                total_generation_time += generation_time
                
                # Get file size
                file_size_mb = os.path.getsize(clip_path) / (1024 * 1024)
                
                # Create processing result
                result = ProcessingResult(
                    success=True,
                    output_path=str(clip_path),
                    metadata=None,  # Will be generated in metadata node
                    processing_time=generation_time
                )
                
                processed_clips.append({
                    **result.dict(),
                    "clip_index": i,
                    "segment_data": clip.dict(),
                    "file_size_mb": file_size_mb,
                    "thumbnail_path": str(thumbnail_path),
                    "filename": clip_filename
                })
                
                print(f"  ✅ Clip {i} generated in {generation_time:.1f}s ({file_size_mb:.1f}MB)")
                
            except Exception as e:
                error_msg = f"Failed to generate clip {i}: {str(e)}"
                print(f"  ❌ {error_msg}")
                warnings.append(error_msg)
                
                # Add failed result
                result = ProcessingResult(
                    success=False,
                    errors=[error_msg],
                    processing_time=time.time() - start_time
                )
                
                processed_clips.append({
                    **result.dict(),
                    "clip_index": i,
                    "segment_data": clip.dict(),
                    "filename": f"failed_clip_{i}.mp4"
                })
                continue
        
        # Clean up main video
        main_video.close()
        
        print(f"✅ Clip generation completed in {total_generation_time:.1f}s")
        
        successful_clips = [c for c in processed_clips if c["success"]]
        failed_clips = [c for c in processed_clips if not c["success"]]
        
        print(f"📊 Results: {len(successful_clips)} successful, {len(failed_clips)} failed")
        
        # Update state
        state["processed_clips"] = processed_clips
        state["warnings"] = warnings
        
        if successful_clips:
            state["status"] = "clips_generated"
        else:
            state["status"] = "clip_generation_failed"
        
        return state
        
    except Exception as e:
        error_msg = f"Clip generation failed: {str(e)}"
        print(f"❌ {error_msg}")
        
        errors.append(error_msg)
        state["errors"] = errors
        state["status"] = "failed"
        
        return state


def convert_to_portrait(clip: VideoFileClip, target_resolution: tuple) -> VideoFileClip:
    """
    Convert video clip to portrait format (9:16) with intelligent cropping/padding.
    """
    
    target_width, target_height = target_resolution
    current_width, current_height = clip.size
    
    # Calculate aspect ratios
    target_aspect = target_width / target_height  # Should be 9/16 = 0.5625
    current_aspect = current_width / current_height
    
    if abs(current_aspect - target_aspect) < 0.01:
        # Already correct aspect ratio, just resize
        return clip.resized((target_width, target_height))
    
    if current_aspect > target_aspect:
        # Video is too wide, need to crop horizontally or add padding
        # Calculate optimal height based on width
        optimal_height = current_width / target_aspect
        
        if optimal_height <= current_height:
            # Crop vertically to fit
            crop_height = optimal_height
            y_center = current_height / 2
            y1 = max(0, y_center - crop_height / 2)
            y2 = min(current_height, y1 + crop_height)
            
            cropped = clip.cropped(y1=y1, y2=y2)
            return cropped.resized((target_width, target_height))
        else:
            # Add horizontal padding (letterbox effect)
            # Resize to fit height
            scale_factor = target_height / current_height
            new_width = int(current_width * scale_factor)
            
            resized_clip = clip.resized((new_width, target_height))
            
            # Create background
            bg = ColorClip(size=(target_width, target_height), color=(0, 0, 0))
            bg = bg.with_duration(clip.duration)
            
            # Center the resized clip
            x_offset = (target_width - new_width) // 2
            positioned_clip = resized_clip.with_position((x_offset, 0))
            
            return CompositeVideoClip([bg, positioned_clip])
    
    else:
        # Video is too tall, need to crop vertically or add padding
        # Calculate optimal width based on height
        optimal_width = current_height * target_aspect
        
        if optimal_width <= current_width:
            # Crop horizontally to fit
            crop_width = optimal_width
            x_center = current_width / 2
            x1 = max(0, x_center - crop_width / 2)
            x2 = min(current_width, x1 + crop_width)
            
            cropped = clip.cropped(x1=x1, x2=x2)
            return cropped.resized((target_width, target_height))
        else:
            # Add vertical padding
            # Resize to fit width
            scale_factor = target_width / current_width
            new_height = int(current_height * scale_factor)
            
            resized_clip = clip.resized((target_width, new_height))
            
            # Create background
            bg = ColorClip(size=(target_width, target_height), color=(0, 0, 0))
            bg = bg.with_duration(clip.duration)
            
            # Center the resized clip
            y_offset = (target_height - new_height) // 2
            positioned_clip = resized_clip.with_position((0, y_offset))
            
            return CompositeVideoClip([bg, positioned_clip])


def generate_thumbnail(clip: VideoFileClip, thumbnails_dir: Path, clip_title: str) -> Path:
    """
    Generate a thumbnail image from the middle of the clip.
    """
    
    # Get frame from middle of clip
    thumbnail_time = clip.duration / 2
    
    thumbnail_path = thumbnails_dir / f"{clip_title}_thumb.jpg"
    
    # Save thumbnail
    clip.save_frame(str(thumbnail_path), t=thumbnail_time)
    
    return thumbnail_path


def cleanup_temp_files(temp_dir: Path):
    """Clean up temporary files created during video processing."""
    try:
        temp_files = [
            "temp-audio.m4a",
            "temp-audio.wav"
        ]
        
        for temp_file in temp_files:
            temp_path = temp_dir / temp_file
            if temp_path.exists():
                temp_path.unlink()
        
    except Exception as e:
        print(f"⚠️  Could not clean up temp files: {e}") 