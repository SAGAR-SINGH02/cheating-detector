import socketio
import time

sio = socketio.Client()
sio.connect('http://localhost:5000')
sio.emit('start_session', {'session_id': 'test123'})
print('🔌 Connected! Session started. Speak suspicious words now (e.g., "help with the answer" or "what is the cheat code") for 20s...')
time.sleep(20)
sio.disconnect()
print('Test ended. Check server logs for alerts!')
