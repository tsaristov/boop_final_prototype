from typing import List, Dict, Any, Optional
import os
import requests
from datetime import datetime
from dotenv import load_dotenv
from .database import (
    get_recent_messages,
    get_memories,
    add_memory,
    clear_memories,
    add_core_memory
)

# Load environment variables
load_dotenv()
API_KEY = os.getenv("OPENROUTER_API_KEY")

# Memory thresholds
THRESHOLDS = {
    "short": 20,  # Number of messages before creating short-term memory
    "mid": 5,     # Number of short-term memories before creating mid-term memory
    "long": 3     # Number of mid-term memories before updating long-term memory
}

def check_memory_thresholds() -> List[str]:
    """
    Check if any memory thresholds have been reached.
    
    Returns:
        List of memory types that need condensation
    """
    needs_condensation = []
    
    # Check messages → short-term
    messages = get_recent_messages(limit=THRESHOLDS["short"] + 1)
    if len(messages) >= THRESHOLDS["short"]:
        needs_condensation.append("short")
    
    # Check short-term → mid-term
    short_term = get_memories("short")
    if len(short_term) >= THRESHOLDS["mid"]:
        needs_condensation.append("mid")
    
    # Check mid-term → long-term
    mid_term = get_memories("mid")
    if len(mid_term) >= THRESHOLDS["long"]:
        needs_condensation.append("long")
    
    return needs_condensation

def condense_messages_to_short_term() -> Dict:
    """
    Condense recent messages into a short-term memory.
    
    Returns:
        Dictionary with the created memory information
    """
    # Get recent messages
    messages = get_recent_messages(limit=THRESHOLDS["short"])
    
    if not messages:
        return {"success": False, "error": "No messages to condense"}
    
    # Format messages for the LLM
    formatted_messages = "\n".join([
        f"{msg['user_name']} ({msg['user_id']}): {msg['content']}"
        for msg in messages
    ])
    
    # Create system prompt
    system_message = """
    Summarize this conversation into a concise paragraph.
    Focus on:
    - Key points discussed
    - Important information shared
    - Main topics and themes
    
    Keep the summary informative but brief.
    """
    
    try:
        # Call LLM API
        summary = call_llm_api(system_message, formatted_messages)
        
        # Add to short-term memory
        memory_id = add_memory("short", summary)
        
        # Clear the messages (in a real system, you might not want to delete them)
        # clear_messages()
        
        return {
            "success": True,
            "memory_id": memory_id,
            "content": summary,
            "type": "short_term"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

def condense_short_term_to_mid_term() -> Dict:
    """
    Condense short-term memories into a mid-term memory.
    
    Returns:
        Dictionary with the created memory information
    """
    # Get short-term memories
    memories = get_memories("short")
    
    if not memories:
        return {"success": False, "error": "No short-term memories to condense"}
    
    # Format memories for the LLM
    formatted_memories = "\n".join([
        f"Memory {i+1}: {memory['content']}"
        for i, memory in enumerate(memories)
    ])
    
    # Create system prompt
    system_message = """
    Condense these short-term memories into a single, cohesive mid-term memory.
    Focus on:
    - Patterns and connections between memories
    - Recurring themes or topics
    - Important details worth preserving
    
    Create a concise but comprehensive summary.
    """
    
    try:
        # Call LLM API
        summary = call_llm_api(system_message, formatted_memories)
        
        # Add to mid-term memory
        memory_id = add_memory("mid", summary)
        
        # Clear short-term memories
        clear_memories("short")
        
        return {
            "success": True,
            "memory_id": memory_id,
            "content": summary,
            "type": "mid_term"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

def update_long_term_memory() -> Dict:
    """
    Update the unified long-term memory from mid-term memories.
    Extracts core memories during the process.
    
    Returns:
        Dictionary with the updated memory information
    """
    # Get mid-term memories
    mid_term_memories = get_memories("mid")
    
    if not mid_term_memories:
        return {"success": False, "error": "No mid-term memories to process"}
    
    # Get existing long-term memory
    long_term_memory = get_memories("long")
    current_ltm = long_term_memory[0]["content"] if long_term_memory else ""
    
    # Format memories for the LLM
    if current_ltm:
        memory_context = f"Existing Long-Term Memory:\n{current_ltm}\n\nNew Mid-Term Memories to Incorporate:\n"
    else:
        memory_context = "Mid-Term Memories to Incorporate into Long-Term Memory:\n"
        
    memory_context += "\n".join([
        f"Memory {i+1}: {memory['content']}"
        for i, memory in enumerate(mid_term_memories)
    ])
    
    # Create system prompt for unified memory
    system_message = """
    Create or update the unified long-term memory by integrating these mid-term memories.
    
    If there's an existing long-term memory, weave the new information into it coherently.
    If this is the first long-term memory, create a comprehensive narrative.
    
    The long-term memory should:
    - Be written in paragraph form
    - Maintain narrative consistency
    - Preserve the most important information
    - Highlight patterns and significant events
    - Read like a coherent personal history
    
    Create a single, unified memory that evolves over time.
    """
    
    try:
        # Call LLM API for long-term memory
        updated_ltm = call_llm_api(system_message, memory_context)
        
        # Extract core memories
        core_memories = extract_core_memories(mid_term_memories, current_ltm)
        
        # Save core memories
        saved_core_memories = []
        for core_mem in core_memories:
            memory_id = add_core_memory(
                description=core_mem["description"],
                importance=core_mem["importance"]
            )
            saved_core_memories.append({
                "id": memory_id,
                "description": core_mem["description"],
                "importance": core_mem["importance"]
            })
        
        # Update long-term memory
        memory_id = add_memory("long", updated_ltm)
        
        # Clear mid-term memories
        clear_memories("mid")
        
        return {
            "success": True,
            "memory_id": memory_id,
            "content": updated_ltm,
            "type": "long_term",
            "core_memories": saved_core_memories
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

def extract_core_memories(mid_term_memories: List[Dict], long_term_memory: str = "") -> List[Dict]:
    """
    Extract core memories from mid-term memories and existing long-term memory.
    
    Args:
        mid_term_memories: List of mid-term memory dictionaries
        long_term_memory: Optional existing long-term memory content
        
    Returns:
        List of core memory dictionaries
    """
    # Format input for the LLM
    memory_content = "\n".join([
        f"Memory {i+1}: {memory['content']}"
        for i, memory in enumerate(mid_term_memories)
    ])
    
    if long_term_memory:
        memory_content += f"\n\nExisting Long-Term Memory:\n{long_term_memory}"
    
    # Create system prompt
    system_message = """
    Extract CORE MEMORIES that are vital to the bot's personality or identity.
    
    Core memories should be fundamental, defining experiences or beliefs that shape who the bot is.
    
    For each core memory:
    1. Provide a concise one-sentence description
    2. Rate its importance on a scale of 1-10
    
    Return your response in this JSON format:
    [
      {
        "description": "One-sentence core memory description",
        "importance": importance rating (1-10)
      }
    ]
    
    Focus on identifying memories that:
    - Define relationships with specific users
    - Establish core personality traits
    - Represent significant experiences or turning points
    - Contain fundamental beliefs or values
    
    Extract only truly significant core memories (typically 1-3 from a set of memories).
    """
    
    try:
        # Call LLM API
        response = call_llm_api(system_message, memory_content)
        
        # Parse core memories
        import re
        import json
        
        # Look for JSON array
        json_match = re.search(r'\[\s*\{.*\}\s*\]', response, re.DOTALL)
        
        if json_match:
            try:
                core_memories = json.loads(json_match.group(0))
                
                # Validate and normalize
                valid_memories = []
                for memory in core_memories:
                    if "description" in memory and "importance" in memory:
                        # Ensure importance is a valid integer between 1 and 10
                        importance = int(memory["importance"])
                        importance = max(1, min(10, importance))
                        
                        valid_memories.append({
                            "description": memory["description"],
                            "importance": importance
                        })
                
                return valid_memories
            except json.JSONDecodeError:
                # Fallback to regex parsing if JSON parsing fails
                pass
        
        # Fallback: try to extract core memories using regex
        descriptions = re.findall(r'description["\s:]+([^,"]+)', response)
        importances = re.findall(r'importance["\s:]+([0-9]+)', response)
        
        # Match descriptions with importances
        fallback_memories = []
        for i in range(min(len(descriptions), len(importances))):
            importance = int(importances[i])
            importance = max(1, min(10, importance))
            
            fallback_memories.append({
                "description": descriptions[i].strip('"\''),
                "importance": importance
            })
        
        return fallback_memories
    
    except Exception as e:
        print(f"Error extracting core memories: {e}")
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
        "X-Title": "Hestia Memory System"
    }
    
    data = {
        "model": "google/gemini-2.0-flash-exp:free",  # Use a reliable, cost-efficient model
        "messages": [
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message}
        ],
        "temperature": 0.2,  # Slightly higher temperature for more creative summarization
        "max_tokens": 500    # Allow more tokens for memory generation
    }
    
    response = requests.post(url, headers=headers, json=data)
    response.raise_for_status()
    
    result = response.json()
    if "choices" in result and len(result["choices"]) > 0:
        return result["choices"][0]["message"]["content"]
    
    raise ValueError("Invalid API response format")