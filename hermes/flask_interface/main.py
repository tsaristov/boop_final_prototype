from flask import Flask, request, jsonify, render_template
import requests

app = Flask(__name__)

API_URL = "http://0.0.0.0:8003/detect-intent"  # FastAPI endpoint

@app.route('/')
def home():
    """Render the chat UI."""
    return render_template('chat.html')

@app.route('/chat', methods=['POST'])
def chat():
    """
    Endpoint to handle chat messages.
    Expects a JSON payload with 'message', 'user_name', and 'user_id'.
    """
    data = request.json
    user_message = data.get("message")
    user_name = data.get("user_name", "Daniel")  # Default to 'User' if not provided
    user_id = data.get("user_id", "1")  # Default to '1' if not provided

    if not user_message:
        return jsonify({"error": "Message is required."}), 400

    try:
        # Send the message to the FastAPI server
        response = requests.post(API_URL, json={
            "message": user_message,
            "user_name": user_name,
            "user_id": user_id
        })
        response.raise_for_status()  # Raise an error for bad responses
        data = response.json()  # Parse the JSON response

        # Return the assistant's reply
        assistant_reply = data.get("message", "No response")
        return jsonify({"response": assistant_reply})

    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Error connecting to the API: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)  # Run the Flask app
