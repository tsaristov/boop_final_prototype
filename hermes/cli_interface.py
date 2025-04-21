import requests
import json

def chat_with_api(api_url: str = "http://0.0.0.0:8003/detect-intent"):
    print("Type 'exit' to end the conversation.")
    conversation = []
    
    while True:
        user_input = input("You: ")        
        if user_input.lower() == 'exit':
            break

        try:
            # Send the user message to the FastAPI server
            response = requests.post(api_url, json={
                "message": user_input, 
                "user_name": 'Daniel', 
                "user_id": '1', 
            })
            response.raise_for_status()
            data = response.json()
            
            # Update to access the correct key for the assistant's reply
            assistant_reply = data.get("message", "No response")  # Changed from "response" to "message"
            print("Bot:", assistant_reply)
            
            conversation.append({"role": "assistant", "content": assistant_reply})
        except requests.exceptions.RequestException as e:
            print("Error:", e)
            break

if __name__ == "__main__":
    chat_with_api()
