import React, { useRef, useEffect, useState } from 'react';
import io from 'socket.io-client';

const socket = io('http://localhost:5000');  // Backend URL

function App() {
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const [sessionId] = useState(Date.now().toString());  // Unique ID
  const [isStreaming, setIsStreaming] = useState(false);
  const [alerts, setAlerts] = useState([]);

  useEffect(() => {
    let videoInterval;
    let screenInterval;
    let screenVideo;
    let screenCanvas;

    // Get camera/mic permissions
    navigator.mediaDevices.getUserMedia({ video: true, audio: true })
      .then(stream => {
        videoRef.current.srcObject = stream;
        videoRef.current.play();
        setIsStreaming(true);

        // Start session
        socket.emit('start_session', { session_id: sessionId });
        console.log('Session ID:', sessionId);

        // Stream frames at 10 FPS
        const canvas = canvasRef.current;
        const ctx = canvas.getContext('2d');
        videoInterval = setInterval(() => {
          if (videoRef.current) {
            ctx.drawImage(videoRef.current, 0, 0, 640, 480);
            const dataURL = canvas.toDataURL('image/jpeg', 0.8);
            const base64Image = dataURL.split(',')[1];
            socket.emit('video_stream', { image: base64Image, session_id: sessionId });
          }
        }, 100);  // 10 FPS for efficiency

        // Screen capture (optional extension)
        navigator.mediaDevices.getDisplayMedia({ video: true })
          .then(screenStream => {
            screenVideo = document.createElement('video');
            screenVideo.srcObject = screenStream;
            screenVideo.play();
            screenCanvas = document.createElement('canvas');
            screenCanvas.width = 1920; screenCanvas.height = 1080;  // Adjust to your screen
            const screenCtx = screenCanvas.getContext('2d');
            screenInterval = setInterval(() => {
              screenCtx.drawImage(screenVideo, 0, 0, screenCanvas.width, screenCanvas.height);
              const screenDataURL = screenCanvas.toDataURL('image/jpeg', 0.5);
              const screenBase64 = screenDataURL.split(',')[1];
              socket.emit('screen_stream', { image: screenBase64, session_id: sessionId });
            }, 500);  // 2 FPS for screen
          })
          .catch(err => console.warn('Screen capture denied:', err));
      })
      .catch(err => console.error('Media error:', err));

    // Listen for alerts from backend
    socket.on('alert', (data) => {
      setAlerts(prev => [...prev, data]);
      alert(`Warning: ${data.type}!`);  // Popup for now
    });

    // Cleanup on unmount
    return () => {
      socket.off('alert');
      if (videoInterval) clearInterval(videoInterval);
      if (screenInterval) clearInterval(screenInterval);
      if (screenVideo && screenVideo.srcObject) {
        screenVideo.srcObject.getTracks().forEach(track => track.stop());
      }
    };
  }, [sessionId]);

  return (
    <div style={{ padding: '20px', textAlign: 'center' }}>
      <h1>🧠 Online Exam - AI Monitored</h1>
      <p>Session ID: {sessionId}</p>
      <p>Streaming: {isStreaming ? '✅ Camera/Mic Active' : '❌ Not Ready'}</p>
      <video ref={videoRef} width="640" height="480" style={{ border: '2px solid blue', margin: '10px' }} autoPlay muted />
      <canvas ref={canvasRef} width={640} height={480} style={{ display: 'none' }} />
      
      <div style={{ marginTop: '20px' }}>
        <h2>Quiz Questions</h2>
        <p>Question 1: What is 2 + 2?</p>
        <input type="text" placeholder="Your answer" style={{ padding: '5px', margin: '5px' }} />
        <button>Submit</button>
        {/* Add more questions/timer later */}
      </div>

      <div style={{ marginTop: '20px', color: 'red' }}>
        <h3>Alerts:</h3>
        <ul>
          {alerts.map((alert, i) => (
            <li key={i}>{alert.type} at {alert.timestamp}</li>
          ))}
        </ul>
      </div>
    </div>
  );
}

export default App;