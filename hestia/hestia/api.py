from typing import List, Dict, Any, Optional
from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel, Field
import asyncio
from datetime import datetime

from .database import (
    add_message,
    get_core_memories,
    add_core_memory,
    delete_core_memory,
    get_all_context
)

from .knowledge import (
    extract_knowledge_from_message,
    extract_knowledge_from_conversation
)

from .memory import (
    check_memory_thresholds,
    condense_messages_to_short_term,
    condense_short_term_to_mid_term,
    update_long_term_memory
)

# Define API models
class MessageRequest(BaseModel):
    user_id: str = Field(..., description="Unique ID for the user")
    user_name: str = Field(..., description="Display name for the user")
    content: str = Field(..., description="Message content")

class KnowledgeRequest(BaseModel):
    user_id: str = Field(..., description="User ID to extract knowledge for")
    limit: int = Field(10, description="Maximum number of messages to analyze")

class CoreMemoryRequest(BaseModel):
    description: str = Field(..., description="Core memory description")
    importance: int = Field(5, description="Importance level (1-10)", ge=1, le=10)

class ContextRequest(BaseModel):
    user_id: str = Field(..., description="User ID to get context for")

# Initialize FastAPI
app = FastAPI(
    title="Hestia Knowledge and Memory API",
    description="A simple and reliable knowledge and memory system for AI assistants",
    version="1.0.0"
)

# API endpoints
@app.post("/add-message")
async def add_message_endpoint(request: MessageRequest, background_tasks: BackgroundTasks):
    """
    Add a message and extract knowledge in the background.
    
    - Stores the message in the database
    - Extracts knowledge from the message
    - Checks if memory summarization is needed
    """
    # Add message to database
    message_id = add_message(request.user_id, request.user_name, request.content)
    
    # Extract knowledge and check memory thresholds in the background
    background_tasks.add_task(
        process_message_background,
        request.user_id,
        request.user_name,
        request.content,
        str(message_id)
    )

@app.post("/get-context")
async def get_context_endpoint(request: ContextRequest):
    """
    Get all context for a user, including:
    - Recent messages
    - User-specific knowledge
    - Short, mid, and long-term memories
    - Core memories
    """
    context = get_all_context(request.user_id)
    
    # Add formatted text representation
    text_context = format_context_as_text(context)
    
    return {
        "status": "success",
        "context": context,
        "text_context": text_context
    }

@app.post("/extract-knowledge")
async def extract_knowledge_endpoint(request: KnowledgeRequest):
    """
    Explicitly extract knowledge from recent conversation history.
    """
    knowledge_entries = extract_knowledge_from_conversation(request.user_id, request.limit)
    
    return {
        "status": "success",
        "knowledge": knowledge_entries,
        "count": len(knowledge_entries)
    }

@app.post("/summarize-memory")
async def summarize_memory_endpoint(memory_type: str):
    """
    Manually trigger memory summarization of a specific type.
    
    - "short": Condense messages to short-term memory
    - "mid": Condense short-term to mid-term memory
    - "long": Update long-term memory from mid-term memories
    """
    if memory_type == "short":
        result = condense_messages_to_short_term()
    elif memory_type == "mid":
        result = condense_short_term_to_mid_term()
    elif memory_type == "long":
        result = update_long_term_memory()
    else:
        return {
            "status": "error",
            "message": f"Invalid memory type: {memory_type}. Must be 'short', 'mid', or 'long'."
        }
    
    return {
        "status": "success",
        "result": result
    }

@app.post("/core-memories")
async def get_core_memories_endpoint(min_importance: int = 0):
    """
    Get all core memories, optionally filtered by minimum importance.
    """
    memories = get_core_memories(min_importance)
    
    return {
        "status": "success",
        "core_memories": memories,
        "count": len(memories)
    }

@app.post("/add-core-memory")
async def add_core_memory_endpoint(request: CoreMemoryRequest):
    """
    Manually add a core memory.
    """
    memory_id = add_core_memory(request.description, request.importance)
    
    return {
        "status": "success",
        "memory_id": memory_id,
        "message": f"Core memory added: {request.description} (Importance: {request.importance})"
    }

@app.delete("/core-memory/{memory_id}")
async def delete_core_memory_endpoint(memory_id: int):
    """
    Delete a core memory.
    """
    success = delete_core_memory(memory_id)
    
    if success:
        return {
            "status": "success",
            "message": f"Core memory with ID {memory_id} deleted"
        }
    else:
        return {
            "status": "error",
            "message": f"Core memory with ID {memory_id} not found"
        }

# Background processing functions
async def process_message_background(user_id: str, user_name: str, content: str, message_id: str):
    """Process a message in the background, extracting knowledge and checking memory thresholds."""
    # Extract knowledge from the message
    knowledge_entries = extract_knowledge_from_message(
        user_id=user_id,
        message=content,
        source=f"message_{message_id}",
        user_name=user_name
    )
    
    # Check if any memory thresholds have been reached
    needs_condensation = check_memory_thresholds()
    
    # Perform memory condensation if needed
    for memory_type in needs_condensation:
        if memory_type == "short":
            condense_messages_to_short_term()
        elif memory_type == "mid":
            condense_short_term_to_mid_term()
        elif memory_type == "long":
            update_long_term_memory()

# Helper functions
def format_context_as_text(context: Dict) -> str:
    """Format context dictionary as readable text."""
    sections = []
    
    # Format core memories
    if context.get("core_memories"):
        core_mem_section = ["## Core Memories"]
        for mem in context["core_memories"]:
            core_mem_section.append(f"- {mem['description']} (Importance: {mem['importance']})")
        sections.append("\n".join(core_mem_section))
    
    # Format user knowledge
    if context.get("knowledge"):
        knowledge_section = ["## User Knowledge"]
        for k in context["knowledge"]:
            knowledge_section.append(f"- {k['attribute']}: {k['value']} (Confidence: {k['confidence']})")
        sections.append("\n".join(knowledge_section))
    
    # Format long-term memory
    if context.get("long_term_memory") and context["long_term_memory"]:
        ltm_section = ["## Long-Term Memory"]
        ltm_section.append(context["long_term_memory"][0]["content"])
        sections.append("\n".join(ltm_section))
    
    # Format mid-term memories
    if context.get("mid_term_memories"):
        mid_term_section = ["## Mid-Term Memories"]
        for mem in context["mid_term_memories"]:
            mid_term_section.append(f"- {mem['content']}")
        sections.append("\n".join(mid_term_section))
    
    # Format short-term memories
    if context.get("short_term_memories"):
        short_term_section = ["## Short-Term Memories"]
        for mem in context["short_term_memories"]:
            short_term_section.append(f"- {mem['content']}")
        sections.append("\n".join(short_term_section))
    
    # Format recent messages
    if context.get("messages"):
        messages_section = ["## Recent Messages"]
        for msg in context["messages"]:
            messages_section.append(f"{msg['user_name']} ({msg['user_id']}): {msg['content']}")
        sections.append("\n".join(messages_section))
    
    # Combine all sections
    return "\n\n".join(sections)