"""
PodcastClipsAgent — orchestrates the full clip-generation workflow via LangGraph.
"""

from datetime import datetime
from typing import Any, Dict

from langgraph.graph import END, StateGraph

from .models import PodcastState
from .nodes import (
    analyze_content_node,
    download_video_node,
    fetch_transcript_node,
    generate_clips_node,
    generate_metadata_node,
    select_clips_node,
)


class PodcastClipsAgent:
    """
    Main agent that orchestrates the podcast-to-short-clips pipeline:
      1. Fetch transcript
      2. Analyse content (single-pass via Gemini)
      3. Select best clips
      4. Download the video
      5. Generate clip files
      6. Generate metadata
    """

    def __init__(self):
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        workflow = StateGraph(PodcastState)

        workflow.add_node("fetch_transcript", fetch_transcript_node)
        workflow.add_node("analyze_content", analyze_content_node)
        workflow.add_node("select_clips", select_clips_node)
        workflow.add_node("download_video", download_video_node)
        workflow.add_node("generate_clips", generate_clips_node)
        workflow.add_node("generate_metadata", generate_metadata_node)

        workflow.set_entry_point("fetch_transcript")

        workflow.add_conditional_edges(
            "fetch_transcript",
            lambda s: "end" if s.get("status") == "failed" or not s.get("transcript") else "analyze",
            {"analyze": "analyze_content", "end": END},
        )
        workflow.add_conditional_edges(
            "analyze_content",
            lambda s: "end" if s.get("status") == "failed" or not s.get("identified_clips") else "select",
            {"select": "select_clips", "end": END},
        )
        workflow.add_conditional_edges(
            "select_clips",
            lambda s: "end" if s.get("status") == "failed" or not s.get("selected_clips") else "download",
            {"download": "download_video", "end": END},
        )
        workflow.add_conditional_edges(
            "download_video",
            lambda s: "end" if s.get("status") == "failed" or not s.get("video_path") else "generate",
            {"generate": "generate_clips", "end": END},
        )
        workflow.add_conditional_edges(
            "generate_clips",
            lambda s: (
                "end"
                if s.get("status") == "failed"
                or not any(c.get("success") for c in s.get("processed_clips", []))
                else "metadata"
            ),
            {"metadata": "generate_metadata", "end": END},
        )
        workflow.add_edge("generate_metadata", END)

        return workflow.compile()

    def process_video(self, url: str, config: Dict[str, Any] = None) -> PodcastState:
        """
        Run the full pipeline for a YouTube URL.

        Args:
            url:    YouTube video URL.
            config: Optional overrides (max_clips_per_video, target_clip_duration, etc.)

        Returns:
            Final PodcastState with results and any errors.
        """
        print(f"Starting podcast clip generation for: {url}")

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
            "completed_at": None,
        }

        try:
            final_state = self.graph.invoke(initial_state)
            final_state["completed_at"] = datetime.now().isoformat()
            self._print_summary(final_state)
            return final_state

        except Exception as e:
            print(f"Workflow failed: {e}")
            initial_state["errors"].append(f"Workflow execution failed: {e}")
            initial_state["status"] = "failed"
            initial_state["completed_at"] = datetime.now().isoformat()
            return initial_state

    def _print_summary(self, state: PodcastState):
        print("\n--- Processing Summary ---")
        print(f"Video: {state.get('video_title')} [{state.get('video_id')}]")
        print(f"Clips identified: {len(state.get('identified_clips', []))}")
        print(f"Clips selected:   {len(state.get('selected_clips', []))}")
        successful = [c for c in state.get("processed_clips", []) if c.get("success")]
        print(f"Clips generated:  {len(successful)}")
        print(f"Status: {state.get('status')}")
        if state.get("errors"):
            print(f"Errors: {state['errors']}")
        if state.get("warnings"):
            print(f"Warnings ({len(state['warnings'])}): first — {state['warnings'][0]}")
        print("--------------------------\n")
