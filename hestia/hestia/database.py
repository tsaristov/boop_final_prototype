import sqlite3
import json
from datetime import datetime
import time
from typing import List, Dict, Any, Optional, Union

# Database configuration
DB_FILE = "hestia.db"

def get_db_connection():
    """Get a database connection with optimized settings."""
    conn = sqlite3.connect(DB_FILE)
    # Enable foreign keys
    conn.execute("PRAGMA foreign_keys = ON")
    # Better performance settings
    conn.execute("PRAGMA synchronous = NORMAL")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn

def initialize_db():
    """Create the database schema."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create tables
    cursor.executescript('''
    -- User Messages Table
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        user_name TEXT NOT NULL,
        content TEXT NOT NULL,
        timestamp TEXT NOT NULL
    );
    
    -- Create index on user_id for faster queries
    CREATE INDEX IF NOT EXISTS idx_messages_user_id ON messages(user_id);
    
    -- Knowledge Table - Simple and reliable
    CREATE TABLE IF NOT EXISTS knowledge (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,    -- The user this knowledge is about
        attribute TEXT NOT NULL,  -- The attribute (e.g., "favorite_color", "hobby", "birthplace")
        value TEXT NOT NULL,      -- The value of this attribute
        confidence REAL NOT NULL, -- Confidence score (0.0 to 1.0)
        source TEXT NOT NULL,     -- Source message ID or description
        timestamp TEXT NOT NULL,  -- When this knowledge was recorded
        -- Composite unique constraint to avoid duplicates for the same user and attribute
        UNIQUE(user_id, attribute)
    );
    
    -- Create index on user_id for faster knowledge retrieval
    CREATE INDEX IF NOT EXISTS idx_knowledge_user_id ON knowledge(user_id);
    
    -- Memory Tables - Separate for each level of memory
    CREATE TABLE IF NOT EXISTS short_term_memories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        summary TEXT NOT NULL,
        timestamp TEXT NOT NULL
    );
    
    CREATE TABLE IF NOT EXISTS mid_term_memories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        summary TEXT NOT NULL,
        timestamp TEXT NOT NULL
    );
    
    CREATE TABLE IF NOT EXISTS long_term_memory (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        content TEXT NOT NULL,
        timestamp TEXT NOT NULL
    );
    
    -- Core Memories Table
    CREATE TABLE IF NOT EXISTS core_memories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        description TEXT NOT NULL,
        importance INTEGER NOT NULL DEFAULT 5,
        timestamp TEXT NOT NULL
    );
    ''')
    
    conn.commit()
    conn.close()
    print("Database initialized successfully")

def add_message(user_id: str, user_name: str, content: str) -> int:
    """
    Add a message to the database.
    
    Args:
        user_id: Unique identifier for the user
        user_name: User's display name
        content: Message content
        
    Returns:
        The ID of the inserted message
    """
    timestamp = datetime.now().isoformat()
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "INSERT INTO messages (user_id, user_name, content, timestamp) VALUES (?, ?, ?, ?)",
        (user_id, user_name, content, timestamp)
    )
    
    message_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return message_id

def get_recent_messages(user_id: str = None, limit: int = 20) -> List[Dict]:
    """
    Get recent messages, optionally filtered by user.
    
    Args:
        user_id: If provided, only get messages from this user
        limit: Maximum number of messages to return
        
    Returns:
        List of message dictionaries
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if user_id:
        cursor.execute(
            "SELECT id, user_id, user_name, content, timestamp FROM messages WHERE user_id = ? ORDER BY id DESC LIMIT ?",
            (user_id, limit)
        )
    else:
        cursor.execute(
            "SELECT id, user_id, user_name, content, timestamp FROM messages ORDER BY id DESC LIMIT ?",
            (limit,)
        )
    
    messages = [
        {
            "id": row[0],
            "user_id": row[1],
            "user_name": row[2],
            "content": row[3],
            "timestamp": row[4]
        }
        for row in cursor.fetchall()
    ]
    
    conn.close()
    return messages

def add_knowledge(user_id: str, attribute: str, value: str, confidence: float, source: str) -> int:
    """
    Add or update knowledge about a user.
    
    Args:
        user_id: The user this knowledge is about
        attribute: The knowledge attribute (e.g., "hobby")
        value: The value of this attribute
        confidence: Confidence score (0.0 to 1.0)
        source: Source of this knowledge (message ID or description)
        
    Returns:
        ID of the inserted/updated knowledge entry
    """
    timestamp = datetime.now().isoformat()
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if we already have knowledge about this attribute for this user
    cursor.execute(
        "SELECT id, confidence FROM knowledge WHERE user_id = ? AND attribute = ?",
        (user_id, attribute)
    )
    
    existing = cursor.fetchone()
    
    if existing and existing[1] >= confidence:
        # We already have this knowledge with equal or higher confidence
        knowledge_id = existing[0]
    elif existing:
        # Update existing knowledge with higher confidence
        cursor.execute(
            "UPDATE knowledge SET value = ?, confidence = ?, source = ?, timestamp = ? WHERE id = ?",
            (value, confidence, source, timestamp, existing[0])
        )
        knowledge_id = existing[0]
    else:
        # Insert new knowledge
        cursor.execute(
            "INSERT INTO knowledge (user_id, attribute, value, confidence, source, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, attribute, value, confidence, source, timestamp)
        )
        knowledge_id = cursor.lastrowid
    
    conn.commit()
    conn.close()
    
    return knowledge_id

def get_knowledge_for_user(user_id: str) -> List[Dict]:
    """
    Get all knowledge entries for a specific user.
    
    Args:
        user_id: The user to get knowledge for
        
    Returns:
        List of knowledge dictionaries
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT id, attribute, value, confidence, source, timestamp FROM knowledge WHERE user_id = ? ORDER BY confidence DESC",
        (user_id,)
    )
    
    knowledge = [
        {
            "id": row[0],
            "attribute": row[1],
            "value": row[2],
            "confidence": row[3],
            "source": row[4],
            "timestamp": row[5]
        }
        for row in cursor.fetchall()
    ]
    
    conn.close()
    return knowledge

def add_memory(memory_type: str, content: str) -> int:
    """
    Add a memory to the specified memory table.
    
    Args:
        memory_type: "short", "mid", or "long"
        content: Memory content
        
    Returns:
        ID of the inserted memory
    """
    timestamp = datetime.now().isoformat()
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if memory_type == "short":
        cursor.execute(
            "INSERT INTO short_term_memories (summary, timestamp) VALUES (?, ?)",
            (content, timestamp)
        )
    elif memory_type == "mid":
        cursor.execute(
            "INSERT INTO mid_term_memories (summary, timestamp) VALUES (?, ?)",
            (content, timestamp)
        )
    elif memory_type == "long":
        # For long-term memory, we replace the existing content
        cursor.execute("DELETE FROM long_term_memory")
        cursor.execute(
            "INSERT INTO long_term_memory (content, timestamp) VALUES (?, ?)",
            (content, timestamp)
        )
    else:
        conn.close()
        raise ValueError(f"Invalid memory type: {memory_type}")
    
    memory_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return memory_id

def get_memories(memory_type: str) -> List[Dict]:
    """
    Get memories from the specified memory table.
    
    Args:
        memory_type: "short", "mid", or "long"
        
    Returns:
        List of memory dictionaries
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if memory_type == "short":
        cursor.execute("SELECT id, summary, timestamp FROM short_term_memories ORDER BY id DESC")
        memories = [{"id": row[0], "content": row[1], "timestamp": row[2]} for row in cursor.fetchall()]
    elif memory_type == "mid":
        cursor.execute("SELECT id, summary, timestamp FROM mid_term_memories ORDER BY id DESC")
        memories = [{"id": row[0], "content": row[1], "timestamp": row[2]} for row in cursor.fetchall()]
    elif memory_type == "long":
        cursor.execute("SELECT id, content, timestamp FROM long_term_memory ORDER BY id DESC LIMIT 1")
        result = cursor.fetchone()
        memories = [{"id": result[0], "content": result[1], "timestamp": result[2]}] if result else []
    else:
        conn.close()
        raise ValueError(f"Invalid memory type: {memory_type}")
    
    conn.close()
    return memories

def clear_memories(memory_type: str) -> None:
    """
    Clear all memories of the specified type.
    
    Args:
        memory_type: "short", "mid", or "long"
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if memory_type == "short":
        cursor.execute("DELETE FROM short_term_memories")
    elif memory_type == "mid":
        cursor.execute("DELETE FROM mid_term_memories")
    elif memory_type == "long":
        cursor.execute("DELETE FROM long_term_memory")
    else:
        conn.close()
        raise ValueError(f"Invalid memory type: {memory_type}")
    
    conn.commit()
    conn.close()

def add_core_memory(description: str, importance: int = 5) -> int:
    """
    Add a core memory.
    
    Args:
        description: Core memory description
        importance: Importance level (1-10)
        
    Returns:
        ID of the inserted core memory
    """
    timestamp = datetime.now().isoformat()
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "INSERT INTO core_memories (description, importance, timestamp) VALUES (?, ?, ?)",
        (description, importance, timestamp)
    )
    
    memory_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return memory_id

def get_core_memories(min_importance: int = 0) -> List[Dict]:
    """
    Get all core memories, optionally filtered by minimum importance.
    
    Args:
        min_importance: Minimum importance level (0-10, 0 means get all)
        
    Returns:
        List of core memory dictionaries
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if min_importance > 0:
        cursor.execute(
            "SELECT id, description, importance, timestamp FROM core_memories WHERE importance >= ? ORDER BY importance DESC",
            (min_importance,)
        )
    else:
        cursor.execute(
            "SELECT id, description, importance, timestamp FROM core_memories ORDER BY importance DESC"
        )
    
    memories = [
        {
            "id": row[0],
            "description": row[1],
            "importance": row[2],
            "timestamp": row[3]
        }
        for row in cursor.fetchall()
    ]
    
    conn.close()
    return memories

def delete_core_memory(memory_id: int) -> bool:
    """
    Delete a core memory.
    
    Args:
        memory_id: ID of the core memory to delete
        
    Returns:
        True if successful, False if the memory wasn't found
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM core_memories WHERE id = ?", (memory_id,))
    
    success = cursor.rowcount > 0
    conn.commit()
    conn.close()
    
    return success

def get_all_context(user_id: str) -> Dict[str, Any]:
    """
    Get all context for a user, including knowledge, memories, and recent messages.
    
    Args:
        user_id: User ID to get context for
        
    Returns:
        Dictionary with all context
    """
    # Get recent messages
    messages = get_recent_messages(limit=20)
    
    # Get user-specific knowledge
    knowledge = get_knowledge_for_user(user_id)
    
    # Get memories
    short_term = get_memories("short")
    mid_term = get_memories("mid")
    long_term = get_memories("long")
    
    # Get core memories
    core_memories = get_core_memories()
    
    return {
        "messages": messages,
        "knowledge": knowledge,
        "short_term_memories": short_term,
        "mid_term_memories": mid_term,
        "long_term_memory": long_term,
        "core_memories": core_memories
    }