from typing import List, Dict, Any, Optional, Tuple
import re
import os
import requests
from datetime import datetime
from dotenv import load_dotenv
from .database import get_recent_messages, add_knowledge

# Load environment variables
load_dotenv()
API_KEY = os.getenv("OPENROUTER_API_KEY")

def extract_knowledge_from_message(user_id: str, message: str, source: str, user_name: str = None) -> List[Dict]:
    """
    Extract knowledge about a user from a message.
    
    Args:
        user_id: ID of the user who sent the message
        message: The message content
        source: Source identifier (e.g., message ID)
        user_name: Optional user name
        
    Returns:
        List of extracted knowledge entries
    """
    # Prepare API request for knowledge extraction
    system_message = """
    Extract verifiable facts about the user from their message. 
    
    Focus on:
    - Preferences (favorite colors, foods, activities)
    - Demographics (age, location, occupation)
    - Personal traits (personality, habits, skills)
    - Relationships (family, friends, pets)
    
    Return a JSON array of facts in this format:
    [
      {
        "attribute": "factual attribute name (e.g., favorite_color, age, has_pet)",
        "value": "the value of this attribute",
        "confidence": confidence score from 0.0 to 1.0
      }
    ]
    
    Only include facts explicitly mentioned or strongly implied. Assign lower confidence scores (0.1-0.5) to implications, and higher scores (0.6-1.0) to explicit statements.
    """
    
    user_message = f"User ({user_id}): {message}"
    
    # Call LLM API
    try:
        response = call_llm_api(system_message, user_message)
        extracted_knowledge = parse_knowledge_response(response)
        
        # Save knowledge to database
        saved_entries = []
        for entry in extracted_knowledge:
            knowledge_id = add_knowledge(
                user_id=user_id,
                attribute=entry["attribute"],
                value=entry["value"],
                confidence=entry["confidence"],
                source=source
            )
            saved_entries.append({
                "id": knowledge_id,
                "attribute": entry["attribute"],
                "value": entry["value"],
                "confidence": entry["confidence"]
            })
        
        return saved_entries
    except Exception as e:
        print(f"Error extracting knowledge: {e}")
        return []

def extract_knowledge_from_conversation(user_id: str, limit: int = 10) -> List[Dict]:
    """
    Extract knowledge from recent conversation history.
    
    Args:
        user_id: User ID to extract knowledge for
        limit: Maximum number of messages to analyze
        
    Returns:
        List of extracted knowledge entries
    """
    # Get recent messages
    messages = get_recent_messages(user_id, limit)
    
    # Prepare conversation history for analysis
    conversation = "\n".join([
        f"{msg['user_name']} ({msg['user_id']}): {msg['content']}"
        for msg in messages
    ])
    
    # Define system prompt for holistic analysis
    system_message = """
    Analyze this conversation history and extract factual knowledge about the user.
    
    Focus on:
    - Consistent patterns in preferences, beliefs, and behaviors
    - Biographical information (location, job, education)
    - Relationships and social connections
    - Skills, hobbies, and interests
    
    Return a JSON array of facts in this format:
    [
      {
        "attribute": "factual attribute name (e.g., favorite_color, hometown, occupation)",
        "value": "the value of this attribute",
        "confidence": confidence score from 0.0 to 1.0
      }
    ]
    
    Only include facts that have contextual support. Assign confidence scores based on:
    - Consistency across messages (higher confidence)
    - Recency (more recent statements get higher confidence)
    - Explicitness (direct statements vs implications)
    """
    
    # Call LLM API
    try:
        response = call_llm_api(system_message, conversation)
        extracted_knowledge = parse_knowledge_response(response)
        
        # Save knowledge to database
        saved_entries = []
        for entry in extracted_knowledge:
            knowledge_id = add_knowledge(
                user_id=user_id,
                attribute=entry["attribute"],
                value=entry["value"],
                confidence=entry["confidence"],
                source="conversation analysis"
            )
            saved_entries.append({
                "id": knowledge_id,
                "attribute": entry["attribute"],
                "value": entry["value"],
                "confidence": entry["confidence"]
            })
        
        return saved_entries
    except Exception as e:
        print(f"Error extracting knowledge from conversation: {e}")
        return []

def call_llm_api(system_message: str, user_message: str) -> str:
    """
    Call an LLM API to generate a response.
    
    Args:
        system_message: System message/instructions
        user_message: User message/content to analyze
        
    Returns:
        The LLM's response text
    """
    url = "https://openrouter.ai/api/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://hestia.ai",
        "X-Title": "Hestia Knowledge System"
    }
    
    data = {
        "model": "google/gemini-2.0-flash-exp:free",  # Use a reliable, cost-efficient model
        "messages": [
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message}
        ],
        "temperature": 0.1,  # Low temperature for more factual responses
        "max_tokens": 300
    }
    
    response = requests.post(url, headers=headers, json=data)
    response.raise_for_status()
    
    result = response.json()
    if "choices" in result and len(result["choices"]) > 0:
        return result["choices"][0]["message"]["content"]
    
    raise ValueError("Invalid API response format")

def parse_knowledge_response(response: str) -> List[Dict]:
    """
    Parse the LLM response to extract structured knowledge.
    
    Args:
        response: LLM response text
        
    Returns:
        List of knowledge dictionaries
    """
    # Look for JSON array in the response
    json_match = re.search(r'\[\s*\{.*\}\s*\]', response, re.DOTALL)
    
    if json_match:
        try:
            import json
            knowledge_list = json.loads(json_match.group(0))
            
            # Validate and clean up the knowledge entries
            valid_entries = []
            for entry in knowledge_list:
                if "attribute" in entry and "value" in entry and "confidence" in entry:
                    # Normalize attribute names (lowercase, underscores)
                    attribute = entry["attribute"].lower().replace(" ", "_")
                    
                    # Ensure confidence is a valid float between 0 and 1
                    confidence = float(entry["confidence"])
                    confidence = max(0.0, min(1.0, confidence))
                    
                    valid_entries.append({
                        "attribute": attribute,
                        "value": str(entry["value"]),
                        "confidence": confidence
                    })
            
            return valid_entries
        except Exception as e:
            print(f"Error parsing knowledge JSON: {e}")
    
    # Fallback: try to extract attributes and values using regex
    attributes = re.findall(r'attribute["\s:]+([^,"]+)', response)
    values = re.findall(r'value["\s:]+([^,"]+)', response)
    confidences = re.findall(r'confidence["\s:]+([0-9.]+)', response)
    
    # Match up attributes, values, and confidences
    fallback_entries = []
    for i in range(min(len(attributes), len(values))):
        confidence = float(confidences[i]) if i < len(confidences) else 0.5
        confidence = max(0.0, min(1.0, confidence))
        
        fallback_entries.append({
            "attribute": attributes[i].lower().replace(" ", "_").strip('"\''),
            "value": values[i].strip('"\''),
            "confidence": confidence
        })
    
    return fallback_entries