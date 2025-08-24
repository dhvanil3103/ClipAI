# 🎬 Podcast Clips Generator - Web Application

A modern full-stack web application that transforms long-form YouTube videos into engaging short clips using AI-powered content analysis.

## ✨ Features

- **Simple URL Input**: Just paste a YouTube URL and click generate
- **Real-time Progress**: Watch the processing progress with live updates
- **AI-Powered Selection**: Uses Gemini AI to identify the most engaging moments
- **3 High-Quality Clips**: Automatically generates 3 optimized clips per video
- **Interactive Playback**: Click on thumbnails to play clips instantly
- **Modern UI**: Beautiful, responsive design that works on all devices

## 🚀 Quick Start

1. **Install Dependencies** (if not already done):
   ```bash
   # Backend dependencies
   pip install -r backend/requirements.txt
   
   # Frontend dependencies
   cd frontend && npm install
   ```

2. **Start the Application**:
   ```bash
   python start_app.py
   ```

3. **Open Your Browser**:
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs

## 🏗️ Architecture

### Backend (FastAPI)
- **Framework**: FastAPI with WebSocket support
- **Processing**: Integrates with existing podcast clips agent
- **Real-time Updates**: WebSocket connection for progress tracking
- **File Serving**: Static file serving for generated clips

### Frontend (React)
- **Framework**: React with JavaScript (no TypeScript)
- **Styling**: Pure CSS with modern gradients and animations
- **State Management**: React hooks for local state
- **API Communication**: Axios for HTTP requests, WebSocket for real-time updates

## 📁 Project Structure

```
podcast_to_shortvideos/
├── backend/
│   ├── main.py              # FastAPI application
│   └── requirements.txt     # Backend dependencies
├── frontend/
│   ├── src/
│   │   ├── App.js          # Main React component
│   │   ├── App.css         # Styling
│   │   └── index.js        # React entry point
│   └── package.json        # Frontend dependencies
├── src/                    # Original processing logic
├── outputs/                # Generated clips storage
└── start_app.py           # Application launcher
```

## 🎯 How It Works

1. **URL Submission**: User enters YouTube URL
2. **Session Creation**: Backend creates processing session
3. **WebSocket Connection**: Real-time progress updates
4. **Video Processing**: 
   - Fetches transcript from YouTube
   - Analyzes content with Gemini AI
   - Selects best 3 clips
   - Downloads and processes video
   - Generates clip files
5. **Results Display**: Interactive grid of playable clips

## 🛠️ Configuration

The app uses the same configuration as the CLI tool:
- **Max Clips**: 3 clips per video
- **API Rate Limit**: 1 second delay between API calls
- **Clip Duration**: 25-35 seconds (targeting 30s)
- **Quality**: Portrait orientation, 4M bitrate

## 🚦 API Endpoints

- `POST /api/process-video` - Start video processing
- `GET /api/status/{session_id}` - Get processing status
- `WS /ws/{session_id}` - WebSocket for real-time updates
- `GET /clips/*` - Serve generated clip files

## 🎨 UI Features

- **Gradient Background**: Modern purple gradient design
- **Progress Animation**: Smooth animated progress bar
- **Clip Cards**: Hover effects and selection states
- **Responsive Design**: Works on desktop, tablet, and mobile
- **Status Indicators**: Emoji-based status updates
- **Video Player**: Integrated HTML5 video player

## 🔧 Development

Start in development mode:
```bash
# Backend (Terminal 1)
cd backend && python main.py

# Frontend (Terminal 2)  
cd frontend && npm start
```

## 🚀 Production Deployment

For production, build the React app and serve it with the FastAPI backend:
```bash
cd frontend && npm run build
# Then configure FastAPI to serve the build files
```

---

**Enjoy creating amazing short clips from your favorite podcasts! 🎬✨** 