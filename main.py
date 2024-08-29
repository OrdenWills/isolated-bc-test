import os
import base64
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import google.generativeai as genai
from datetime import datetime
import dotenv
import time

app = Flask(__name__)
app.secret_key = os.environ.get("APP_PASSWORD")
CORS(app, resources={r"/*": {"origins": "http://localhost:5173"}})
socketio = SocketIO(app,cors_allowed_origins="http://localhost:5173")


# Directory to save videos
SAVE_DIR = 'videos'
if not os.path.exists(SAVE_DIR):
    os.makedirs(SAVE_DIR)

dotenv.load_dotenv('./keys.env')
print(os.path.exists('./keys.env'))

def init_model():
    GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
    genai.configure(api_key=GOOGLE_API_KEY)
    model = genai.GenerativeModel('models/gemini-1.5-flash')
    return model.start_chat(history=[])

conversations = init_model()

structured_prompt = """

Please provide your response as a valid JSON array for multi-step processes, using default Markdown formatting within the JSON strings to preserve text styling and structure:

[
  {{
    "title": "[Step Title] .... # Headings for titles Add Markdown elements as needed",
    "description": [
      "Brief overview point 1 with **bold** or *italic* if needed",
      "Brief overview point 2 with `code` or [links](url) if relevant"
    ],
    "view_more": "Detailed explanation of the step...\n\n- Use bullet points\n- # Headings\n- **Bold text**\n- *Italic text*\n- `code snippets`\n- And other Markdown elements as needed"
  }},
  {{
    "title": "[Step Title].... # Headings for titles Add Markdown elements as needed",
    "description": [
      "Brief overview point 1 with **bold** or *italic* if needed",
      "Brief overview point 2 with `code` or [links](url) if relevant"
    ],
    "view_more": "Detailed explanation with Markdown...\n\n1. Numbered lists\n2. ## Subheadings\n3. > Blockquotes\n\nAnd so on..."
  }},
  ...
]

Important:
1. Ensure the response is a valid JSON array without any surrounding code block markers(eg ```json```).
2. Use Markdown formatting within the JSON strings for text styling and structure.
3. Escape any quotes or special characters within the JSON strings properly.
4. Omit the "view_more" field if there's no additional information to provide.

"""

screenshot_analysis_prompt = """
Analyze the provided screenshot in the context of the user's current task.

1. Identify the main elements and content visible in the screenshot.
2. Determine if the screenshot shows the correct screen for the user's current task.
3. If the screenshot does not match the expected screen for the task:
   a. Explain that the user is on the wrong screen.
   b. Provide clear, step-by-step instructions on how to navigate to the correct screen.
   c. Describe what the correct screen should look like.
4. If the screenshot does show the correct screen:
   a. Confirm that the user is in the right place.
   b. Provide guidance on what to do next for their task.

Please structure your response as a valid JSON object with the following format:

{
  "screenshot_matches_task": true/false,
  "current_screen_description": "Brief description of what's visible in the screenshot",
  "guidance": [
    {
      "step": "Step 1",
      "instruction": "Detailed instruction for this step"
    },
    {
      "step": "Step 2",
      "instruction": "Detailed instruction for this step"
    }
  ],
  "additional_notes": "Any other relevant information or tips"
}

Important:
1. Ensure the response is a valid JSON array without any surrounding code block markers(eg ```json```).=.
"""

@app.route("/")
def home():
    # print("My files:")
    # for f in genai.list_files():
    #     print("  ", f.name)
    #     genai.delete_file(f.name)
    return jsonify({"response":"you're in home page"})


@app.route("/prompt", methods=["POST"])
def process_prompt():
    data = request.json
    print('data object is',data)
    prompt = data.get('prompt')
    
    try:
        # Check if the video directory is not empty
        screenshots = os.listdir(SAVE_DIR)
        if screenshots:
            try:
                # Get the latest screenshot (assuming filenames are timestamp-based)
                latest_screenshot = max(screenshots, key=lambda f: os.path.getctime(os.path.join(SAVE_DIR, f)))
                screenshot_path = os.path.join(SAVE_DIR, latest_screenshot)
                
                print(f"Using latest screenshot:....")
                video_file = genai.upload_file(path=screenshot_path)
                print(f"Completed upload: {video_file.uri}")
                chat = conversations.send_message(
                    [f"{prompt} {structured_prompt}", video_file],
                    safety_settings={
                        'HATE': 'BLOCK_NONE',
                        'HARASSMENT': 'BLOCK_NONE',
                        'SEXUAL': 'BLOCK_NONE',
                        'DANGEROUS': 'BLOCK_NONE'
                    },   
                )
                print(chat.text)
            except Exception as e:
                print('analysis error',str(e))

        else: 
            try:
                print('no screenshot avail')
                chat = conversations.send_message(
                    f"{prompt} {structured_prompt}",
                    safety_settings={
                        'HATE': 'BLOCK_NONE',
                        'HARASSMENT': 'BLOCK_NONE',
                        'SEXUAL': 'BLOCK_NONE',
                        'DANGEROUS': 'BLOCK_NONE'
                    }
                )
                print(chat.text)
                return jsonify({"response": chat.text})
            except Exception as e:
                print('analysis error',str(e))
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    


@socketio.on('connect')
def handle_connect():
    print('Client connected')

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

@socketio.on('video-data')
def handle_video_data(data):
    
    # Generate a unique filename using timestamp
    timestamp = int(time.time() * 1000)
    file_name = os.path.join(SAVE_DIR, f'screenshot_{timestamp}.webm')
    
    # Save the incoming data to a WebM file
    with open(file_name, 'wb') as f:
        f.write(data)
    
    latest_screenshot = file_name
    # Videos need to be processed before you can use them.
    while myfile.state.name == "PROCESSING":
        print("processing video...")
        time.sleep(3)
        myfile = genai.get_file(myfile.name)
    print(f'New screenshot saved: {file_name}')
    # genai.delete_file(video_file)
    # Trigger the prompt processing
    try:
        chat = conversations.send_message(
            [f"Analyze the latest screenshot: {screenshot_analysis_prompt}", video_file],
            safety_settings={
                'HATE': 'BLOCK_NONE',
                'HARASSMENT': 'BLOCK_NONE',
                'SEXUAL': 'BLOCK_NONE',
                'DANGEROUS': 'BLOCK_NONE'
            },   
        )
        print(chat.text)
        emit('analysis_result', {'response': chat.text})
    except Exception as e:
        print('analysis error',str(e))
        emit('analysis_error', {'error': str(e)})

    emit('received', {'status': 'success', 'file_name': file_name})
if __name__ == "__main__":
    socketio.run(app, debug=True, port=5000)















# import os, time
# import base64
# import dotenv
# import json
# from flask import Flask, request, jsonify
# from flask_cors import CORS
# from flask_socketio import SocketIO, emit
# import google.generativeai as genai
# from datetime import datetime

# app = Flask(__name__)
# app.secret_key = os.environ.get("APP_PASSWORD")
# CORS(app, resources={r"/*": {"origins": "http://localhost:5173"}})
# socketio = SocketIO(app,cors_allowed_origins="http://localhost:5173")


# # Directory to save videos
# SAVE_DIR = 'videos'
# if not os.path.exists(SAVE_DIR):
#     os.makedirs(SAVE_DIR)

# dotenv.load_dotenv('./keys.env')
# # print(os.path.exists('./keys.env'))

# latest_screenshot = None

# def init_model():
#     GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
#     genai.configure(api_key=GOOGLE_API_KEY)
#     model = genai.GenerativeModel('models/gemini-1.5-flash')
#     return model.start_chat(history=[])

# conversations = init_model()

# @app.route("/")
# def home():
#     return jsonify({"response":"you're in home page"})

# structured_prompt =  """

# Please provide your response as a valid JSON array for multi-step processes, using default Markdown formatting within the JSON strings to preserve text styling and structure:

# [
#   {{
#     "title": "Step 1: [Step Title] .... # Headings for titles Add Markdown elements as needed",
#     "description": [
#       "Brief overview point 1 with **bold** or *italic* if needed",
#       "Brief overview point 2 with `code` or [links](url) if relevant"
#     ],
#     "view_more": "Detailed explanation of the step...\n\n- Use bullet points\n- # Headings\n- **Bold text**\n- *Italic text*\n- `code snippets`\n- And other Markdown elements as needed"
#   }},
#   {{
#     "title": "Step 2: [Step Title].... # Headings for titles Add Markdown elements as needed",
#     "description": [
#       "Brief overview point 1 with **bold** or *italic* if needed",
#       "Brief overview point 2 with `code` or [links](url) if relevant"
#     ],
#     "view_more": "Detailed explanation with Markdown...\n\n1. Numbered lists\n2. ## Subheadings\n3. > Blockquotes\n\nAnd so on..."
#   }},
#   ...
# ]

# Important:
# 1. Ensure the response is a valid JSON array without any surrounding code block markers(eg ```json```).
# 2. Use Markdown formatting within the JSON strings for text styling and structure.
# 3. Escape any quotes or special characters within the JSON strings properly.
# 4. Omit the "view_more" field if there's no additional information to provide.

# """

# screenshot_analysis_prompt = """
# Analyze the provided screenshot in the context of the user's current task.

# 1. Identify the main elements and content visible in the screenshot.
# 2. Determine if the screenshot shows the correct screen for the user's current task.
# 3. If the screenshot does not match the expected screen for the task:
#    a. Explain that the user is on the wrong screen.
#    b. Provide clear, step-by-step instructions on how to navigate to the correct screen.
#    c. Describe what the correct screen should look like.
# 4. If the screenshot does show the correct screen:
#    a. Confirm that the user is in the right place.
#    b. Provide guidance on what to do next for their task.

# Please structure your response as a valid JSON object with the following format:

# {
#   "screenshot_matches_task": true/false,
#   "current_screen_description": "Brief description of what's visible in the screenshot",
#   "guidance": [
#     {
#       "step": "Step 1",
#       "instruction": "Detailed instruction for this step"
#     },
#     {
#       "step": "Step 2",
#       "instruction": "Detailed instruction for this step"
#     }
#   ],
#   "additional_notes": "Any other relevant information or tips"
# }

# Ensure your response is a valid JSON object that can be parsed without modification.
# """

# @app.route("/prompt", methods=["POST"])
# def process_prompt():
#     data = request.json
#     print('data object is',data)
#     prompt = data.get('prompt')
    



#     chat = conversations.send_message(
#                 [f"{prompt} {structured_prompt}"],
#                 safety_settings={
#                     'HATE': 'BLOCK_NONE',
#                     'HARASSMENT': 'BLOCK_NONE',
#                     'SEXUAL': 'BLOCK_NONE',
#                     'DANGEROUS': 'BLOCK_NONE'
#                 }
#             )



#     response_text = chat.text
#     print(response_text)
#     return jsonify({"response": response_text})
#     # except Exception as e:
#     #     return jsonify({"error": str(e)}), 500
    


# @socketio.on('connect')
# def handle_connect():
#     print('Client connected')

# @socketio.on('disconnect')
# def handle_disconnect():
#     print('Client disconnected')

# @socketio.on('video-data')
# def handle_video_data(data):
#     # Save the incoming data to a WebM file
#     global latest_screenshot
    
#     # Generate a unique filename using timestamp
#     timestamp = int(time.time() * 1000)
#     file_name = os.path.join(SAVE_DIR, f'screenshot_{timestamp}.webm')
    
#     # Save the incoming data to a WebM file
#     with open(file_name, 'wb') as f:
#         f.write(data)
    
#     latest_screenshot = file_name
#     print(f'New screenshot saved: {file_name}')
    
#     # Trigger the prompt processing
#     try:
#         chat = conversations.send_message(
#             [f"Analyze the latest screenshot: {screenshot_analysis_prompt}", genai.upload_file(path=file_name)],
#             safety_settings={
#                 'HATE': 'BLOCK_NONE',
#                 'HARASSMENT': 'BLOCK_NONE',
#                 'SEXUAL': 'BLOCK_NONE',
#                 'DANGEROUS': 'BLOCK_NONE'
#             },   
#         )
#         emit('analysis_result', {'response': chat.text})
#     except Exception as e:
#         emit('analysis_error', {'error': str(e)})

#     emit('received', {'status': 'success', 'file_name': file_name})

# if __name__ == "__main__":
#     socketio.run(app, debug=True, port=5000)