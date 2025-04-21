import os
import requests
from fastapi import HTTPException
from dotenv import load_dotenv

# Load environment variables from .env if available
load_dotenv()
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

def llm_api_call(model: str, messages: list, system_instructions: str = None, context: str = None, personality: str = None):
    try:
        # If system instructions are provided, include them first
        system_message_content = system_instructions if system_instructions else ""
        
        # If personality is provided, append it after system instructions, otherwise, leave it out
        if personality:
            system_message_content += f" Your personality: {personality}"

        # Create the system message with the prioritized instructions
        system_message = {
            "role": "system",
            "content": system_message_content
        }

        # Add the system message to the top of the messages list
        messages = [system_message] + messages

        # If context is provided, append it to the user message
        if context:
            # Modify the user message to include context
            messages[0]["content"] = f"{context}\n{messages[0]['content']}"

        # Make the API request
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": model,
                "messages": messages
            }
        )
        response.raise_for_status()
        # print(response.json())  # Print the JSON content of the response for debugging
        return response.json()["choices"][0]["message"]["content"]  # Return only the final response content
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=str(e))
