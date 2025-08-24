"""
Content analysis node using single-pass full transcript analysis.
"""

import time
import json
import re
from typing import List, Dict, Any
import google.generativeai as genai

from ..models.state import PodcastState, VideoSegment
from ..models.config import AppConfig
from ..utils.transcript import clean_transcript_text


def analyze_content_node(state: PodcastState) -> PodcastState:
    """
    LangGraph node to analyze the complete transcript and identify the best clip segments.
    
    This node:
    1. Takes the entire transcript as input
    2. Sends it to LLM in a single API call
    3. Gets back the 3 best segments with timestamps
    4. Much faster and more accurate than chunked analysis
    """
    
    transcript_text = state.get("transcript")
    transcript_segments = state.get("transcript_segments", [])
    video_title = state.get("video_title", "Unknown Video")
    video_duration = state.get("video_duration", 0)
    errors = state.get("errors", [])
    warnings = state.get("warnings", [])
    
    if not transcript_text or not transcript_segments:
        error_msg = "No transcript available for analysis"
        errors.append(error_msg)
        state["errors"] = errors
        return state
    
    try:
        # Load configuration
        app_config = AppConfig.from_env()
        
        # Apply custom configuration overrides from state
        custom_config = state.get("config", {})
        if custom_config:
            print(f"🔧 Using custom configuration: {custom_config}")
            # Override specific values if provided
            if "max_clips_per_video" in custom_config:
                app_config.processing.max_clips_per_video = custom_config["max_clips_per_video"]
            if "target_clip_duration" in custom_config:
                app_config.processing.target_clip_duration = custom_config["target_clip_duration"]
            if "min_clip_duration" in custom_config:
                app_config.processing.min_clip_duration = custom_config["min_clip_duration"]
            if "max_clip_duration" in custom_config:
                app_config.processing.max_clip_duration = custom_config["max_clip_duration"]
        
        # Configure Gemini
        if not app_config.llm.api_key:
            raise Exception("Google API key not configured")
        
        genai.configure(api_key=app_config.llm.api_key)
        model = genai.GenerativeModel(app_config.llm.model_name)
        
        # Clean the transcript
        clean_text = clean_transcript_text(transcript_text)
        
        print(f"📊 Analyzing complete transcript ({len(clean_text)} characters)")
        print(f"🎥 Video: {video_title}")
        print(f"⏱️  Duration: {video_duration/60:.1f} minutes")
        print(f"🎯 Target: {app_config.processing.max_clips_per_video} clips ({app_config.processing.target_clip_duration}s each)")
        
        # Create the full transcript analysis prompt
        prompt = create_full_transcript_prompt(
            transcript_text=clean_text,
            video_title=video_title,
            video_duration=video_duration,
            target_clips=app_config.processing.max_clips_per_video,
            target_duration=app_config.processing.target_clip_duration
        )
        
        # Single API call to analyze the entire transcript
        start_time = time.time()
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=app_config.llm.temperature
            )
        )
        analysis_time = time.time() - start_time
        
        print(f"✅ Analysis completed in {analysis_time:.2f}s (single API call)")
        
        # Parse the response to extract clip segments
        identified_clips = parse_full_transcript_response(response.text, transcript_segments)
        
        print(f"🎬 Identified {len(identified_clips)} high-quality clips")
        
        # Display the identified clips
        for i, clip in enumerate(identified_clips, 1):
            duration = clip.end_time - clip.start_time
            print(f"  🎯 Clip {i}: {clip.start_time:.1f}s-{clip.end_time:.1f}s "
                  f"({duration:.1f}s, score: {clip.score:.1f}, type: {clip.segment_type})")
            print(f"      Reasoning: {clip.reasoning[:100]}...")
        
        # Convert clips to dictionaries for JSON serialization
        clips_dict = [clip.dict() for clip in identified_clips]
        
        # Update state
        state["identified_clips"] = clips_dict
        state["status"] = "clips_identified"
        
        print(f"🎉 Single-pass analysis complete - found the best moments from the entire video!")
        
    except Exception as e:
        error_msg = f"Content analysis failed: {str(e)}"
        errors.append(error_msg)
        print(f"❌ {error_msg}")
        state["errors"] = errors
        state["status"] = "analysis_failed"
    
    return state


def create_full_transcript_prompt(
    transcript_text: str,
    video_title: str,
    video_duration: float,
    target_clips: int,
    target_duration: float
) -> str:
    """Create a prompt for analyzing the complete transcript."""
    
    duration_minutes = video_duration / 60
    
    prompt = f"""
You are an expert content creator specializing in viral short-form videos for YouTube Shorts, Instagram Reels, and TikTok. You have the COMPLETE transcript of a {duration_minutes:.1f}-minute video and need to find the {target_clips} absolute BEST segments for viral clips.

VIDEO CONTEXT:
- Title: "{video_title}"
- Duration: {duration_minutes:.1f} minutes
- Target: {target_clips} clips of ~{target_duration} seconds each

YOUR TASK:
Analyze the ENTIRE transcript below and identify the {target_clips} most engaging segments that would work best as standalone viral clips. You have the full context, so find the true peaks of engagement across the whole video.

SELECTION CRITERIA (in order of importance):
1. **Viral Potential**: Content that naturally hooks viewers and encourages shares
2. **Standalone Value**: Segments that work perfectly without additional context  
3. **Emotional Impact**: Moments that evoke strong reactions (surprise, insight, humor, inspiration)
4. **Actionable Content**: Practical advice viewers can immediately apply
5. **Story/Example**: Compelling narratives or case studies
6. **Controversial/Counterintuitive**: Ideas that challenge conventional wisdom
7. **Quote-worthy**: Memorable phrases that people would want to share

CONTENT TYPES TO PRIORITIZE:
- Key insights or "aha moments"
- Practical actionable advice
- Surprising facts or revelations
- Compelling stories or examples
- Strong opinions or controversial takes
- Motivational or inspirational moments
- Funny or entertaining segments

AVOID:
- Introductory content or setup
- Transitions between topics
- Basic explanations without payoff
- Repetitive content
- Technical jargon without clear benefit
- Conclusion/summary segments

TRANSCRIPT TO ANALYZE:

{transcript_text}

RESPONSE FORMAT:
Return EXACTLY {target_clips} segments in JSON format. Each segment must be exactly {target_duration} seconds long and represent the absolute best moments from the entire video:

{{
  "clips": [
    {{
      "start_time": 1234.5,
      "end_time": 1264.5,
      "score": 9.5,
      "segment_type": "actionable|insight|story|funny|controversial|inspirational",
      "reasoning": "Detailed explanation of why this specific segment is viral-worthy and engaging",
      "content_summary": "Brief summary of what happens in this segment",
      "hook_factor": "Why this segment would hook viewers in the first 3 seconds"
    }}
  ]
}}

IMPORTANT:
- Use the FULL transcript context to find the very best moments
- Ensure segments are spaced throughout the video (avoid clustering)
- Each segment must be EXACTLY {target_duration} seconds
- Scores should be 8.0+ (only the most engaging content)
- Provide detailed reasoning for each selection
- Make sure segments work as standalone clips

Find the absolute gems in this content!
"""
    
    return prompt


def parse_full_transcript_response(response_text: str, transcript_segments: List[Dict]) -> List[VideoSegment]:
    """Parse the LLM response and convert to VideoSegment objects."""
    
    clips = []
    
    try:
        # Clean the response text and extract JSON
        cleaned_response = response_text.strip()
        
        # Handle markdown code blocks
        if "```json" in cleaned_response:
            json_start = cleaned_response.find("```json") + 7
            json_end = cleaned_response.find("```", json_start)
            if json_end == -1:
                json_end = len(cleaned_response)
            cleaned_response = cleaned_response[json_start:json_end].strip()
        elif "```" in cleaned_response:
            json_start = cleaned_response.find("```") + 3
            json_end = cleaned_response.find("```", json_start)
            if json_end == -1:
                json_end = len(cleaned_response)
            cleaned_response = cleaned_response[json_start:json_end].strip()
        
        # Parse JSON
        try:
            data = json.loads(cleaned_response)
        except json.JSONDecodeError:
            # Try to extract JSON from text if direct parsing fails
            json_match = re.search(r'\{.*\}', cleaned_response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
            else:
                raise ValueError("No valid JSON found in response")
        
        # Extract clips from the response
        clips_data = data.get("clips", [])
        
        for clip_data in clips_data:
            try:
                # Extract the relevant transcript segment for this time range
                start_time = float(clip_data["start_time"])
                end_time = float(clip_data["end_time"])
                
                # Find matching transcript segments
                segment_text = extract_segment_text(transcript_segments, start_time, end_time)
                
                clip = VideoSegment(
                    start_time=start_time,
                    end_time=end_time,
                    content=segment_text,
                    score=float(clip_data.get("score", 8.0)),
                    reasoning=clip_data.get("reasoning", ""),
                    segment_type=clip_data.get("segment_type", "unknown"),
                    engagement_factors=clip_data.get("hook_factor", ""),
                    transcript_segments=get_segment_range(transcript_segments, start_time, end_time)
                )
                
                clips.append(clip)
                
            except (ValueError, KeyError) as e:
                print(f"⚠️  Warning: Failed to parse clip data: {e}")
                continue
                
    except Exception as e:
        print(f"⚠️  Warning: Failed to parse LLM response: {e}")
        print(f"Response text: {response_text[:500]}...")
    
    return clips


def extract_segment_text(transcript_segments: List[Dict], start_time: float, end_time: float) -> str:
    """Extract the text content for a specific time range."""
    
    relevant_text = []
    
    for segment in transcript_segments:
        seg_start = segment.get("start", 0)
        seg_end = seg_start + segment.get("duration", 0)
        
        # Check if segment overlaps with our target range
        if seg_end >= start_time and seg_start <= end_time:
            relevant_text.append(segment.get("text", ""))
    
    return " ".join(relevant_text).strip()


def get_segment_range(transcript_segments: List[Dict], start_time: float, end_time: float) -> List[Dict]:
    """Get all transcript segments that fall within the time range."""
    
    relevant_segments = []
    
    for segment in transcript_segments:
        seg_start = segment.get("start", 0)
        seg_end = seg_start + segment.get("duration", 0)
        
        # Check if segment overlaps with our target range
        if seg_end >= start_time and seg_start <= end_time:
            relevant_segments.append(segment)
    
    return relevant_segments 