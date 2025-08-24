"""
Main PodcastClipsAgent using LangGraph for workflow orchestration.
"""

from typing import Dict, Any
from datetime import datetime
from langgraph.graph import StateGraph, END

from ..models.state import PodcastState
from ..nodes.transcript_node import fetch_transcript_node
from ..nodes.analysis_node import analyze_content_node
from ..nodes.selection_node import select_clips_node
from ..nodes.video_download_node import download_video_node
from ..nodes.clip_generation_node import generate_clips_node
from ..nodes.metadata_generation_node import generate_metadata_node


class PodcastClipsAgent:
    """
    Main agent for processing podcast videos into short clips.
    
    This agent orchestrates the entire workflow:
    1. Fetch transcript from YouTube
    2. Analyze content for engaging moments
    3. Select best clips without overlap
    4. (Future: Generate actual video clips and metadata)
    """
    
    def __init__(self):
        """Initialize the agent and build the workflow graph."""
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow."""
        
        # Create the state graph
        workflow = StateGraph(PodcastState)
        
        # Add nodes
        workflow.add_node("fetch_transcript", fetch_transcript_node)
        workflow.add_node("analyze_content", analyze_content_node)
        workflow.add_node("select_clips", select_clips_node)
        workflow.add_node("download_video", download_video_node)
        workflow.add_node("generate_clips", generate_clips_node)
        workflow.add_node("generate_metadata", generate_metadata_node)
        
        # Define the flow
        workflow.set_entry_point("fetch_transcript")
        
        # Add conditional edges
        workflow.add_conditional_edges(
            "fetch_transcript",
            self._should_continue_after_transcript,
            {
                "analyze": "analyze_content",
                "end": END
            }
        )
        
        workflow.add_conditional_edges(
            "analyze_content", 
            self._should_continue_after_analysis,
            {
                "select": "select_clips",
                "end": END
            }
        )
        
        workflow.add_conditional_edges(
            "select_clips",
            self._should_continue_after_selection,
            {
                "download": "download_video",
                "end": END
            }
        )
        
        workflow.add_conditional_edges(
            "download_video",
            self._should_continue_after_download,
            {
                "generate": "generate_clips",
                "end": END
            }
        )
        
        workflow.add_conditional_edges(
            "generate_clips",
            self._should_continue_after_generation,
            {
                "metadata": "generate_metadata",
                "end": END
            }
        )
        
        workflow.add_edge("generate_metadata", END)
        
        # Compile the graph
        return workflow.compile()
    
    def _should_continue_after_transcript(self, state: PodcastState) -> str:
        """Decide whether to continue after transcript fetching."""
        if state.get("status") == "failed":
            return "end"
        if not state.get("transcript"):
            return "end"
        return "analyze"
    
    def _should_continue_after_analysis(self, state: PodcastState) -> str:
        """Decide whether to continue after content analysis."""
        if state.get("status") == "failed":
            return "end"
        if not state.get("identified_clips"):
            return "end"
        return "select"
    
    def _should_continue_after_selection(self, state: PodcastState) -> str:
        """Decide whether to continue after clip selection."""
        if state.get("status") == "failed":
            return "end"
        if not state.get("selected_clips"):
            return "end"
        return "download"
    
    def _should_continue_after_download(self, state: PodcastState) -> str:
        """Decide whether to continue after video download."""
        if state.get("status") == "failed":
            return "end"
        if not state.get("video_path"):
            return "end"
        return "generate"
    
    def _should_continue_after_generation(self, state: PodcastState) -> str:
        """Decide whether to continue after clip generation."""
        if state.get("status") == "failed":
            return "end"
        processed_clips = state.get("processed_clips", [])
        successful_clips = [c for c in processed_clips if c.get("success", False)]
        if not successful_clips:
            return "end"
        return "metadata"
    
    def process_video(self, url: str, config: Dict[str, Any] = None) -> PodcastState:
        """
        Process a YouTube video and generate clip recommendations.
        
        Args:
            url: YouTube video URL
            config: Optional configuration overrides
        
        Returns:
            Final state with processing results
        """
        
        print(f"🚀 Starting podcast clip generation for: {url}")
        
        # Initialize state
        initial_state: PodcastState = {
            "url": url,
            "video_path": None,
            "audio_path": None,
            "transcript": None,
            "transcript_segments": [],
            "transcript_source": None,
            "identified_clips": [],
            "selected_clips": [],
            "processed_clips": [],
            "metadata": [],
            "video_title": None,
            "video_duration": None,
            "video_id": None,
            "errors": [],
            "warnings": [],
            "config": config or {},
            "status": "starting",
            "created_at": datetime.now().isoformat(),
            "completed_at": None
        }
        
        try:
            # Run the workflow
            final_state = self.graph.invoke(initial_state)
            
            # Mark completion
            final_state["completed_at"] = datetime.now().isoformat()
            
            # Print summary
            self._print_summary(final_state)
            
            return final_state
            
        except Exception as e:
            print(f"❌ Workflow failed: {e}")
            initial_state["errors"].append(f"Workflow execution failed: {str(e)}")
            initial_state["status"] = "failed"
            initial_state["completed_at"] = datetime.now().isoformat()
            return initial_state
    
    def _print_summary(self, state: PodcastState):
        """Print a summary of the processing results."""
        
        print(f"\n📊 Processing Summary")
        print(f"{'='*50}")
        
        # Basic info
        print(f"🎥 Video: {state.get('video_title', 'Unknown')}")
        print(f"🆔 Video ID: {state.get('video_id', 'Unknown')}")
        print(f"⏱️  Duration: {state.get('video_duration', 0):.1f} seconds")
        print(f"📝 Transcript: {len(state.get('transcript', ''))} characters")
        print(f"🔗 Source: {state.get('transcript_source', 'Unknown')}")
        
        # Processing results
        identified_count = len(state.get("identified_clips", []))
        selected_count = len(state.get("selected_clips", []))
        
        print(f"🎬 Clips identified: {identified_count}")
        print(f"✅ Clips selected: {selected_count}")
        
        # Status
        status = state.get("status", "unknown")
        status_emoji = {
            "clips_selected": "✅",
            "no_clips_found": "⚠️ ",
            "no_clips_selected": "⚠️ ",
            "failed": "❌"
        }.get(status, "❓")
        
        print(f"📍 Status: {status_emoji} {status}")
        
        # Errors and warnings
        errors = state.get("errors", [])
        warnings = state.get("warnings", [])
        
        if errors:
            print(f"\n❌ Errors ({len(errors)}):")
            for error in errors:
                print(f"  • {error}")
        
        if warnings:
            print(f"\n⚠️  Warnings ({len(warnings)}):")
            for warning in warnings:
                print(f"  • {warning}")
        
        # Selected clips details
        selected_clips = state.get("selected_clips", [])
        if selected_clips:
            print(f"\n🎬 Selected Clips:")
            for i, clip_data in enumerate(selected_clips, 1):
                duration = clip_data["end_time"] - clip_data["start_time"]
                print(f"  {i}. {clip_data['start_time']:.1f}s-{clip_data['end_time']:.1f}s "
                      f"({duration:.1f}s, score: {clip_data['score']:.1f})")
                print(f"     Type: {clip_data['segment_type']}")
                print(f"     Reasoning: {clip_data['reasoning'][:100]}...")
        
        # Timing
        created_at = state.get("created_at")
        completed_at = state.get("completed_at")
        if created_at and completed_at:
            from datetime import datetime
            start = datetime.fromisoformat(created_at)
            end = datetime.fromisoformat(completed_at)
            duration = (end - start).total_seconds()
            print(f"\n⏱️  Total processing time: {duration:.2f} seconds")
        
        print(f"{'='*50}\n") 