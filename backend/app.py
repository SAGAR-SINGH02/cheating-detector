from flask import Flask
from flask_socketio import SocketIO, emit
import cv2
import mediapipe as mp
import base64
import numpy as np
import threading
import time
from datetime import datetime
import speech_recognition as sr
import pytesseract  # Ready for OCR!

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-this-in-prod'
socketio = SocketIO(app, cors_allowed_origins="*")

# MediaPipe for face/eye/head
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(max_num_faces=1, refine_landmarks=True)

# Voice setup (laptop mic for testing)
recognizer = sr.Recognizer()
mic = sr.Microphone()

# Sessions dict
active_sessions = {}

def process_frame(frame, session_id):
    """AI: Eye & head detection using MediaPipe."""
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = face_mesh.process(rgb_frame)
    
    if results.multi_face_landmarks:
        # Eye tracking (left eye landmark 33 x-pos)
        eye_x = results.multi_face_landmarks[0].landmark[33].x
        if abs(eye_x - 0.5) > 0.15:  # Gaze off-screen
            alert = {'type': 'eye_diverted', 'session_id': session_id, 'timestamp': datetime.now().isoformat()}
            active_sessions[session_id]['alerts'].append(alert)
            emit('alert', alert)
            print(f"🚨 Alert: {alert['type']} for session {session_id}")
            return True
        
        # Head pose (nose tip landmark 1 x-pos for yaw/turn)
        nose_x = results.multi_face_landmarks[0].landmark[1].x
        if abs(nose_x - 0.5) > 0.2:  # Head turned
            alert = {'type': 'head_turned', 'session_id': session_id, 'timestamp': datetime.now().isoformat()}
            active_sessions[session_id]['alerts'].append(alert)
            emit('alert', alert)
            print(f"🚨 Alert: {alert['type']} for session {session_id}")
            return True
    return False

def voice_monitor(session_id):
    """AI: Keyword detection in voice."""
    # Adjust noise once at start (wrap in with to open device)
    with mic as source:
        recognizer.adjust_for_ambient_noise(source, duration=1)
    while session_id in active_sessions:
        try:
            # Listen with fresh with block each time
            with mic as source:
                audio = recognizer.listen(source, timeout=2, phrase_time_limit=5)
            text = recognizer.recognize_google(audio).lower()
            suspicious_words = ['help', 'answer', 'cheat', 'what is']
            if len(text) > 5 and any(word in text for word in suspicious_words):
                alert = {'type': 'suspicious_voice', 'session_id': session_id, 'transcript': text[:50], 'timestamp': datetime.now().isoformat()}
                active_sessions[session_id]['alerts'].append(alert)
                emit('alert', alert)
                print(f"🗣️ Voice Alert: '{text[:50]}...' for session {session_id}")
            else:
                print(f"Speech heard but not suspicious: '{text[:50]}...'")  # Debug all speech
        except sr.WaitTimeoutError:
            pass  # Quiet
        except sr.UnknownValueError:
            print("No clear speech detected")  # Debug unclear audio
        except Exception as e:
            print(f"Voice error: {e}")
        time.sleep(1)

@socketio.on('connect')
def handle_connect():
    print('🔌 Client connected')

@socketio.on('video_stream')
def handle_video(data):
    session_id = data.get('session_id')
    if not session_id:
        return
    if session_id not in active_sessions:
        active_sessions[session_id] = {'frame_count': 0, 'alerts': []}
    
    # Decode base64 frame
    img_data = base64.b64decode(data['image'])
    nparr = np.frombuffer(img_data, np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    if frame is not None:
        active_sessions[session_id]['frame_count'] += 1
        print(f"📹 Frame {active_sessions[session_id]['frame_count']} for {session_id}")
        process_frame(frame, session_id)

@socketio.on('screen_stream')
def handle_screen(data):
    session_id = data.get('session_id')
    if not session_id:
        return
    # Decode frame
    img_data = base64.b64decode(data['image'])
    nparr = np.frombuffer(img_data, np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if frame is not None:
        # OCR for unauthorized text
        text = pytesseract.image_to_string(frame, config='--psm 6').lower()
        suspicious = ['google', 'chat', 'notes']
        if any(word in text for word in suspicious):
            alert = {'type': 'unauthorized_screen', 'session_id': session_id, 'text': text[:50], 'timestamp': datetime.now().isoformat()}
            emit('alert', alert)
            print(f"🖥️ Screen Alert: '{text[:50]}...' for {session_id}")
        print(f"🖥️ Screen frame for {session_id}")

@socketio.on('start_session')
def start_session(data):
    session_id = data['session_id']
    active_sessions[session_id] = {'frame_count': 0, 'alerts': []}
    emit('session_started', {'session_id': session_id})
    threading.Thread(target=voice_monitor, args=(session_id,), daemon=True).start()
    print(f"🎓 Session {session_id} started - AI monitoring active!")

if __name__ == '__main__':
    print("🚀 Backend AI Server starting on http://localhost:5000")
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)