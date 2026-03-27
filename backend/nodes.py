"""
All LangGraph processing nodes and utility functions, consolidated into a single module.
Covers: transcript, analysis, selection, video download, clip generation, and metadata.
"""

import json
import os
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import google.generativeai as genai
import yt_dlp
from moviepy import ColorClip, CompositeVideoClip, VideoFileClip
from youtube_transcript_api import YouTubeTranscriptApi
import imageio_ffmpeg
os.environ["IMAGEIO_FFMPEG_EXE"] = imageio_ffmpeg.get_ffmpeg_exe()
from .models import (
    AppConfig,
    ClipMetadata,
    PodcastState,
    ProcessingResult,
    TranscriptSegment,
    VideoSegment,
)


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def extract_video_id(url: str) -> str:
    """Extract YouTube video ID from a URL (or return the input if already an ID)."""
    patterns = [
        r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([^&\n?#]+)',
        r'youtube\.com/watch\?.*v=([^&\n?#]+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return url


def sanitize_filename(filename: str) -> str:
    """Remove invalid filesystem characters from a filename."""
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    filename = filename.strip(' .')
    return filename[:200]


def clean_transcript_text(text: str) -> str:
    """Remove music notation, speaker labels, and extra whitespace from transcript."""
    text = re.sub(r'\[♪♪♪\]', '', text)
    text = re.sub(r'♪[^♪]*♪', '', text)
    text = re.sub(r'^\s*[A-Z][A-Z\s]+:', '', text, flags=re.MULTILINE)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


# ---------------------------------------------------------------------------
# Transcript node
# ---------------------------------------------------------------------------

def fetch_transcript_node(state: PodcastState) -> PodcastState:
    """Fetch YouTube transcript and video metadata, then update the workflow state."""

    url = state["url"]
    errors = state.get("errors", [])
    warnings = state.get("warnings", [])

    try:
        video_id = extract_video_id(url)
        print(f"Fetching transcript for video: {video_id}")

        # --- Video metadata (via yt-dlp — pytube/YoutubeLoader is no longer reliable) ---
        try:
            with yt_dlp.YoutubeDL({
                'quiet': True,
                'no_warnings': True,
                'extractor_args': {'youtube': {'player_client': ['android', 'mweb']}},
            }) as ydl:
                info = ydl.extract_info(url, download=False)
            state["video_title"] = info.get("title", "Unknown Title")
            state["video_duration"] = float(info.get("duration", 0) or 0)
            state["video_id"] = video_id
            print(f"Video: {state['video_title']} ({state['video_duration']}s)")
        except Exception as e:
            warnings.append(f"Could not fetch video metadata: {e}")
            state["video_title"] = "Unknown Title"
            state["video_duration"] = 0.0
            state["video_id"] = video_id

        # --- Transcript ---
        t0 = time.time()
        full_transcript, segments, source = _fetch_youtube_transcript(url)
        print(f"Transcript fetched in {time.time() - t0:.2f}s from {source}")
        print(f"Length: {len(full_transcript)} chars, {len(segments)} segments")

        state["transcript"] = full_transcript
        state["transcript_segments"] = [s.model_dump() for s in segments]
        state["transcript_source"] = source
        state["status"] = "transcript_fetched"

        if state.get("created_at") is None:
            state["created_at"] = datetime.now().isoformat()

        return state

    except Exception as e:
        msg = f"Failed to fetch transcript: {e}"
        print(f"ERROR: {msg}")
        errors.append(msg)
        state["errors"] = errors
        state["status"] = "failed"
        return state


def _fetch_youtube_transcript(url: str) -> Tuple[str, List[TranscriptSegment], str]:
    """Internal helper to call YouTube Transcript API."""
    video_id = extract_video_id(url)
    api = YouTubeTranscriptApi()
    transcript_list = api.list(video_id)

    transcript = None
    source = "youtube_manual"

    try:
        transcript = transcript_list.find_manually_created_transcript(['en'])
        source = "youtube_manual"
    except Exception:
        try:
            transcript = transcript_list.find_generated_transcript(['en'])
            source = "youtube_auto"
        except Exception:
            pass

    if transcript is None:
        for t in transcript_list:
            if t.language_code.startswith('en'):
                transcript = t
                source = "youtube_auto" if t.is_generated else "youtube_manual"
                break

    if transcript is None:
        raise Exception("No English transcript available for this video")

    data = transcript.fetch()
    if not data:
        raise Exception("Transcript data is empty")

    segments: List[TranscriptSegment] = []
    parts: List[str] = []
    for item in data:
        segments.append(TranscriptSegment(
            start_time=float(item.start),
            end_time=float(item.start) + float(item.duration),
            text=item.text.strip(),
            confidence=0.95,
        ))
        parts.append(item.text.strip())

    full_transcript = " ".join(parts)
    if len(full_transcript.strip()) < 50:
        raise Exception("Transcript is too short or empty")

    return full_transcript, segments, source


# ---------------------------------------------------------------------------
# Analysis node
# ---------------------------------------------------------------------------

def analyze_content_node(state: PodcastState) -> PodcastState:
    """Send the complete transcript to Gemini in a single call and identify the best clips."""

    transcript_text = state.get("transcript")
    transcript_segments = state.get("transcript_segments", [])
    video_title = state.get("video_title", "Unknown Video")
    video_duration = state.get("video_duration", 0)
    errors = state.get("errors", [])
    warnings = state.get("warnings", [])

    if not transcript_text or not transcript_segments:
        errors.append("No transcript available for analysis")
        state["errors"] = errors
        return state

    try:
        app_config = AppConfig.from_env()
        custom_config = state.get("config", {})

        max_clips = custom_config.get("max_clips_per_video", 3)
        target_duration = custom_config.get("target_clip_duration", 30)

        print(f"Analysis config — clips: {max_clips}, target duration: {target_duration}s")

        if not app_config.llm.api_key:
            raise Exception("Google API key not configured")

        genai.configure(api_key=app_config.llm.api_key)
        model = genai.GenerativeModel(app_config.llm.model_name)

        clean_text = clean_transcript_text(transcript_text)
        print(f"Analyzing transcript ({len(clean_text)} chars) for {video_title}")

        prompt = _build_analysis_prompt(clean_text, video_title, video_duration, max_clips, target_duration)

        t0 = time.time()
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(temperature=app_config.llm.temperature),
        )
        print(f"Analysis completed in {time.time() - t0:.2f}s")

        identified_clips = _parse_analysis_response(response.text, transcript_segments)
        print(f"Identified {len(identified_clips)} clips")

        state["identified_clips"] = [c.model_dump() for c in identified_clips]
        state["status"] = "clips_identified"

    except Exception as e:
        msg = f"Content analysis failed: {e}"
        errors.append(msg)
        print(f"ERROR: {msg}")
        state["errors"] = errors
        state["status"] = "analysis_failed"

    return state


def _build_analysis_prompt(
    transcript_text: str,
    video_title: str,
    video_duration: float,
    target_clips: int,
    target_duration: float,
) -> str:
    duration_minutes = video_duration / 60
    return f"""
You are an expert content creator specialising in viral short-form videos for YouTube Shorts, Instagram Reels, and TikTok. You have the COMPLETE transcript of a {duration_minutes:.1f}-minute video and must find the {target_clips} absolute BEST segments for viral clips.

VIDEO CONTEXT:
- Title: "{video_title}"
- Duration: {duration_minutes:.1f} minutes
- Target: {target_clips} clips of ~{target_duration} seconds each

TASK:
Analyse the ENTIRE transcript below and identify the {target_clips} most engaging segments that work best as standalone viral clips. Use the full context to find true peaks of engagement across the whole video.

SELECTION CRITERIA (in priority order):
1. Viral Potential — naturally hooks viewers and encourages shares
2. Standalone Value — works without additional context
3. Emotional Impact — surprise, insight, humour, or inspiration
4. Actionable Content — practical advice viewers can immediately apply
5. Compelling narrative or counterintuitive idea
6. Quote-worthy — memorable phrases people would share

AVOID: introductions, transitions, basic explanations, repetitive content, summaries.

TRANSCRIPT:
{transcript_text}

RESPONSE FORMAT — return EXACTLY {target_clips} segments as JSON:
{{
  "clips": [
    {{
      "start_time": 1234.5,
      "end_time": 1264.5,
      "score": 9.5,
      "segment_type": "actionable|insight|story|funny|controversial|inspirational",
      "reasoning": "Detailed explanation of why this is viral-worthy",
      "content_summary": "Brief summary of the segment",
      "hook_factor": "Why this hooks viewers in the first 3 seconds"
    }}
  ]
}}

RULES:
- Each segment must be EXACTLY {target_duration} seconds long
- Scores should be 8.0+ (only the most engaging content)
- Spread segments throughout the video — avoid clustering
- Segments must work as standalone clips
"""


def _parse_analysis_response(response_text: str, transcript_segments: List[Dict]) -> List[VideoSegment]:
    """Parse the Gemini JSON response into VideoSegment objects."""
    clips: List[VideoSegment] = []

    try:
        cleaned = response_text.strip()

        # Strip markdown code fences
        if "```json" in cleaned:
            start = cleaned.find("```json") + 7
            end = cleaned.find("```", start)
            cleaned = cleaned[start:end if end != -1 else len(cleaned)].strip()
        elif "```" in cleaned:
            start = cleaned.find("```") + 3
            end = cleaned.find("```", start)
            cleaned = cleaned[start:end if end != -1 else len(cleaned)].strip()

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            data = _repair_json(cleaned)

        for clip_data in data.get("clips", []):
            try:
                start_time = float(clip_data["start_time"])
                end_time = float(clip_data["end_time"])
                segment_text = _extract_segment_text(transcript_segments, start_time, end_time)
                segment_range = _get_segment_range(transcript_segments, start_time, end_time)

                clips.append(VideoSegment(
                    start_time=start_time,
                    end_time=end_time,
                    content=segment_text,
                    score=float(clip_data.get("score", 8.0)),
                    reasoning=clip_data.get("reasoning", ""),
                    segment_type=clip_data.get("segment_type", "unknown"),
                    engagement_factors=clip_data.get("hook_factor", ""),
                    transcript_segments=segment_range,
                ))
            except (ValueError, KeyError) as e:
                print(f"Warning: skipping clip — {e}")

    except Exception as e:
        print(f"Warning: failed to parse LLM response — {e}")
        print(f"Response preview: {response_text[:300]}...")

    return clips


def _repair_json(text: str) -> dict:
    """Best-effort repair of truncated JSON by collecting complete clip objects."""
    if '"clips": [' not in text:
        raise ValueError("No clips array found in response")

    clips_start = text.find('"clips": [') + 10
    clips_part = text[clips_start:]

    complete_clips = []
    current = ""
    depth = 0
    in_string = False
    escape_next = False

    for char in clips_part:
        if escape_next:
            escape_next = False
            current += char
            continue
        if char == '\\':
            escape_next = True
            current += char
            continue
        if char == '"' and not escape_next:
            in_string = not in_string
        if not in_string:
            if char == '{':
                depth += 1
            elif char == '}':
                depth -= 1
        current += char
        if depth == 0 and current.strip().endswith('}'):
            complete_clips.append(current.strip().rstrip(','))
            current = ""

    if not complete_clips:
        raise ValueError("Could not repair JSON — no complete clip objects found")

    repaired = f'{{"clips": [{", ".join(complete_clips)}]}}'
    return json.loads(repaired)


def _extract_segment_text(segments: List[Dict], start: float, end: float) -> str:
    parts = []
    for seg in segments:
        seg_start = seg.get("start_time", seg.get("start", 0))
        seg_end = seg.get("end_time", seg_start + seg.get("duration", 0))
        if seg_end >= start and seg_start <= end:
            parts.append(seg.get("text", ""))
    return " ".join(parts).strip()


def _get_segment_range(segments: List[Dict], start: float, end: float) -> List[Dict]:
    result = []
    for seg in segments:
        seg_start = seg.get("start_time", seg.get("start", 0))
        seg_end = seg.get("end_time", seg_start + seg.get("duration", 0))
        if seg_end >= start and seg_start <= end:
            result.append(seg)
    return result


# ---------------------------------------------------------------------------
# Selection node
# ---------------------------------------------------------------------------

def select_clips_node(state: PodcastState) -> PodcastState:
    """Validate identified clips and select the final set."""

    identified_clips = state.get("identified_clips", [])
    errors = state.get("errors", [])
    warnings = state.get("warnings", [])

    if not identified_clips:
        warnings.append("No clips identified by analysis")
        state["warnings"] = warnings
        state["selected_clips"] = []
        state["status"] = "no_clips_identified"
        return state

    try:
        app_config = AppConfig.from_env()
        custom_config = state.get("config", {})

        max_clips = custom_config.get("max_clips_per_video", 3)
        target_duration = custom_config.get("target_clip_duration", 30)
        min_duration = max(10, target_duration - 10)
        max_duration = target_duration + 15
        min_score = app_config.processing.min_engagement_score

        print(f"Selection config — clips: {max_clips}, duration range: {min_duration}-{max_duration}s, min score: {min_score}")

        clips = [VideoSegment(**c) for c in identified_clips]
        validated: List[VideoSegment] = []

        for clip in clips:
            duration = clip.end_time - clip.start_time
            if duration < min_duration:
                print(f"  Skipping {clip.start_time:.1f}s-{clip.end_time:.1f}s: too short ({duration:.1f}s)")
                continue
            if duration > max_duration:
                print(f"  Skipping {clip.start_time:.1f}s-{clip.end_time:.1f}s: too long ({duration:.1f}s)")
                continue
            if clip.score < min_score:
                print(f"  Skipping {clip.start_time:.1f}s-{clip.end_time:.1f}s: low score ({clip.score:.1f})")
                continue
            validated.append(clip)

        if not validated:
            warnings.append("No clips passed validation criteria")
            state["warnings"] = warnings
            state["selected_clips"] = []
            state["status"] = "no_clips_passed_validation"
            return state

        validated.sort(key=lambda x: x.score, reverse=True)
        selected = validated[:max_clips]

        print(f"Selected {len(selected)} clips from {len(validated)} validated")

        state["selected_clips"] = [c.model_dump() for c in selected]
        state["status"] = "clips_selected"
        state["warnings"] = warnings

    except Exception as e:
        msg = f"Clip selection failed: {e}"
        errors.append(msg)
        print(f"ERROR: {msg}")
        state["errors"] = errors
        state["status"] = "selection_failed"

    return state


# ---------------------------------------------------------------------------
# Video download node
# ---------------------------------------------------------------------------

def download_video_node(state: PodcastState) -> PodcastState:
    """Download the YouTube video using yt-dlp."""

    url = state["url"]
    video_id = state.get("video_id") or extract_video_id(url)
    errors = state.get("errors", [])
    warnings = state.get("warnings", [])
    state["video_id"] = video_id

    try:
        app_config = AppConfig.from_env()

        output_dir = Path(app_config.output_directory) / video_id
        output_dir.mkdir(parents=True, exist_ok=True)
        temp_dir = Path(app_config.temp_directory)
        temp_dir.mkdir(parents=True, exist_ok=True)

        video_output_template = str(temp_dir / f"{video_id}.%(ext)s")

        ydl_opts = {
            # android client reliably bypasses DRM and SABR streaming restrictions
            # that YouTube started enforcing on tv/web clients in late 2025
            'extractor_args': {'youtube': {'player_client': ['android', 'mweb']}},
            'format': (
                'bestvideo[height>=720][ext=mp4]+bestaudio[ext=m4a]'
                '/bestvideo[height>=480][ext=mp4]+bestaudio[ext=m4a]'
                '/bestvideo+bestaudio/best'
            ),
            'outtmpl': video_output_template,
            'noplaylist': True,
            'merge_output_format': 'mp4',
            'prefer_ffmpeg': True,
            'writeinfojson': True,
            'writethumbnail': True,
        }

        print(f"Downloading video: {video_id}")
        t0 = time.time()
        actual_path = None

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            duration = info.get('duration', 0)

            if duration > app_config.processing.max_video_duration:
                msg = (
                    f"Video is {duration/3600:.1f}h "
                    f"(>{app_config.processing.max_video_duration/3600:.1f}h limit). "
                    "Processing may be slow."
                )
                warnings.append(msg)
                print(f"WARNING: {msg}")

            print(f"Video: {info.get('title')} ({duration//60}:{duration%60:02d})")
            ydl.download([url])

            for ext in ['mp4', 'webm', 'mkv']:
                candidate = temp_dir / f"{video_id}.{ext}"
                if candidate.exists():
                    actual_path = str(candidate)
                    break

        if not actual_path or not os.path.exists(actual_path) or os.path.getsize(actual_path) == 0:
            raise Exception("Video download failed or file is empty")

        size_mb = os.path.getsize(actual_path) / (1024 * 1024)
        print(f"Downloaded in {time.time() - t0:.1f}s ({size_mb:.1f} MB)")

        state["video_path"] = actual_path
        state["video_title"] = info.get('title', state.get("video_title", "Unknown Title"))
        state["video_duration"] = float(info.get('duration', state.get("video_duration", 0)))
        state["warnings"] = warnings
        state["status"] = "video_downloaded"

    except Exception as e:
        msg = f"Video download failed: {e}"
        print(f"ERROR: {msg}")
        errors.append(msg)
        state["errors"] = errors
        state["status"] = "failed"

    return state


# ---------------------------------------------------------------------------
# Clip generation node
# ---------------------------------------------------------------------------

def generate_clips_node(state: PodcastState) -> PodcastState:
    """Cut the video into clip files and generate thumbnails using MoviePy."""

    video_path = state.get("video_path")
    selected_clips = state.get("selected_clips", [])
    video_id = state.get("video_id")
    errors = state.get("errors", [])
    warnings = state.get("warnings", [])

    if not video_path or not os.path.exists(video_path):
        errors.append("No video file available for clip generation")
        state["errors"] = errors
        return state

    if not selected_clips:
        warnings.append("No clips selected for generation")
        state["warnings"] = warnings
        state["processed_clips"] = []
        state["status"] = "no_clips_to_generate"
        return state

    try:
        app_config = AppConfig.from_env()
        custom_config = state.get("config", {})

        # Apply custom overrides
        if "max_clips_per_video" in custom_config:
            app_config.processing.max_clips_per_video = custom_config["max_clips_per_video"]
        if "target_clip_duration" in custom_config:
            app_config.processing.target_clip_duration = custom_config["target_clip_duration"]
        if "min_clip_duration" in custom_config:
            app_config.processing.min_clip_duration = custom_config["min_clip_duration"]
        if "max_clip_duration" in custom_config:
            app_config.processing.max_clip_duration = custom_config["max_clip_duration"]

        output_dir = Path(app_config.output_directory) / video_id
        clips_dir = output_dir / "clips"
        thumbnails_dir = output_dir / "thumbnails"
        clips_dir.mkdir(parents=True, exist_ok=True)
        thumbnails_dir.mkdir(parents=True, exist_ok=True)

        print(f"Generating {len(selected_clips)} clips from {video_path}")
        main_video = VideoFileClip(video_path)
        processed_clips = []
        total_time = 0.0

        for i, clip_data in enumerate(selected_clips, 1):
            t0 = time.time()
            clip = VideoSegment(**clip_data)

            try:
                print(f"  Clip {i}/{len(selected_clips)}: {clip.start_time:.1f}s–{clip.end_time:.1f}s")
                segment = main_video.subclipped(clip.start_time, clip.end_time)

                if app_config.video.aspect_ratio == "original":
                    final = segment
                else:
                    final = _convert_to_portrait(segment, app_config.video.resolution)

                clip_title = sanitize_filename(f"clip_{i:02d}_{clip.segment_type}")
                clip_filename = f"{clip_title}.mp4"
                clip_path = clips_dir / clip_filename

                # Write video file; temp audio lands in the clips dir to avoid polluting root
                temp_audio = str(clips_dir / "temp-audio.m4a")
                final.write_videofile(
                    str(clip_path),
                    codec=app_config.video.codec,
                    audio_codec='aac',
                    temp_audiofile=temp_audio,
                    remove_temp=True,
                    fps=app_config.video.fps,
                    bitrate=app_config.video.bitrate,
                    preset='faster',
                    ffmpeg_params=[
                        '-movflags', '+faststart',
                        '-profile:v', 'main',
                        '-level', '4.0',
                        '-pix_fmt', 'yuv420p',
                        '-g', '30',
                    ],
                )

                thumbnail_path = _generate_thumbnail(final, thumbnails_dir, clip_title)

                if final is not segment:
                    final.close()
                segment.close()

                elapsed = time.time() - t0
                total_time += elapsed
                size_mb = os.path.getsize(clip_path) / (1024 * 1024)

                result = ProcessingResult(
                    success=True,
                    output_path=str(clip_path),
                    processing_time=elapsed,
                )

                processed_clips.append({
                    **result.model_dump(),
                    "clip_index": i,
                    "segment_data": clip.model_dump(),
                    "file_size_mb": size_mb,
                    "thumbnail_path": str(thumbnail_path),
                    "filename": clip_filename,
                })
                print(f"    Done in {elapsed:.1f}s ({size_mb:.1f} MB)")

            except Exception as e:
                msg = f"Failed to generate clip {i}: {e}"
                print(f"    ERROR: {msg}")
                warnings.append(msg)
                elapsed = time.time() - t0
                processed_clips.append({
                    **ProcessingResult(success=False, errors=[msg], processing_time=elapsed).model_dump(),
                    "clip_index": i,
                    "segment_data": clip_data,
                    "filename": f"failed_clip_{i}.mp4",
                })

        main_video.close()
        print(f"Clip generation finished in {total_time:.1f}s total")

        successful = [c for c in processed_clips if c["success"]]
        print(f"Results: {len(successful)} succeeded, {len(processed_clips) - len(successful)} failed")

        state["processed_clips"] = processed_clips
        state["warnings"] = warnings
        state["status"] = "clips_generated" if successful else "clip_generation_failed"

    except Exception as e:
        msg = f"Clip generation failed: {e}"
        print(f"ERROR: {msg}")
        errors.append(msg)
        state["errors"] = errors
        state["status"] = "failed"

    return state


def _convert_to_portrait(clip: VideoFileClip, target_resolution: tuple) -> VideoFileClip:
    """Crop / pad a clip to portrait (9:16) format."""
    tw, th = target_resolution
    cw, ch = clip.size
    target_ar = tw / th
    current_ar = cw / ch

    if abs(current_ar - target_ar) < 0.01:
        return clip.resized((tw, th))

    if current_ar > target_ar:
        optimal_h = cw / target_ar
        if optimal_h <= ch:
            yc = ch / 2
            y1 = max(0, yc - optimal_h / 2)
            y2 = min(ch, y1 + optimal_h)
            return clip.cropped(y1=y1, y2=y2).resized((tw, th))
        else:
            scale = th / ch
            nw = int(cw * scale)
            resized = clip.resized((nw, th))
            bg = ColorClip(size=(tw, th), color=(0, 0, 0)).with_duration(clip.duration)
            x_off = (tw - nw) // 2
            return CompositeVideoClip([bg, resized.with_position((x_off, 0))])
    else:
        optimal_w = ch * target_ar
        if optimal_w <= cw:
            xc = cw / 2
            x1 = max(0, xc - optimal_w / 2)
            x2 = min(cw, x1 + optimal_w)
            return clip.cropped(x1=x1, x2=x2).resized((tw, th))
        else:
            scale = tw / cw
            nh = int(ch * scale)
            resized = clip.resized((tw, nh))
            bg = ColorClip(size=(tw, th), color=(0, 0, 0)).with_duration(clip.duration)
            y_off = (th - nh) // 2
            return CompositeVideoClip([bg, resized.with_position((0, y_off))])


def _generate_thumbnail(clip: VideoFileClip, thumbnails_dir: Path, clip_title: str) -> Path:
    thumbnail_path = thumbnails_dir / f"{clip_title}_thumb.jpg"
    clip.save_frame(str(thumbnail_path), t=clip.duration / 2)
    return thumbnail_path


# ---------------------------------------------------------------------------
# Metadata generation node
# ---------------------------------------------------------------------------

def generate_metadata_node(state: PodcastState) -> PodcastState:
    """Use Gemini to create engaging titles, descriptions, and hashtags for each clip."""

    processed_clips = state.get("processed_clips", [])
    video_title = state.get("video_title", "Unknown Video")
    errors = state.get("errors", [])
    warnings = state.get("warnings", [])

    successful_clips = [c for c in processed_clips if c.get("success", False)]

    if not successful_clips:
        warnings.append("No successful clips to generate metadata for")
        state["warnings"] = warnings
        state["metadata"] = []
        return state

    try:
        app_config = AppConfig.from_env()

        if not app_config.llm.api_key:
            raise Exception("Google API key not configured")

        genai.configure(api_key=app_config.llm.api_key)
        model = genai.GenerativeModel(app_config.llm.model_name)

        print(f"Generating metadata for {len(successful_clips)} clips")
        generated: List[Dict] = []
        total_time = 0.0

        for i, clip_data in enumerate(successful_clips, 1):
            try:
                t0 = time.time()
                seg = clip_data.get("segment_data", {})
                prompt = _build_metadata_prompt(
                    clip_reasoning=seg.get("reasoning", ""),
                    clip_type=seg.get("segment_type", "unknown"),
                    clip_content=seg.get("content", ""),
                    video_title=video_title,
                    clip_index=i,
                )

                response = model.generate_content(
                    prompt,
                    generation_config=genai.types.GenerationConfig(
                        temperature=0.8,
                        max_output_tokens=800,
                    ),
                )

                elapsed = time.time() - t0
                total_time += elapsed
                metadata = _parse_metadata_response(response.text, clip_data)

                if metadata:
                    generated.append(metadata.model_dump())
                    print(f"  Clip {i}: metadata ready in {elapsed:.1f}s — {metadata.title[:60]}")
                else:
                    warnings.append(f"Failed to parse metadata for clip {i}")

                if i < len(successful_clips):
                    time.sleep(app_config.processing.api_rate_limit_delay)

            except Exception as e:
                msg = f"Metadata error for clip {i}: {e}"
                warnings.append(msg)
                print(f"  WARNING: {msg}")

        print(f"Metadata generation done in {total_time:.1f}s — {len(generated)}/{len(successful_clips)} clips")
        state["metadata"] = generated
        state["warnings"] = warnings
        state["status"] = "metadata_generated"

    except Exception as e:
        msg = f"Metadata generation failed: {e}"
        print(f"ERROR: {msg}")
        errors.append(msg)
        state["errors"] = errors
        state["status"] = "failed"

    return state


def _build_metadata_prompt(
    clip_reasoning: str,
    clip_type: str,
    clip_content: str,
    video_title: str,
    clip_index: int,
) -> str:
    tone_map = {
        "insight": "educational and insightful",
        "funny": "entertaining and engaging",
        "controversial": "thought-provoking and discussion-worthy",
        "inspirational": "inspiring and motivational",
    }
    tone = tone_map.get(clip_type, "relatable and engaging")

    return f"""
You are an expert social media content creator. Create compelling metadata for a {clip_type} clip from a podcast.

CONTEXT:
- Original video: "{video_title}"
- Clip type: {clip_type}
- Content hook: {clip_content[:300]}
- Selection reasoning: {clip_reasoning[:300]}
- Clip number: {clip_index}

Generate metadata optimised for YouTube Shorts, Instagram Reels, and TikTok.

FORMAT — respond with JSON only:
{{
  "title": "Compelling title (≤60 chars)",
  "description": "2-3 sentence engaging description",
  "hashtags": ["tag1", "tag2", "tag3", "tag4", "tag5", "tag6", "tag7", "tag8"],
  "platforms": {{
    "youtube": {{"title": "YouTube title", "description": "YouTube description"}},
    "instagram": {{"caption": "Instagram caption with emojis", "hashtags": ["ig", "tags"]}},
    "tiktok": {{"caption": "TikTok caption", "hashtags": ["tiktok", "tags"]}}
  }},
  "thumbnail_description": "What makes a good thumbnail for this clip"
}}

Tone: {tone}. Be authentic — no excessive caps or spam.
"""


def _parse_metadata_response(response_text: str, clip_data: Dict) -> Optional[ClipMetadata]:
    try:
        text = response_text.strip()
        start = text.find('{')
        end = text.rfind('}') + 1
        if start == -1 or end == 0:
            return None

        data = json.loads(text[start:end])
        required = ["title", "description", "hashtags"]
        if not all(k in data for k in required):
            return None

        seg = clip_data.get("segment_data", {})
        start_time = seg.get("start_time", 0)
        end_time = seg.get("end_time", 60)
        duration = end_time - start_time

        return ClipMetadata(
            title=data["title"][:100],
            description=data["description"][:500],
            hashtags=data.get("hashtags", [])[:15],
            thumbnail_time=start_time + duration / 2,
            duration=duration,
            platform_specific=data.get("platforms", {}),
        )

    except Exception as e:
        print(f"Warning: could not parse metadata response — {e}")
        return None
