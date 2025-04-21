import os
import json
import time
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import requests

# Import Hephestus core components
from main import detect_tool, get_installed_tools
from intent_outcomes.create_tool.create_tool import tool_pipeline
from intent_outcomes.run_tool.run_tool import run_tool
from tool_library.installer import (
    find_and_install_tool, install_tool_by_name,
    list_installed_tools, upload_tool_to_library,
    get_tool_functions_from_local
)
from tool_library.github_library import search_tools

# Create FastAPI application
app = FastAPI(
    title="Hephestus API",
    description="API for tool detection, creation, installation and execution",
    version="1.0.0"
)

# Define request and response models
class MessageRequest(BaseModel):
    message: str
    user_name: str
    user_id: str
    
class ToolRequest(BaseModel):
    tool_name: str
    details: Optional[str] = None
    
class InstallToolRequest(BaseModel):
    tool_name: Optional[str] = None
    description: Optional[str] = None
    run_after_install: Optional[bool] = False
    
class SearchToolsRequest(BaseModel):
    query: Optional[str] = ""
    tags: Optional[List[str]] = None
    
class RunToolRequest(BaseModel):
    tool_name: str
    message: str
    args: Optional[Dict[str, Any]] = None

class IntentResponse(BaseModel):
    intent_type: str
    tool_name: Optional[str] = None
    details: Optional[str] = None
    repository_url: Optional[str] = None
    
class ApiResponse(BaseModel):
    status: str
    message: str
    data: Optional[Dict[str, Any]] = None
    execution_time: float

# Helper function for consistent response formatting
def create_response(status: str, message: str, data: Optional[Dict[str, Any]] = None, 
                   execution_time: Optional[float] = None) -> Dict[str, Any]:
    """Creates a standardized API response."""
    if execution_time is None:
        execution_time = 0.0
        
    return {
        "status": status,
        "message": message,
        "data": data,
        "execution_time": execution_time
    }

@app.get("/")
async def root():
    """Root endpoint returning API information."""
    return {"message": "Hephestus API - Tool Management System", 
            "version": "1.0.0",
            "endpoints": [
                "/detect-intent", 
                "/create-tool", 
                "/run-tool",
                "/tools",
                "/install-tool",
                "/search-tools",
                "/tool-functions/{tool_name}"
            ]}

@app.post("/detect-intent", response_model=ApiResponse)
async def ddetect_intent(request: MessageRequest):
    """
    Detects the intent from a user message and processes it accordingly.
    Always returns Apollo's response for tool-related intents.
    """
    start_time = time.time()
    try:
        # Process the message through intent detection
        response = detect_tool(
            message=request.message,
            user_name=request.user_name,
            user_id=request.user_id
        )
        
        total_execution_time = time.time() - start_time
        tool_execution_time = response.get("execution_time", 0)
        execution_time = total_execution_time + tool_execution_time
        
        # Prepare context and user info for Apollo API
        context = response.get("details", "")
        user_id = request.user_id
        user_name = request.user_name
        
        # Call Apollo API for all tool-related intents
        apollo_response = requests.post(
            "http://0.0.0.0:8001/generate",
            json={
                "user_id": user_id,
                "user_name": user_name,
                "message": request.message,
                "context": context
            }
        )
        apollo_response.raise_for_status()
        apollo_data = apollo_response.json()
        
        if "message" not in apollo_data:
            raise ValueError("Apollo API response is missing 'message' field.")
        
        # Always return Apollo's response
        return create_response(
            status="success",
            message=apollo_data["message"],
            data=apollo_data,
            execution_time=execution_time
        )
            
    except Exception as e:
        execution_time = time.time() - start_time
        return create_response(
            status="error",
            message=f"Error processing intent: {str(e)}",
            execution_time=execution_time
        )

# Run the API server when script is executed directly
if __name__ == "__main__":
    # Check if port is specified in environment variable, default to 8000
    port = int(os.environ.get("HEPHESTUS_API_PORT", 8003))
    
    # Get host from environment variable, default to 127.0.0.1
    host = os.environ.get("HEPHESTUS_API_HOST", "0.0.0.0")
    
    print(f"Starting Hephestus API server on {host}:{port}")
    uvicorn.run("api:app", host=host, port=port, reload=True)