import React, { useState, useEffect } from 'react';
import './App.css';

function App() {
  const [url, setUrl] = useState('');
  const [status, setStatus] = useState('idle'); // idle, processing, completed, failed
  const [message, setMessage] = useState('');
  const [clips, setClips] = useState([]);
  const [sessionId, setSessionId] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!url) return;

    try {
      const response = await fetch('http://localhost:8000/api/process-video', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ youtube_url: url }),
      });

      if (!response.ok) {
        throw new Error('Failed to start processing');
      }

      const data = await response.json();
      setSessionId(data.session_id);
      setStatus('processing');
      setMessage('Processing your video...');
      setClips([]);

    } catch (error) {
      console.error('Error:', error);
      alert('Failed to start processing. Please check if the backend is running.');
    }
  };

  // WebSocket connection for real-time updates
  useEffect(() => {
    if (!sessionId) return;

    const websocket = new WebSocket(`ws://localhost:8000/ws/${sessionId}`);
    
    websocket.onopen = () => {
      console.log('WebSocket connected');
    };

    websocket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        console.log('Received update:', data);
        
        setStatus(data.status);
        setMessage(data.message);
        
        if (data.clips && data.clips.length > 0) {
          setClips(data.clips);
        }
      } catch (error) {
        console.error('Error parsing WebSocket message:', error);
      }
    };

    websocket.onerror = (error) => {
      console.error('WebSocket error:', error);
      // Fallback to polling
      startStatusPolling();
    };

    websocket.onclose = () => {
      console.log('WebSocket closed');
    };

    return () => {
      if (websocket.readyState === WebSocket.OPEN) {
        websocket.close();
      }
    };
  }, [sessionId]);

  // Fallback polling if WebSocket fails
  const startStatusPolling = () => {
    const pollInterval = setInterval(async () => {
      try {
        const response = await fetch(`http://localhost:8000/api/status/${sessionId}`);
        if (response.ok) {
          const data = await response.json();
          setStatus(data.status);
          setMessage(data.message);
          
          if (data.clips && data.clips.length > 0) {
            setClips(data.clips);
          }
          
          if (data.status === 'completed' || data.status === 'failed') {
            clearInterval(pollInterval);
          }
        }
      } catch (error) {
        console.error('Polling error:', error);
      }
    }, 2000);

    return () => clearInterval(pollInterval);
  };

  const getStatusEmoji = (status) => {
    switch (status) {
      case 'processing': return '⚡';
      case 'completed': return '✅';
      case 'failed': return '❌';
      default: return '🎬';
    }
  };

  const playClip = (videoPath) => {
    const fullPath = `http://localhost:8000${videoPath}`;
    const video = document.createElement('video');
    video.src = fullPath;
    video.controls = true;
    video.autoplay = true;
    video.style.width = '100%';
    video.style.maxWidth = '600px';
    video.style.borderRadius = '8px';
    
    const modal = document.createElement('div');
    modal.style.cssText = `
      position: fixed;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      background: rgba(0,0,0,0.8);
      display: flex;
      justify-content: center;
      align-items: center;
      z-index: 1000;
      padding: 20px;
      box-sizing: border-box;
    `;
    
    modal.appendChild(video);
    
    modal.onclick = (e) => {
      if (e.target === modal) {
        modal.remove();
      }
    };
    
    document.body.appendChild(modal);
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>🎬 Podcast Clip Generator</h1>
        <p>Transform long videos into engaging short clips</p>
      </header>

      <main className="App-main">
        <form onSubmit={handleSubmit} className="url-form">
          <div className="input-group">
            <input
              type="url"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="Enter YouTube URL..."
              className="url-input"
              disabled={status === 'processing'}
            />
            <button 
              type="submit" 
              className="submit-button"
              disabled={!url || status === 'processing'}
            >
              {status === 'processing' ? 'Processing...' : 'Generate Clips'}
            </button>
          </div>
        </form>

        {status !== 'idle' && (
          <div className="status-section">
            <div className="status-header">
              <span className="status-emoji">{getStatusEmoji(status)}</span>
              <span className="status-message">{message}</span>
            </div>
            
            {status === 'processing' && (
              <div className="loading-container">
                <div className="loading-spinner"></div>
                <p className="loading-text">This may take a few minutes for longer videos...</p>
              </div>
            )}
          </div>
        )}

        {clips.length > 0 && (
          <div className="clips-section">
            <h2>🎥 Generated Clips</h2>
            <div className="clips-grid">
              {clips.map((clip) => (
                <div key={clip.id} className="clip-card" onClick={() => playClip(clip.video_path)}>
                  <div className="clip-thumbnail">
                    <div className="play-button">▶</div>
                    <img 
                      src={`http://localhost:8000${clip.thumbnail_path}`} 
                      alt={clip.title}
                      onError={(e) => {
                        e.target.style.display = 'none';
                      }}
                    />
                  </div>
                  <div className="clip-info">
                    <h3>{clip.title}</h3>
                    <div className="clip-details">
                      <span className="clip-duration">{clip.duration}</span>
                      <span className="clip-type">{clip.type}</span>
                      <span className="clip-score">⭐ {clip.score}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
