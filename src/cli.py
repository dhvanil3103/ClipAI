"""
Command line interface for the Podcast Clips Generator.
"""

import typer
from typing import Optional
from pathlib import Path
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel
import os

# Disable LangSmith tracing to prevent 403 errors
os.environ['LANGCHAIN_TRACING_V2'] = 'false'
os.environ['LANGSMITH_TRACING'] = 'false'

from .models.config import AppConfig

app = typer.Typer(
    name="podcast-clips",
    help="Generate short video clips from long-form YouTube podcasts",
    add_completion=False
)

console = Console()


@app.command("process")
def process_video(
    url: str = typer.Argument(..., help="YouTube URL to process"),
    output_dir: Optional[str] = typer.Option(
        None, 
        "--output", 
        "-o", 
        help="Output directory for generated clips"
    ),
    max_clips: Optional[int] = typer.Option(
        None,
        "--max-clips",
        "-m",
        help="Maximum number of clips to generate"
    ),
    min_duration: Optional[int] = typer.Option(
        None,
        "--min-duration",
        help="Minimum clip duration in seconds"
    ),
    max_duration: Optional[int] = typer.Option(
        None,
        "--max-duration", 
        help="Maximum clip duration in seconds"
    ),
    aspect_ratio: Optional[str] = typer.Option(
        None,
        "--aspect-ratio",
        "-a",
        help="Aspect ratio for clips (9:16, 16:9, 1:1, 4:5)"
    ),
    config_file: Optional[Path] = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to configuration file"
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Enable verbose logging"
    )
):
    """
    Process a YouTube video and generate short clips.
    
    This command downloads the video, extracts transcripts, analyzes content,
    and generates engaging short clips suitable for social media platforms.
    """
    
    console.print("\n🎥 [bold blue]Podcast Clips Generator[/bold blue]\n")
    
    # Load configuration
    try:
        config = AppConfig.from_env()
        
        # Override with command line arguments
        if output_dir:
            config.output_directory = output_dir
        if max_clips:
            config.processing.max_clips_per_video = max_clips
        if min_duration:
            config.processing.min_clip_duration = min_duration
        if max_duration:
            config.processing.max_clip_duration = max_duration
        if aspect_ratio:
            config.video.aspect_ratio = aspect_ratio
            
    except Exception as e:
        console.print(f"❌ [red]Configuration error: {e}[/red]")
        raise typer.Exit(1)
    
    # Validate required environment variables
    if not config.llm.api_key:
        console.print("❌ [red]Error: GOOGLE_API_KEY not found in environment.[/red]")
        console.print("\nPlease set your Google API key:")
        console.print("1. Copy env.template to .env")
        console.print("2. Add your Google API key to the .env file")
        console.print("3. Source the environment: source .env")
        raise typer.Exit(1)
    
    # Display configuration
    console.print(Panel.fit(
        f"[bold]URL:[/bold] {url}\n"
        f"[bold]Output Directory:[/bold] {config.output_directory}\n"
        f"[bold]Max Clips:[/bold] {config.processing.max_clips_per_video}\n"
        f"[bold]Duration Range:[/bold] {config.processing.min_clip_duration}-{config.processing.max_clip_duration}s\n"
        f"[bold]Aspect Ratio:[/bold] {config.video.aspect_ratio}\n"
        f"[bold]Quality:[/bold] {config.video.bitrate} bitrate",
        title="🎬 Processing Configuration"
    ))
    
    # Validate URL
    if not url.startswith(("http://", "https://")):
        console.print("❌ [red]Error: Please provide a valid YouTube URL[/red]")
        raise typer.Exit(1)
    
    # Import and run the actual processing workflow
    try:
        from .agents.podcast_agent import PodcastClipsAgent
        from .utils.video_utils import validate_youtube_url
        
        # Validate YouTube URL format
        if not validate_youtube_url(url):
            console.print("❌ [red]Error: Invalid YouTube URL format[/red]")
            raise typer.Exit(1)
        
        # Create and run the agent
        agent = PodcastClipsAgent()
        
        # Convert config to dict for state
        config_dict = {
            "max_clips": config.processing.max_clips_per_video,
            "min_duration": config.processing.min_clip_duration,
            "max_duration": config.processing.max_clip_duration,
            "min_score": config.processing.min_engagement_score
        }
        
        # Process the video
        console.print("\n🚀 [bold blue]Starting video processing...[/bold blue]")
        result = agent.process_video(url, config_dict)
        
        # Check results
        if result["status"] == "clips_selected":
            console.print(f"\n✅ [green]Successfully generated {len(result['selected_clips'])} clips![/green]")
            
            # Save results summary
            import json
            from pathlib import Path
            
            output_dir = Path(config.output_directory) / result["video_id"]
            output_dir.mkdir(parents=True, exist_ok=True)
            
            summary_file = output_dir / "analysis_summary.json"
            with open(summary_file, 'w') as f:
                json.dump(result, f, indent=2, default=str)
            
            console.print(f"📁 Results saved to: {summary_file}")
            
            console.print("\n🎬 [bold]Next Steps:[/bold]")
            console.print("• Video clips analysis complete")
            console.print("• Video generation will be implemented in Phase 3")
            console.print("• Check the analysis_summary.json for detailed results")
            
        elif result["status"] in ["no_clips_found", "no_clips_selected"]:
            console.print("\n⚠️  [yellow]No suitable clips found for this video.[/yellow]")
            console.print("This could mean:")
            console.print("• Content doesn't meet engagement criteria")
            console.print("• Video is too short or lacks clear structure")
            console.print("• Try adjusting the minimum score threshold")
            
        else:
            console.print(f"\n❌ [red]Processing failed: {result.get('status', 'unknown error')}[/red]")
            if result.get("errors"):
                for error in result["errors"]:
                    console.print(f"  • {error}")
        
    except ImportError as e:
        console.print(f"❌ [red]Import error: {e}[/red]")
        console.print("Make sure all dependencies are installed.")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"❌ [red]Unexpected error: {e}[/red]")
        raise typer.Exit(1)


@app.command("config")
def show_config():
    """Show current configuration settings."""
    
    try:
        config = AppConfig.from_env()
        
        console.print("\n📋 [bold blue]Current Configuration[/bold blue]\n")
        
        console.print(Panel.fit(
            f"[bold]Output Directory:[/bold] {config.output_directory}\n"
            f"[bold]Temp Directory:[/bold] {config.temp_directory}\n"
    
            f"[bold]Video Settings:[/bold]\n"
            f"  • Resolution: {config.video.resolution}\n"
            f"  • Aspect Ratio: {config.video.aspect_ratio}\n"
            f"  • FPS: {config.video.fps}\n"
            f"  • Codec: {config.video.codec}\n\n"
            f"[bold]Processing Settings:[/bold]\n"
            f"  • Max Clips: {config.processing.max_clips_per_video}\n"
            f"  • Duration: {config.processing.min_clip_duration}-{config.processing.max_clip_duration}s\n"
            f"  • Min Score: {config.processing.min_engagement_score}\n\n"
            f"[bold]LLM Settings:[/bold]\n"
            f"  • Model: {config.llm.model_name}\n"
            f"  • Temperature: {config.llm.temperature}\n"
            f"  • API Key: {'✅ Set' if config.llm.api_key else '❌ Not Set'}",
            title="🛠️ Configuration"
        ))
        
    except Exception as e:
        console.print(f"❌ [red]Error loading configuration: {e}[/red]")
        raise typer.Exit(1)


@app.command("web")
def start_web_server(
    port: int = typer.Option(5000, "--port", "-p", help="Port to run the web server on"),
    host: str = typer.Option("127.0.0.1", "--host", "-h", help="Host to bind the web server to"),
    debug: bool = typer.Option(False, "--debug", "-d", help="Enable debug mode")
):
    """Start the web interface to view generated clips."""
    
    console.print("\n🌐 [bold blue]Starting Web Interface[/bold blue]\n")
    
    try:
        from .web.app import create_app
        
        app = create_app()
        
        console.print(f"🚀 Web server starting on http://{host}:{port}")
        console.print("📁 Serving clips from the outputs directory")
        console.print("🔄 Refresh your browser after processing new videos")
        console.print("\n💡 [yellow]Tip: Keep this running while processing videos to see real-time results![/yellow]")
        console.print("\n🛑 Press Ctrl+C to stop the server\n")
        
        app.run(host=host, port=port, debug=debug)
        
    except ImportError as e:
        console.print(f"❌ [red]Import error: {e}[/red]")
        console.print("Make sure Flask is installed: pip install flask")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"❌ [red]Failed to start web server: {e}[/red]")
        raise typer.Exit(1)


@app.command("setup")
def setup_environment():
    """Set up the environment and verify dependencies."""
    
    console.print("\n🔧 [bold blue]Environment Setup[/bold blue]\n")
    
    checks = []
    
    # Check Python version
    import sys
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    checks.append(("Python Version", python_version, sys.version_info >= (3, 9)))
    
    # Check required directories
    config = AppConfig.from_env()
    for dir_name, dir_path in [
        ("Output Directory", config.output_directory),
        ("Temp Directory", config.temp_directory)
    ]:
        exists = Path(dir_path).exists()
        checks.append((dir_name, dir_path, exists))
    
    # Check environment variables
    api_key_set = bool(os.getenv('GOOGLE_API_KEY'))
    checks.append(("Google API Key", "Set" if api_key_set else "Not Set", api_key_set))
    
    # Check external dependencies
    external_deps = []
    
    # Check FFmpeg
    try:
        import subprocess
        result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True)
        ffmpeg_available = result.returncode == 0
        external_deps.append(("FFmpeg", "Available" if ffmpeg_available else "Not Found", ffmpeg_available))
    except FileNotFoundError:
        external_deps.append(("FFmpeg", "Not Found", False))
    
    # Display results
    console.print("📦 [bold]Python Environment[/bold]")
    for name, value, status in checks:
        status_icon = "✅" if status else "❌"
        console.print(f"  {status_icon} {name}: {value}")
    
    console.print("\n🛠️ [bold]External Dependencies[/bold]")
    for name, value, status in external_deps:
        status_icon = "✅" if status else "❌"
        console.print(f"  {status_icon} {name}: {value}")
    
    # Show setup instructions if needed
    failed_checks = [name for name, _, status in checks + external_deps if not status]
    
    if failed_checks:
        console.print(f"\n⚠️  [yellow]Setup Issues Found[/yellow]")
        
        if not api_key_set:
            console.print("\n🔑 [bold]API Key Setup:[/bold]")
            console.print("1. Get a Google API key from: https://aistudio.google.com/app/apikey")
            console.print("2. Copy env.template to .env: cp env.template .env")
            console.print("3. Add your API key to the .env file")
            console.print("4. Load environment: source .env")
        
        if "FFmpeg" in failed_checks:
            console.print("\n🎬 [bold]FFmpeg Installation:[/bold]")
            console.print("macOS: brew install ffmpeg")
            console.print("Ubuntu: sudo apt install ffmpeg")
            console.print("Windows: Download from https://ffmpeg.org/download.html")
    else:
        console.print("\n✅ [green bold]All checks passed! Environment is ready.[/green bold]")


def main():
    """Main entry point for the CLI."""
    app()


if __name__ == "__main__":
    main() 