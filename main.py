import os
import base64
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import google.generativeai as genai
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.environ.get("APP_PASSWORD")
CORS(app)
socketio = SocketIO(app)

# Directory to save videos
SAVE_DIR = 'videos'
if not os.path.exists(SAVE_DIR):
    os.makedirs(SAVE_DIR)

# dotenv.load_dotenv('./keys.env')
# print(os.path.exists('./keys.env'))

def init_model():
    GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
    genai.configure(api_key=GOOGLE_API_KEY)
    model = genai.GenerativeModel('models/gemini-1.5-flash')
    return model.start_chat(history=[])

conversations = init_model()

@app.route("/")
def home():
    return jsonify({"response":"you're in home page"})

@app.route("/prompt", methods=["POST"])
def process_prompt():
    data = request.json
    print('data object is',data)
    prompt = data.get('prompt')
    # temperature = data.get('temperature')
    # top_k = data.get('topK')
    screenshot = data.get('screenshot')
    
    try:
        # If there's no screenshot, just process the text prompt
        # Save the screenshot if it exists
        if screenshot:
            file_name = f"{SAVE_DIR}/output.webm"
            video_file = genai.upload_file(path=file_name)
            print(f"Completed upload: {video_file.uri}")

            chat = conversations.send_message(
                [prompt,video_file],
                safety_settings={
                    'HATE': 'BLOCK_NONE',
                    'HARASSMENT': 'BLOCK_NONE',
                    'SEXUAL': 'BLOCK_NONE',
                    'DANGEROUS': 'BLOCK_NONE'
                },   
            )

        else: 
            chat = conversations.send_message(
                prompt,
                safety_settings={
                    'HATE': 'BLOCK_NONE',
                    'HARASSMENT': 'BLOCK_NONE',
                    'SEXUAL': 'BLOCK_NONE',
                    'DANGEROUS': 'BLOCK_NONE'
                }
            )
            return jsonify({"response": chat.text})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    


@socketio.on('connect')
def handle_connect():
    print('Client connected')

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

@socketio.on('video_data')
def handle_video_data(data):
    # Save the incoming data to a WebM file
    with open(os.path.join(SAVE_DIR, 'output.webm'), 'ab') as f:
        f.write(data)
    emit('received', {'status': 'success'})

if __name__ == '__main__':
    socketio.run(app, debug=True)