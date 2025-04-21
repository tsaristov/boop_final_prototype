"""
LLM API Module for Hephestus

This module provides a standardized interface for making LLM API calls.
"""

import os
import requests
import logging
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv
from fastapi import HTTPException

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables from .env if available
load_dotenv()
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

def llm_api_call(
    model: str, 
    messages: List[Dict[str, str]], 
    system_instructions: Optional[str] = None, 
    personality: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: Optional[int] = None
) -> Dict[str, Any]:
    """
    Make an API call to an LLM service.
    
    Args:
        model: Model identifier (e.g., "anthropic/claude-3-haiku")
        messages: List of message objects with "role" and "content"
        system_instructions: Optional system instructions
        personality: Optional personality modifier
        temperature: Controls randomness (0.0-1.0)
        max_tokens: Maximum tokens to generate
        
    Returns:
        Response from the LLM API
    """
    try:
        # Prepare system message
        system_content = system_instructions or ""
        if personality:
            system_content += f" Your personality: {personality}"

        # Add system message if content exists
        if system_content:
            system_message = {"role": "system", "content": system_content}
            messages = [system_message] + messages

        # Prepare request payload
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature
        }
        
        # Add optional parameters if provided
        if max_tokens:
            payload["max_tokens"] = max_tokens

        # Make the API request
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json"
            },
            json=payload
        )
        response.raise_for_status()
        return response.json()
    
    except requests.exceptions.RequestException as e:
        logger.error(f"LLM API error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
