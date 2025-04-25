# Apollo: Personality and Chat Core

Apollo serves as the primary personality and chat interaction layer for the Boop AI assistant system. It handles generating responses to user messages, incorporating personality, context, and ensuring a consistent character voice.

## Core Functionality

*   **Chat Response Generation:** Receives user messages and context, then generates appropriate responses using an external Language Model (LLM).
*   **Personality Integration:** Loads and applies the defined personality (`prompt.md`) to all LLM interactions.
*   **Context Handling:** Accepts context provided by other systems (like Hephaestus or Hestia) or fetches it directly from Hestia if needed.
*   **Message Logging:** Stores both user messages and bot responses in a local SQLite database (`apollo.db`) for history.
*   **Hestia Integration:** Sends messages (user and bot) to the Hestia system for long-term memory and knowledge processing via Hestia's `/add-message` endpoint.

## Architecture & Components

*   **`main.py`:** FastAPI application defining the `/generate` endpoint for chat requests. Orchestrates the interaction flow.
*   **`apollo/core.py`:** Contains the main chat logic (`chat_with_bot`), including loading the personality and structuring the LLM call.
*   **`apollo/database.py`:** Manages the SQLite database (`apollo.db`) connection, schema initialization (`messages` table), and message insertion. Also triggers sending messages to Hestia.
*   **`llm_api.py`:** Handles communication with the external LLM service (OpenRouter). Constructs the API request payload including messages, system instructions, and personality.
*   **`prompt.md`:** Defines the core personality, capabilities, limitations, and conversational style of the Boop assistant.
*   **`requirements.txt`:** Lists Python package dependencies.
*   **`apollo.db`:** SQLite database file for storing message history.

## API Endpoints

*   **`POST /generate`**:
    *   **Request Body:** `ChatRequest` (user\_id, user\_name, message, context)
    *   **Response Body:** `ChatResponse` (message)
    *   **Action:** Takes user input, generates a bot response using the LLM and personality, logs messages, sends messages to Hestia, and returns the bot's reply.

## Setup & Installation

1.  **Prerequisites:** Python 3.x
2.  **Clone Repository:** Apollo is part of the main Boop repository. Clone the parent repository.
3.  **Navigate to Directory:** `cd apollo`
4.  **Install Dependencies:** `pip install -r requirements.txt`
5.  **Environment Variables:** Create a `.env` file in the `apollo` directory or set environment variables:
    *   `OPENROUTER_API_KEY`: Your API key for the OpenRouter service.
6.  **Database:** The SQLite database (`apollo.db`) will be automatically created and initialized on the first run.

## Running the System

```bash
uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```
