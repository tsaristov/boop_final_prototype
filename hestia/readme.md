# Hestia: Knowledge and Memory System

Hestia provides the knowledge storage and memory management capabilities for the Boop AI assistant. It stores conversation history, extracts structured knowledge, manages different layers of memory (short, mid, long-term, core), and provides context to other systems.

## Core Functionality

*   **Message Storage:** Persistently stores user and bot messages in a SQLite database (`hestia.db`).
*   **Knowledge Extraction:** Uses an LLM to analyze messages and conversations, extracting factual information (preferences, demographics, etc.) about users. Stores this knowledge with confidence scores.
*   **Memory Management:** Implements a tiered memory system:
    *   **Short-Term:** Summarizes recent messages into concise memories when a threshold is met.
    *   **Mid-Term:** Condenses multiple short-term memories into more abstract summaries when a threshold is met.
    *   **Long-Term:** Integrates mid-term memories into a single, evolving narrative representing the bot's overall experience and knowledge.
    *   **Core Memories:** Extracts fundamental, identity-defining memories during the long-term update process, storing them separately with an importance score.
*   **Context Provision:** Provides a consolidated context package (recent messages, knowledge, all memory tiers) to other systems upon request.

## Architecture & Components

*   **`hestia/api.py`:** FastAPI application defining endpoints for adding messages, retrieving context, managing memories, and extracting knowledge.
*   **`hestia/database.py`:** Manages the SQLite database (`hestia.db`) connection and schema. Defines tables for `messages`, `knowledge`, `short_term_memories`, `mid_term_memories`, `long_term_memory`, and `core_memories`. Provides functions for CRUD operations on these tables.
*   **`hestia/knowledge.py`:** Contains logic for extracting structured knowledge from messages and conversations using an LLM (via `call_llm_api`).
*   **`hestia/memory.py`:** Implements the memory condensation pipeline. Includes functions to check thresholds (`check_memory_thresholds`), condense messages to short-term, short-term to mid-term, update long-term memory, and extract core memories, all utilizing an LLM.
*   **`main.py`:** Entry point for running the Hestia FastAPI server.
*   **`requirements.txt`:** Lists Python package dependencies.
*   **`hestia.db`:** SQLite database file storing all messages, knowledge, and memories.

## API Endpoints

*   **`POST /add-message`**:
    *   **Request Body:** `MessageRequest` (user\_id, user\_name, content)
    *   **Action:** Stores the message. Triggers background tasks for knowledge extraction and memory threshold checks.
*   **`POST /get-context`**:
    *   **Request Body:** `ContextRequest` (user\_id)
    *   **Response Body:** JSON containing `messages`, `knowledge`, `short_term_memories`, `mid_term_memories`, `long_term_memory`, `core_memories`, and a `text_context` representation.
    *   **Action:** Retrieves all relevant context for the specified user.
*   **`POST /extract-knowledge`**:
    *   **Request Body:** `KnowledgeRequest` (user\_id, limit)
    *   **Action:** Manually triggers knowledge extraction from recent messages for a user.
*   **`POST /summarize-memory`**:
    *   **Query Parameter:** `memory_type` ('short', 'mid', or 'long')
    *   **Action:** Manually triggers the specified memory condensation step.
*   **`POST /core-memories`**:
    *   **Query Parameter:** `min_importance` (optional)
    *   **Action:** Retrieves core memories, optionally filtered by importance.
*   **`POST /add-core-memory`**:
    *   **Request Body:** `CoreMemoryRequest` (description, importance)
    *   **Action:** Manually adds a core memory.
*   **`DELETE /core-memory/{memory_id}`**:
    *   **Action:** Deletes a specific core memory by its ID.

## Setup & Installation

1.  **Prerequisites:** Python 3.x
2.  **Clone Repository:** Hestia is part of the main Boop repository. Clone the parent repository.
3.  **Navigate to Directory:** `cd hestia`
4.  **Install Dependencies:** `pip install -r requirements.txt`
5.  **Environment Variables:** Create a `.env` file in the `hestia` directory or set environment variables:
    *   `OPENROUTER_API_KEY`: Your API key for the OpenRouter service (used for knowledge/memory LLM calls).
6.  **Database:** The SQLite database (`hestia.db`) will be automatically created and initialized on the first run via `hestia/database.py`.

## Running the System

```bash
uvicorn main:app --host 0.0.0.0 --port 8002 --reload
```
