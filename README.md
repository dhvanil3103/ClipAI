# 🎬 Podcast Clips Generator

An AI-powered tool that automatically transforms long-form YouTube podcasts into engaging short video clips using LangChain, LangGraph, and Google's Gemini AI.

## 🌟 Features

- **🤖 AI-Powered Analysis**: Uses Google Gemini 2.0 to analyze content and identify engaging moments
- **📝 Free Transcript Fetching**: Leverages YouTube's built-in transcripts (no additional API costs)
- **🎯 Smart Clip Selection**: Automatically selects the best clips while avoiding overlaps
- **⚡ Fast Processing**: Optimized workflow processes most videos in minutes
- **🎬 Multiple Formats**: Supports various aspect ratios (9:16 for Shorts, 16:9, 1:1, etc.)
- **📊 Detailed Analytics**: Provides engagement scores and reasoning for each clip

## 🚀 Quick Start

### Prerequisites

- Python 3.9+
- Google API Key (free tier available)
- FFmpeg (for future video processing)

### Installation

1. **Clone and setup environment:**
   ```bash
   git clone <repository>
   cd podcast_to_shortvideos
   python -m venv venv
   source venv/bin/activate  # or `venv\Scripts\activate` on Windows
   pip install -r requirements.txt
   ```

2. **Configure API key:**
   ```bash
   # Copy the environment template
   cp env.template .env
   
   # Edit .env and add your Google API key:
   # GOOGLE_API_KEY=your_gemini_api_key_here
   ```

3. **Get a Google API Key:**
   - Visit [Google AI Studio](https://aistudio.google.com/app/apikey)
   - Create a new API key
   - Add it to your `.env` file

4. **Verify setup:**
   ```bash
   python main.py setup
   ```

### Basic Usage

```bash
# Process a YouTube video
python main.py process "https://youtube.com/watch?v=VIDEO_ID"

# With custom options
python main.py process "https://youtube.com/watch?v=VIDEO_ID" \
  --max-clips 3 \
  --min-duration 45 \
  --max-duration 75 \
  --aspect-ratio 9:16
```

## 📋 Current Status

### ✅ Implemented (Phase 1 & 2)
- **Environment Setup**: Virtual environment, dependencies, configuration
- **Project Structure**: Organized codebase with proper separation of concerns
- **YouTube Transcript Fetching**: Free, fast transcript extraction
- **LangGraph Workflow**: Sophisticated state management and flow control
- **AI Content Analysis**: Gemini-powered engagement analysis
- **Smart Clip Selection**: Overlap detection and ranking algorithms
- **CLI Interface**: User-friendly command-line tool

### 🚧 In Development (Phase 3)
- **Video Download & Processing**: yt-dlp integration for video files
- **Clip Generation**: FFmpeg-based video segment extraction
- **Caption Overlay**: Automatic subtitle generation
- **Aspect Ratio Conversion**: Multiple format support

### 🔮 Future Features (Phase 4+)
- **Metadata Generation**: AI-powered titles, descriptions, hashtags
- **Social Media Integration**: Direct uploads to platforms
- **Advanced Analytics**: Performance prediction and optimization
- **Custom Branding**: Logos, watermarks, brand colors

## 🎬 How It Works

### 1. Transcript Analysis
```
YouTube URL → Transcript Fetch → Content Chunking → AI Analysis
```

### 2. Content Scoring
The AI analyzes each segment for:
- **Hook Strength**: Attention-grabbing opening
- **Value Density**: Actionable insights or entertainment
- **Standalone Quality**: Comprehensible without context
- **Emotional Impact**: Funny, surprising, or thought-provoking moments

### 3. Smart Selection
- Filters by duration (30-90 seconds)
- Ranks by engagement score and content diversity
- Removes overlapping segments
- Selects optimal clips for maximum impact

## 🛠️ Configuration

### Environment Variables
```bash
# API Keys
GOOGLE_API_KEY=your_gemini_api_key_here
LANGCHAIN_API_KEY=optional_langsmith_key

# Processing Settings
MAX_CLIPS_PER_VIDEO=5
MIN_CLIP_DURATION=30
MAX_CLIP_DURATION=90
DEFAULT_ASPECT_RATIO=9:16

# Output Settings
OUTPUT_DIRECTORY=outputs
TEMP_DIRECTORY=temp
```

### Command Line Options
```bash
# Show current configuration
python main.py config

# Process with custom settings
python main.py process URL \
  --output outputs/my_clips \
  --max-clips 3 \
  --min-duration 45 \
  --max-duration 75 \
  --aspect-ratio 9:16
```

## 💰 Cost Optimization

### Free Tier Friendly
- **YouTube Transcripts**: Completely free, no API limits
- **Gemini 2.0**: Generous free tier with rate limiting
- **Local Processing**: No cloud compute costs

### Best Practices
- **Batch Processing**: Group multiple videos to optimize API usage
- **Smart Caching**: Reuse transcripts and analysis results
- **Rate Limiting**: Respectful API usage to stay within free limits

## 📁 Project Structure

```
podcast_to_shortvideos/
├── src/
│   ├── agents/          # LangGraph agents
│   │   └── podcast_agent.py
│   ├── nodes/           # Individual workflow nodes
│   │   ├── transcript_node.py
│   │   ├── analysis_node.py
│   │   └── selection_node.py
│   ├── utils/           # Utility functions
│   │   ├── transcript.py
│   │   └── video_utils.py
│   ├── models/          # Data models
│   │   ├── state.py
│   │   └── config.py
│   └── cli.py           # Command-line interface
├── outputs/             # Generated clips
├── temp/                # Temporary files
├── cache/               # Cached data
├── requirements.txt     # Dependencies
├── env.template         # Environment template
└── main.py             # Entry point
```

## 🔧 Development

### Running Tests
```bash
# Test transcript functionality
python -c "from src.utils.transcript import fetch_youtube_transcript; print('✅ Imports working')"

# Test configuration
python main.py config

# Test with a sample video
python main.py process "https://youtube.com/watch?v=dQw4w9WgXcQ"
```

### Adding New Features
1. **New Nodes**: Add to `src/nodes/` and register in the agent
2. **Utilities**: Add helper functions to `src/utils/`
3. **Configuration**: Extend models in `src/models/config.py`
4. **CLI Commands**: Add to `src/cli.py`

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details.

## 🆘 Troubleshooting

### Common Issues

**"Google API key not found"**
- Ensure you've copied `env.template` to `.env`
- Add your Google API key to the `.env` file
- Source the environment: `source .env`

**"No transcripts found"**
- Video may not have auto-generated transcripts
- Try with popular videos that likely have transcripts
- Check if the video is public and accessible

**"FFmpeg not found"**
- Install FFmpeg: `brew install ffmpeg` (macOS) or see [FFmpeg installation guide](https://ffmpeg.org/download.html)

**"Import errors"**
- Ensure virtual environment is activated
- Run `pip install -r requirements.txt`
- Check Python version (3.9+ required)

### Getting Help

- Check the [GitHub Issues](link-to-issues) for common problems
- Review the troubleshooting section in the CLI: `python main.py setup`
- Join our [Discord community](link-to-discord) for support

## 🎯 Roadmap

### Q1 2024
- [ ] Complete video generation pipeline
- [ ] Add caption overlays
- [ ] Support multiple aspect ratios

### Q2 2024
- [ ] Metadata generation with AI
- [ ] Thumbnail creation
- [ ] Performance analytics

### Q3 2024
- [ ] Social media integrations
- [ ] Batch processing
- [ ] Custom branding

### Q4 2024
- [ ] Advanced AI models
- [ ] Real-time processing
- [ ] Enterprise features

---

Made with ❤️ by the Podcast Clips team. Star ⭐ this repo if you find it useful! 