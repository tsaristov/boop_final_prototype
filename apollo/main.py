from fastapi import FastAPI
from pydantic import BaseModel
from apollo.core import chat_with_bot
from apollo.database import add_message, initialize_db
import requests
import uvicorn
import os

app = FastAPI()

initialize_db()

class ChatRequest(BaseModel):
    user_id: str
    user_name: str
    message: str
    context: str

class ChatResponse(BaseModel):
    message: str

@app.post("/generate", response_model=ChatResponse)
async def generate_response(request: ChatRequest):
    user_id = request.user_id # Store the user ID
    user_name = request.user_name
    user_message = request.message
    user_context = request.context

    if user_context == "":
        user_context = requests.post(
            f"http://0.0.0.0:8002/get-context",
            json={
                "user_id": user_id,
                "user_name": user_name,
                "message": user_message
            }
        ).json()

    print(user_context)
    # Store the user's message in the database
    add_message(user_id, user_name, user_message)

    # Call the chat_with_bot to generate a response
    response = chat_with_bot(user_message, user_context)

    # Store the bot's message in the database
    add_message("0", "Talos", response)
    
    return ChatResponse(message=response)

if __name__ == "__main__":
    print("Starting Apollo Personality server...")
    
    # Check if OpenRouter API key is set
    if not os.getenv("OPENROUTER_API_KEY"):
        print("WARNING: OPENROUTER_API_KEY environment variable is not set.")
        print("LLM-based features will not work properly.")
        print("Please set this variable in your .env file or environment.")
    
    # Run the FastAPI server
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8001,
        reload=True
    )