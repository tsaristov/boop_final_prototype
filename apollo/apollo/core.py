from llm_api import llm_api_call
from datetime import datetime
import json
import re

# Load personality from personality.md
def load_personality():
    with open("prompt.md", "r", encoding="utf-8") as file:
        return file.read().strip()

PERSONALITY_PROMPT = load_personality()


def chat_with_bot(message: str, context: str):
    """
    Main chat handler.
    - Processes the message as a regular chat.
    - Guarantees a response, even if the LLM doesn't return anything.
    """

    # Process regular chat
    print("💬 Processing message...")

    # System instructions
    system_instructions = f"""
    Your directive is to reply to the following message, considering the context and your personality.
    You should only respond as your character. Do not provide reasoning, context explanations, or commentary.
    Output only the message the bot would say, as a single continuous piece of dialogue, with no name tags.
    The only thing that should be outputed is the reply, no name tags, or response tags (Ex: "Name: <bot message>)
    """

    content = f"User Message: {message}"

    # Send to LLM API
    try:
        response = llm_api_call(
            model="gryphe/mythomax-l2-13b",
            messages=[{"role": "user", "content": content}],
            personality=PERSONALITY_PROMPT,
            system_instructions=system_instructions,
            context=context
        )

        # Check if the LLM API call was successful and returned a response
        if response:  # response should now be a string
            return response  # Return the response directly without a name tag
        else:
            # Return a default message if the LLM response is empty or malformed
            print("⚠️ LLM API returned an empty or malformed response.")
            return "I'm sorry, I seem to be having a bit of trouble formulating a response right now. Can we try again in a moment?"

    except Exception as e:
        print(f"⚠️ LLM API call failed: {e}")
        # Return a default message if the LLM API call fails
        return "I'm experiencing some technical difficulties. Please bear with me!"