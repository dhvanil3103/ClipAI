import React, { useState, useEffect } from 'react';
import './App.css';
import Home from './pages/Home';
import Processing from './pages/Processing';
import Results from './pages/Results';

function App() {
  const [status, setStatus] = useState('idle'); // idle, processing, completed, failed
  const [clips, setClips] = useState([]);
  const [sessionId, setSessionId] = useState(null);
  const [job, setJob] = useState(null);

  const handleGenerate = async ({ url, numClips, duration }) => {
    setJob({ url, numClips, duration });

    try {
      const response = await fetch('http://localhost:8000/api/process-video', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          youtube_url: url,
          num_clips: numClips,
          clip_duration: duration,
        }),
      });

      if (!response.ok) throw new Error('Failed to start processing');

      const data = await response.json();
      setSessionId(data.session_id);
      setStatus('processing');
      setClips([]);
    } catch (error) {
      console.error('Error:', error);
      alert('Failed to start processing. Please check if the backend is running.');
    }
  };

  // WebSocket for real-time updates
  useEffect(() => {
    if (!sessionId) return;

    const websocket = new WebSocket(`ws://localhost:8000/ws/${sessionId}`);

    websocket.onopen = () => console.log('WebSocket connected');

    websocket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        setStatus(data.status);
        if (data.clips && data.clips.length > 0) setClips(data.clips);
      } catch (err) {
        console.error('WebSocket parse error:', err);
      }
    };

    websocket.onerror = () => startStatusPolling();

    websocket.onclose = () => console.log('WebSocket closed');

    return () => {
      if (websocket.readyState === WebSocket.OPEN) websocket.close();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId]);

  const startStatusPolling = () => {
    const pollInterval = setInterval(async () => {
      try {
        const response = await fetch(`http://localhost:8000/api/status/${sessionId}`);
        if (response.ok) {
          const data = await response.json();
          setStatus(data.status);
          if (data.clips && data.clips.length > 0) setClips(data.clips);
          if (data.status === 'completed' || data.status === 'failed') {
            clearInterval(pollInterval);
          }
        }
      } catch (err) {
        console.error('Polling error:', err);
      }
    }, 2000);

    return () => clearInterval(pollInterval);
  };

  const handleCancel = () => {
    setStatus('idle');
    setSessionId(null);
    setJob(null);
    setClips([]);
  };

  // Map backend clips to Results card format
  const mappedClips = clips.map((clip) => ({
    title: clip.title,
    duration: clip.duration,
    score: clip.score,
    scoreColor: clip.score >= 95 ? 'tertiary' : 'secondary',
    tag: clip.type || 'AI GENERATED',
    tagColor: clip.score >= 95 ? 'tertiary' : clip.score >= 90 ? 'secondary' : 'primary',
    thumbnail: clip.thumbnail_path ? `http://localhost:8000${clip.thumbnail_path}` : null,
    videoPath: clip.video_path ? `http://localhost:8000${clip.video_path}` : null,
  }));

  if (status === 'processing') {
    return (
      <div className="dark">
        <Processing job={job} onCancel={handleCancel} />
      </div>
    );
  }

  if (status === 'completed') {
    return (
      <div className="dark">
        <Results clips={mappedClips} onNewClip={handleCancel} />
      </div>
    );
  }

  return (
    <div className="dark">
      <Home onGenerate={handleGenerate} />
    </div>
  );
}

export default App;
