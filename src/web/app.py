"""
Flask web application for viewing generated clips.
"""

import os
import json
from pathlib import Path
from flask import Flask, render_template, send_file, jsonify, request, url_for
from datetime import datetime

from ..models.config import AppConfig


def create_app():
    """Create and configure the Flask app."""
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'podcast-clips-viewer'
    
    @app.route('/')
    def index():
        """Main page showing all processed videos."""
        config = AppConfig.from_env()
        output_dir = Path(config.output_directory)
        
        if not output_dir.exists():
            return render_template('no_videos.html')
        
        # Find all video directories
        video_dirs = [d for d in output_dir.iterdir() if d.is_dir()]
        videos = []
        
        for video_dir in video_dirs:
            summary_file = video_dir / "analysis_summary.json"
            if summary_file.exists():
                try:
                    with open(summary_file, 'r') as f:
                        summary = json.load(f)
                    
                    # Count successful clips
                    processed_clips = summary.get("processed_clips", [])
                    successful_clips = [c for c in processed_clips if c.get("success", False)]
                    
                    videos.append({
                        'video_id': video_dir.name,
                        'title': summary.get('video_title', 'Unknown Title'),
                        'duration': summary.get('video_duration', 0),
                        'uploader': summary.get('video_metadata', {}).get('uploader', 'Unknown'),
                        'created_at': summary.get('created_at', ''),
                        'status': summary.get('status', 'unknown'),
                        'clip_count': len(successful_clips),
                        'url': summary.get('url', ''),
                        'thumbnail_exists': len(successful_clips) > 0
                    })
                except Exception as e:
                    print(f"Error reading summary for {video_dir.name}: {e}")
                    continue
        
        # Sort by creation time (newest first)
        videos.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        
        return render_template('index.html', videos=videos)
    
    @app.route('/video/<video_id>')
    def video_details(video_id):
        """Show details and clips for a specific video."""
        config = AppConfig.from_env()
        video_dir = Path(config.output_directory) / video_id
        summary_file = video_dir / "analysis_summary.json"
        
        if not summary_file.exists():
            return "Video not found", 404
        
        try:
            with open(summary_file, 'r') as f:
                summary = json.load(f)
            
            # Get processed clips with file paths
            processed_clips = summary.get("processed_clips", [])
            metadata = summary.get("metadata", [])
            
            clips_data = []
            for i, clip in enumerate(processed_clips):
                if not clip.get("success", False):
                    continue
                
                clip_metadata = metadata[i] if i < len(metadata) else {}
                
                clips_data.append({
                    'index': clip.get('clip_index', i + 1),
                    'filename': clip.get('filename', ''),
                    'file_size_mb': clip.get('file_size_mb', 0),
                    'thumbnail_path': clip.get('thumbnail_path', ''),
                    'segment_data': clip.get('segment_data', {}),
                    'metadata': clip_metadata,
                    'video_url': url_for('serve_clip', video_id=video_id, filename=clip.get('filename', '')),
                    'thumbnail_url': url_for('serve_thumbnail', video_id=video_id, filename=Path(clip.get('thumbnail_path', '')).name) if clip.get('thumbnail_path') else ''
                })
            
            video_info = {
                'video_id': video_id,
                'title': summary.get('video_title', 'Unknown Title'),
                'duration': summary.get('video_duration', 0),
                'uploader': summary.get('video_metadata', {}).get('uploader', 'Unknown'),
                'view_count': summary.get('video_metadata', {}).get('view_count', 0),
                'upload_date': summary.get('video_metadata', {}).get('upload_date', ''),
                'url': summary.get('url', ''),
                'status': summary.get('status', 'unknown'),
                'created_at': summary.get('created_at', ''),
                'total_clips': len(clips_data)
            }
            
            return render_template('video_details.html', video=video_info, clips=clips_data)
            
        except Exception as e:
            return f"Error loading video details: {e}", 500
    
    @app.route('/video/<video_id>/clips/<filename>')
    def serve_clip(video_id, filename):
        """Serve video clip files."""
        config = AppConfig.from_env()
        clip_path = Path(config.output_directory) / video_id / "clips" / filename
        
        if not clip_path.exists():
            return "Clip not found", 404
        
        return send_file(clip_path, as_attachment=False)
    
    @app.route('/video/<video_id>/thumbnails/<filename>')
    def serve_thumbnail(video_id, filename):
        """Serve thumbnail images."""
        config = AppConfig.from_env()
        thumbnail_path = Path(config.output_directory) / video_id / "thumbnails" / filename
        
        if not thumbnail_path.exists():
            return "Thumbnail not found", 404
        
        return send_file(thumbnail_path, as_attachment=False)
    
    @app.route('/api/video/<video_id>/summary')
    def api_video_summary(video_id):
        """API endpoint for video summary data."""
        config = AppConfig.from_env()
        summary_file = Path(config.output_directory) / video_id / "analysis_summary.json"
        
        if not summary_file.exists():
            return jsonify({"error": "Video not found"}), 404
        
        try:
            with open(summary_file, 'r') as f:
                summary = json.load(f)
            return jsonify(summary)
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    @app.route('/download/<video_id>/<filename>')
    def download_clip(video_id, filename):
        """Download a clip file."""
        config = AppConfig.from_env()
        clip_path = Path(config.output_directory) / video_id / "clips" / filename
        
        if not clip_path.exists():
            return "Clip not found", 404
        
        return send_file(clip_path, as_attachment=True)
    
    # Register template filters
    app.jinja_env.filters['duration'] = format_duration
    app.jinja_env.filters['datetime'] = format_datetime
    
    return app


def format_duration(seconds):
    """Format seconds as MM:SS."""
    if not seconds:
        return "0:00"
    
    minutes = int(seconds // 60)
    seconds = int(seconds % 60)
    return f"{minutes}:{seconds:02d}"


def format_datetime(iso_string):
    """Format ISO datetime string for display."""
    if not iso_string:
        return "Unknown"
    
    try:
        dt = datetime.fromisoformat(iso_string)
        return dt.strftime("%Y-%m-%d %H:%M")
    except:
        return iso_string 