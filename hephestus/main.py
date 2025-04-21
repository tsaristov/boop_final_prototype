import json
import os
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Optional, Any
from functools import lru_cache

from llm_api import llm_api_call
from intent_outcomes.create_tool.create_tool import tool_pipeline
from intent_outcomes.run_tool.run_tool import run_tool
from tool_library.installer import (
    find_and_install_tool, install_tool_by_name,
    upload_tool_to_library, TOOLS_DIR
)

import uvicorn

# Constants
TOOLS_CACHE_TTL = 300  # Cache tool list for 5 minutes

# Initialize cache for tool listing
last_tools_update = 0
tools_cache = []

def get_installed_tools(force_refresh: bool = False) -> List[str]:
    """
    Get list of installed tools and their summaries with caching for performance.
    
    Args:
        force_refresh: Force refresh the cache even if not expired
        
    Returns:
        List of tool names with their summaries
    """
    global last_tools_update, tools_cache
    
    # Check if cache is valid
    current_time = time.time()
    if (not force_refresh and 
        tools_cache and 
        current_time - last_tools_update < TOOLS_CACHE_TTL):
        return tools_cache
    
    installed_tools = []
    
    if os.path.exists(TOOLS_DIR):
        # Get all tool directories
        tool_dirs = [
            d for d in os.listdir(TOOLS_DIR) 
            if os.path.isdir(os.path.join(TOOLS_DIR, d)) and not d.startswith(".")
        ]
        
        # Process tool summaries in parallel for performance
        with ThreadPoolExecutor(max_workers=min(10, len(tool_dirs) or 1)) as executor:
            future_to_tool = {
                executor.submit(get_tool_summary, tool_name): tool_name 
                for tool_name in tool_dirs
            }
            
            for future in future_to_tool:
                tool_name = future_to_tool[future]
                try:
                    summary = future.result()
                    if summary:
                        installed_tools.append(f"{tool_name}:\n{summary}")
                except Exception as e:
                    print(f"Error processing tool {tool_name}: {e}")
    
    # Update cache
    tools_cache = installed_tools
    last_tools_update = current_time
    
    return installed_tools

def get_tool_summary(tool_name: str) -> Optional[str]:
    """
    Get summary for a specific tool.
    
    Args:
        tool_name: Name of the tool
        
    Returns:
        Tool summary or None if summary doesn't exist
    """
    tool_path = os.path.join(TOOLS_DIR, tool_name)
    summary_path = os.path.join(tool_path, "summary.md")
    
    if os.path.exists(summary_path):
        try:
            with open(summary_path, 'r') as f:
                return f.read().strip()
        except Exception:
            return None
    
    return None

@lru_cache(maxsize=32)
def get_tools_list() -> str:
    """
    Get formatted list of installed tools for LLM context.
    Uses caching for performance improvement.
    
    Returns:
        Formatted string containing all tools and their summaries
    """
    installed_tools = get_installed_tools()
    return "\n---\n".join(f"{i+1}. {tool}" for i, tool in enumerate(installed_tools))

def detect_tool(message: str, user_name: str, user_id: str) -> Dict[str, Any]:
    """
    Analyze user message to detect tool-related intents and handle appropriately.
    
    Args:
        message: User's message
        user_name: User's name
        user_id: User's ID
        
    Returns:
        Dictionary containing the intent detection results and any tool output
    """
    # Get updated tools list
    tools_list = get_tools_list()
    
    system_instructions = f"""
        You are an expert at detecting user intents related to tool usage, installation, and creation.

        **Task:**
        Analyze the user's message and determine if they are:
        1. Explicitly requesting to use or create a tool
        2. Asking to install or find a tool
        3. Having a general conversation
        
        **Intent Types:**
        - USE_INSTALLED_TOOL: User EXPLICITLY asks to use/run/execute a specific tool
          Example: "Can you use the weather tool to check the forecast?"
        
        - REQUEST_TOOL_CREATION: User EXPLICITLY asks to create/make/build a new tool
          Example: "Can you create a tool that converts currencies?"
        
        - INSTALL_TOOL: User EXPLICITLY asks to install, find, or get a tool
          Example: "Install a calendar tool" or "Find a tool for parsing JSON"
          
        - REQUEST_UNINSTALLED_TOOL: User tries to use a tool that isn't installed, but is potentially a tool that can be installed or created
          Example: "Can you check the stock price of AAPL" (when stock_price isn't installed)
        
        - NO_TOOL_INTENT: User is having a general conversation or asking questions
          Example: "How are you today?" or "Remember what we talked about earlier?"

        **Important Rules:**
        - Default to NO_TOOL_INTENT unless the user EXPLICITLY mentions using, installing, or creating a tool
        - Look for clear action words like "use", "install", "find", "create", "make", "build", "run" in relation to tools
        - If user wants to "install" or "find" a tool, use INSTALL_TOOL intent
        - General questions about capabilities or casual conversation = NO_TOOL_INTENT
        - If user message specifies running a command or action with a tool that isn't in the list, use REQUEST_UNINSTALLED_TOOL
        
        ---
        
        **Available Tools**
        {tools_list}

        ---
        **Output Format:**
        Return ONLY a JSON object:
        {{
            "intent_type": "**Intent Type**",
            "tool_name": "**Tool name, or null**",
            "details": "**Brief sentence of details about what the tool should do**",
            "run_after_install": boolean (true if the user wants to run the tool after installing it)
        }}
    """

    # Use a more appropriate model based on task complexity
    response = llm_api_call(
        model="openai/gpt-4.1-nano",
        messages=[{"role": "user", "content": message}],
        system_instructions=system_instructions
    )

    message_content = response["choices"][0]["message"]["content"]
    
    try:
        parsed = json.loads(message_content)
        
        intent_type = parsed["intent_type"]
        tool_name = parsed.get("tool_name")
        details = parsed.get("details", "")
        run_after_install = parsed.get("run_after_install", False)
        
        # Execute appropriate action based on intent
        if intent_type == "USE_INSTALLED_TOOL":
            start_time = time.time()
            tool_output = run_tool(tool_name, message)
            execution_time = time.time() - start_time
            
            return {
                "intent_type": intent_type,
                "tool_name": tool_name,
                "content": tool_output,
                "execution_time": execution_time
            }
        
        elif intent_type == "INSTALL_TOOL":
            start_time = time.time()
            
            # Try to find and install the tool from the library
            if tool_name and tool_name != "null":
                # Specific tool name provided
                success, message = install_tool_by_name(tool_name)
                if success:
                    install_result = f"Successfully installed tool '{tool_name}'"
                    installed_tool_name = tool_name
                else:
                    # If direct installation fails, try searching by description
                    install_result, installed_tool_name = find_and_install_tool(details)
            else:
                # Search based on description
                install_result, installed_tool_name = find_and_install_tool(details)
            
            execution_time = time.time() - start_time
            
            # If tool was successfully installed and user wants to run it
            if installed_tool_name and run_after_install:
                tool_output = run_tool(installed_tool_name, message)
                return {
                    "intent_type": "INSTALL_AND_RUN",
                    "tool_name": installed_tool_name,
                    "content": f"{install_result}\n\nTool output:\n{tool_output}",
                    "execution_time": execution_time
                }
            
            return {
                "intent_type": intent_type,
                "tool_name": installed_tool_name,
                "content": install_result,
                "execution_time": execution_time
            }
        
        elif intent_type in ["REQUEST_TOOL_CREATION", "REQUEST_UNINSTALLED_TOOL"]:
            start_time = time.time()
            
            # First check if a matching tool already exists in the library
            install_result, installed_tool_name = find_and_install_tool(details)
            
            if installed_tool_name:
                # A matching tool was found and installed
                execution_time = time.time() - start_time
                
                # If the user originally wanted to run the tool, do that too
                if run_after_install:
                    tool_output = run_tool(installed_tool_name, message)
                    return {
                        "intent_type": "INSTALL_AND_RUN",
                        "tool_name": installed_tool_name,
                        "content": f"{install_result}\n\nTool output:\n{tool_output}",
                        "execution_time": execution_time
                    }
                
                return {
                    "intent_type": "INSTALL_TOOL",
                    "tool_name": installed_tool_name,
                    "content": install_result,
                    "execution_time": execution_time
                }
            
            # No matching tool found, create a new one
            tool_pipeline_outcome = tool_pipeline(tool_name, details)
            
            # Try to upload the newly created tool to the library
            try:
                success, upload_message = upload_tool_to_library(tool_name)
                if success:
                    tool_pipeline_outcome += f"\n\nTool has been uploaded to the library for future use."
            except Exception as e:
                # Upload failure shouldn't break the tool creation flow
                pass
            
            execution_time = time.time() - start_time
            
            return {
                "intent_type": intent_type,
                "tool_name": tool_name,
                "content": tool_pipeline_outcome,
                "execution_time": execution_time
            }
        
        elif intent_type == "NO_TOOL_INTENT":
            return {
                "intent_type": intent_type,
                "tool_name": None,
                "content": "",
                "execution_time": 0
            }
        
        else:
            return {
                "intent_type": "ERROR",
                "tool_name": None,
                "content": f"Error: Unknown intent type: {intent_type}",
                "execution_time": 0
            }
            
    except (json.JSONDecodeError, KeyError) as e:
        return {
            "intent_type": "ERROR",
            "tool_name": None,
            "content": f"Error processing your request: {str(e)}",
            "execution_time": 0
        }