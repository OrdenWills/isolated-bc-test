import os
import base64
from flask import Flask, request, jsonify
from flask_cors import CORS
import google.generativeai as genai

app = Flask(__name__)
app.secret_key = os.environ.get("APP_PASSWORD")
CORS(app)

# dotenv.load_dotenv('./keys.env')
# print(os.path.exists('./keys.env'))

def init_model():
    GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
    genai.configure(api_key=GOOGLE_API_KEY)
    model = genai.GenerativeModel('models/gemini-1.5-pro-latest')
    return model.start_chat(history=[])

conversations = init_model()

@app.route("/prompt", methods=["POST"])
def process_prompt():
    data = request.json
    print('data object is',data)
    prompt = data.get('prompt')
    temperature = data.get('temperature')
    top_k = data.get('topK')
    screenshot = data.get('screenshot')
    
    try:
        # If there's a screenshot, process it
        if screenshot:
            # Remove the data URL prefix
            image_data = screenshot.split(',')[1]
            image_bytes = base64.b64decode(image_data)
            
            # Generate a response based on both the image and the text prompt
            chat = conversations.send_message(
                [prompt, image_bytes],
                generation_config={
                    'temperature': temperature,
                    'top_k': top_k,
                },
                safety_settings={
                    'HATE': 'BLOCK_NONE',
                    'HARASSMENT': 'BLOCK_NONE',
                    'SEXUAL': 'BLOCK_NONE',
                    'DANGEROUS': 'BLOCK_NONE'
                }
            )
        else:
            # If there's no screenshot, just process the text prompt
            chat = conversations.send_message(
                prompt,
                generation_config={
                    'temperature': temperature,
                    'top_k': top_k,
                },
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

if __name__ == '__main__':
    app.run(debug=True)