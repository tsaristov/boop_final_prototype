# Hephaestus: Tool Management and Intent Routing

Hephaestus is the tool management and execution engine for the Boop AI assistant. It detects user intent related to tools, manages the lifecycle of tools (creation, installation, debugging), executes tools when requested, and interfaces with a GitHub-based tool library.

## Core Functionality

*   **Intent Detection:** Analyzes user messages to determine intent: use an installed tool, create a new tool, install a tool from the library, or no specific tool intent.
*   **Tool Execution:** Runs specified tools by dynamically loading their code (`tool.py`), installing necessary requirements (`requirements.txt`), and passing arguments extracted from the user message.
*   **Tool Creation Pipeline:** Orchestrates the creation of new tools based on user requests:
    *   Generates documentation (`documentation.md`, `functions.md`, `summary.md`) using an LLM.
    *   Generates Python code (`tool.py`) based on `functions.md` using an LLM.
    *   Automatically tests and debugs the generated code (`debug_code.py`) using an LLM.
    *   Generates metadata (`metadata.json`) including auto-tagging.
    *   Uploads the finished tool to the configured GitHub tool library.
*   **Tool Installation:** Searches the GitHub tool library for tools based on name or description, downloads them, and installs them locally into the `tools/` directory.
*   **Tool Library Management:** Interacts with a designated GitHub repository to search, download, and upload tools.

## Architecture & Components

*   **`api.py`:** FastAPI application exposing the core `/detect-intent` endpoint.
*   **`main.py`:** Contains the primary intent detection logic (`detect_tool`) which uses an LLM to classify user messages and route them to the appropriate action (run, create, install, or pass through). Manages caching for the installed tools list.
*   **`llm_api.py`:** Handles communication with the external LLM service (OpenRouter) for intent detection, code generation, debugging, etc.
*   **`intent_outcomes/`:** Contains modules for handling specific intents:
    *   **`create_tool/`:** Logic for the tool creation pipeline (`create_tool.py`, `generate_docs.py`, `generate_code.py`, `debug_code.py`).
    *   **`run_tool/run_tool.py`:** Logic for executing installed tools, including argument extraction and dynamic code loading.
*   **`tool_library/`:** Manages interaction with the tool library:
    *   **`github_library.py`:** Functions for searching, downloading, uploading, and retrieving metadata from the GitHub repository library. Uses the GitHub API.
    *   **`installer.py`:** Functions for installing tools locally, listing installed tools, managing requirements, generating metadata, and triggering uploads.
*   **`tools/`:** Local directory where tools are installed/created. Each tool resides in its own subdirectory.
*   **`requirements.txt`:** Lists Python package dependencies for Hephaestus itself.

## API Endpoints

*   **`POST /detect-intent`**:
    *   **Request Body:** `MessageRequest` (message, user\_name, user\_id)
    *   **Response Body:** `ApiResponse` (status, message, data, execution\_time)
    *   **Action:** Detects intent. If tool-related, performs the action (run, create, install) and gets a final response from Apollo. Returns Apollo's response.

## Setup & Installation

1.  **Prerequisites:** Python 3.x, Git command-line tool (for `GitPython`).
2.  **Clone Repository:** Hephaestus is part of the main Boop repository. Clone the parent repository.
3.  **Navigate to Directory:** `cd hephestus`
4.  **Install Dependencies:** `pip install -r requirements.txt`
5.  **Environment Variables:** Create a `.env` file in the `hephestus` directory or set environment variables:
    *   `OPENROUTER_API_KEY`: Your API key for the OpenRouter service.
    *   `GITHUB_TOKEN`: A GitHub Personal Access Token with `repo` scope for accessing/managing the tool library repository.
    *   `HEPHESTUS_GITHUB_OWNER`: The GitHub username or organization owning the tool library repository.
    *   `HEPHESTUS_GITHUB_REPO`: The name of the GitHub repository used as the tool library.
6.  **Tool Library:** Ensure the GitHub repository specified by the environment variables exists and is accessible with the provided token. It should ideally have a `tools/` directory.

## Running the System

```bash
uvicorn api:app --host 0.0.0.0 --port 8003 --reload
```
