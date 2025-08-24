"""
Metadata generation node using AI to create engaging titles, descriptions, and hashtags.
"""

import json
import time
from typing import Dict, List
import google.generativeai as genai

from ..models.state import PodcastState, ClipMetadata
from ..models.config import AppConfig


def generate_metadata_node(state: PodcastState) -> PodcastState:
    """
    LangGraph node to generate metadata for processed clips.
    
    This node:
    1. Uses AI to create engaging titles for each clip
    2. Generates descriptions optimized for social media
    3. Creates relevant hashtags
    4. Adds platform-specific optimizations
    """
    
    processed_clips = state.get("processed_clips", [])
    video_title = state.get("video_title", "Unknown Video")
    video_metadata = state.get("video_metadata", {})
    errors = state.get("errors", [])
    warnings = state.get("warnings", [])
    
    if not processed_clips:
        warning_msg = "No processed clips available for metadata generation"
        warnings.append(warning_msg)
        state["warnings"] = warnings
        state["metadata"] = []
        return state
    
    # Filter only successful clips
    successful_clips = [clip for clip in processed_clips if clip.get("success", False)]
    
    if not successful_clips:
        warning_msg = "No successful clips to generate metadata for"
        warnings.append(warning_msg)
        state["warnings"] = warnings
        state["metadata"] = []
        return state
    
    try:
        # Load configuration
        app_config = AppConfig.from_env()
        
        # Configure Gemini
        if not app_config.llm.api_key:
            raise Exception("Google API key not configured")
        
        genai.configure(api_key=app_config.llm.api_key)
        model = genai.GenerativeModel(app_config.llm.model_name)
        
        print(f"📝 Generating metadata for {len(successful_clips)} clips")
        
        generated_metadata = []
        total_metadata_time = 0
        
        for i, clip_data in enumerate(successful_clips, 1):
            try:
                start_time = time.time()
                
                # Get segment data
                segment_data = clip_data.get("segment_data", {})
                clip_reasoning = segment_data.get("reasoning", "")
                clip_type = segment_data.get("segment_type", "unknown")
                clip_score = segment_data.get("score", 0)
                clip_content = segment_data.get("content", "")
                
                print(f"📋 Generating metadata for clip {i}: {clip_type} (score: {clip_score})")
                
                # Create metadata prompt
                prompt = create_metadata_prompt(
                    clip_reasoning=clip_reasoning,
                    clip_type=clip_type,
                    clip_content=clip_content,
                    video_title=video_title,
                    video_uploader=video_metadata.get("uploader", "Unknown"),
                    clip_index=i
                )
                
                # Call Gemini
                response = model.generate_content(
                    prompt,
                    generation_config=genai.types.GenerationConfig(
                        temperature=0.8,  # Slightly higher for creative titles
                        max_output_tokens=800
                    )
                )
                
                metadata_time = time.time() - start_time
                total_metadata_time += metadata_time
                
                # Parse response
                metadata = parse_metadata_response(response.text, clip_data)
                
                if metadata:
                    generated_metadata.append(metadata.dict())
                    print(f"  ✅ Metadata generated in {metadata_time:.1f}s")
                    print(f"     Title: {metadata.title[:50]}...")
                else:
                    warnings.append(f"Failed to generate metadata for clip {i}")
                    print(f"  ⚠️  Failed to parse metadata response")
                
                # Rate limiting
                if i < len(successful_clips):
                    time.sleep(app_config.processing.api_rate_limit_delay)
                    
            except Exception as e:
                warning_msg = f"Failed to generate metadata for clip {i}: {str(e)}"
                warnings.append(warning_msg)
                print(f"  ❌ {warning_msg}")
                continue
        
        print(f"✅ Metadata generation completed in {total_metadata_time:.1f}s")
        print(f"📊 Generated metadata for {len(generated_metadata)}/{len(successful_clips)} clips")
        
        # Update state
        state["metadata"] = generated_metadata
        state["warnings"] = warnings
        state["status"] = "metadata_generated"
        
        return state
        
    except Exception as e:
        error_msg = f"Metadata generation failed: {str(e)}"
        print(f"❌ {error_msg}")
        
        errors.append(error_msg)
        state["errors"] = errors
        state["status"] = "failed"
        
        return state


def create_metadata_prompt(
    clip_reasoning: str,
    clip_type: str,
    clip_content: str,
    video_title: str,
    video_uploader: str,
    clip_index: int
) -> str:
    """Create a prompt for generating clip metadata."""
    
    prompt = f"""
You are an expert social media content creator specializing in viral short-form videos. Create compelling metadata for a {clip_type} clip extracted from a podcast.

CONTEXT:
- Original Video: "{video_title}" by {video_uploader}
- Clip Type: {clip_type}
- Clip Content/Hook: {clip_content}
- Selection Reasoning: {clip_reasoning}
- Clip Number: {clip_index}

TASK:
Generate metadata optimized for YouTube Shorts, Instagram Reels, and TikTok. Create content that will:
1. Hook viewers in the first 3 seconds
2. Encourage engagement and shares
3. Use trending formats and language
4. Appeal to the target audience for this content type

REQUIREMENTS:
- Title: 60 characters max, attention-grabbing, no clickbait
- Description: 2-3 sentences, engaging but authentic
- Hashtags: 8-12 relevant tags, mix of broad and niche
- Platform-specific optimizations

FORMAT YOUR RESPONSE AS JSON:
{{
  "title": "Compelling title that hooks viewers immediately",
  "description": "Brief but engaging description that provides context and encourages viewing",
  "hashtags": ["relevant", "trending", "hashtags", "for", "this", "content"],
  "platforms": {{
    "youtube": {{
      "title": "YouTube-optimized title (can be longer)",
      "description": "YouTube-specific description with context"
    }},
    "instagram": {{
      "caption": "Instagram-friendly caption with emojis",
      "hashtags": ["instagram", "specific", "tags"]
    }},
    "tiktok": {{
      "caption": "TikTok-style caption that drives engagement",
      "hashtags": ["tiktok", "trending", "tags"]
    }}
  }},
  "thumbnail_description": "Description of what makes a good thumbnail for this clip"
}}

TONE GUIDELINES:
- {clip_type} content should feel: {"educational and insightful" if clip_type == "insight" else "entertaining and engaging" if clip_type == "funny" else "thought-provoking and discussion-worthy" if clip_type == "controversial" else "inspiring and motivational" if clip_type == "inspirational" else "relatable and engaging"}
- Use language that resonates with the podcast's audience
- Avoid excessive capitalization or spam-like content
- Be authentic and genuine

Create metadata that will maximize engagement while staying true to the content!
"""
    
    return prompt


def parse_metadata_response(response_text: str, clip_data: Dict) -> ClipMetadata:
    """Parse the AI response and convert to ClipMetadata object."""
    
    try:
        # Clean up response text
        response_text = response_text.strip()
        
        # Find JSON content
        start_idx = response_text.find('{')
        end_idx = response_text.rfind('}') + 1
        
        if start_idx == -1 or end_idx == 0:
            print("⚠️  No JSON found in metadata response")
            return None
        
        json_text = response_text[start_idx:end_idx]
        data = json.loads(json_text)
        
        # Validate required fields
        required_fields = ["title", "description", "hashtags"]
        if not all(field in data for field in required_fields):
            print(f"⚠️  Missing required fields in metadata: {data}")
            return None
        
        # Get clip duration and thumbnail time
        segment_data = clip_data.get("segment_data", {})
        start_time = segment_data.get("start_time", 0)
        end_time = segment_data.get("end_time", 60)
        duration = end_time - start_time
        thumbnail_time = start_time + (duration / 2)  # Middle of clip
        
        # Create ClipMetadata object
        metadata = ClipMetadata(
            title=data["title"][:100],  # Ensure reasonable length
            description=data["description"][:500],  # Ensure reasonable length
            hashtags=data.get("hashtags", [])[:15],  # Limit hashtags
            thumbnail_time=thumbnail_time,
            duration=duration,
            platform_specific=data.get("platforms", {})
        )
        
        return metadata
        
    except json.JSONDecodeError as e:
        print(f"⚠️  JSON decode error in metadata: {e}")
        print(f"Response text: {response_text[:200]}...")
        return None
    except Exception as e:
        print(f"⚠️  Error parsing metadata response: {e}")
        return None


def create_fallback_metadata(clip_data: Dict, clip_index: int) -> ClipMetadata:
    """Create basic fallback metadata if AI generation fails."""
    
    segment_data = clip_data.get("segment_data", {})
    clip_type = segment_data.get("segment_type", "clip")
    start_time = segment_data.get("start_time", 0)
    end_time = segment_data.get("end_time", 60)
    duration = end_time - start_time
    
    # Basic metadata
    title = f"Interesting {clip_type.title()} Moment #{clip_index}"
    description = f"A compelling {duration:.0f}-second {clip_type} from this podcast episode."
    hashtags = ["podcast", "shorts", clip_type, "viral", "content"]
    
    return ClipMetadata(
        title=title,
        description=description,
        hashtags=hashtags,
        thumbnail_time=start_time + (duration / 2),
        duration=duration,
        platform_specific={}
    ) 