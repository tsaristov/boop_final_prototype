"""
Tool Installer Module for Hephestus

This module provides functions to:
1. Install tools from the library
2. Search for tools based on user needs
3. Manage installed tools
"""

import os
import shutil
import json
import logging
from typing import Dict, List, Optional, Any, Tuple
import re
from datetime import datetime

from tool_library.github_library import (
    search_tools, download_tool, get_tool_metadata,
    upload_tool, generate_metadata_for_tool, ToolMetadata
)
from llm_api import llm_api_call

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Constants
TOOLS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools")

def get_tool_path(tool_name: str, tools_dir: str = None) -> str:
    """
    Get the absolute path for a tool.
    
    Args:
        tool_name: Name of the tool
        tools_dir: Base directory for tools (default: TOOLS_DIR)
        
    Returns:
        Absolute path to the tool directory
    """
    if tools_dir is None:
        tools_dir = TOOLS_DIR
    
    return os.path.join(tools_dir, tool_name)

def find_and_install_tool(query: str, tags: List[str] = None, tools_dir: str = None) -> Tuple[str, Optional[str]]:
    """
    Find a tool matching the query and install it.
    
    Args:
        query: Search query describing the tool functionality
        tags: Optional list of tags to filter by
        tools_dir: Directory to install tools to (default: TOOLS_DIR)
        
    Returns:
        Tuple of (status message, installed tool name or None)
    """
    if tools_dir is None:
        tools_dir = TOOLS_DIR
    
    # Ensure tools directory exists
    os.makedirs(tools_dir, exist_ok=True)
    
    # First, try exact search
    matching_tools = search_tools(query=query, tags=tags)
    
    if not matching_tools:
        # No direct matches, use LLM to convert the query to better search terms
        improved_query = _generate_improved_search_terms(query)
        logger.info(f"Improved search query: {improved_query}")
        matching_tools = search_tools(query=improved_query, tags=tags)
    
    if not matching_tools:
        return "No matching tools found in the library.", None
    
    # Take the first match as the best tool
    best_match = matching_tools[0]
    tool_name = best_match["name"]
    
    # Download and install the tool
    success, message = download_tool(tool_name, tools_dir)
    
    if success:
        return f"Successfully installed tool '{tool_name}': {best_match['description']}", tool_name
    else:
        return f"Error installing tool: {message}", None

def install_tool_by_name(tool_name: str, tools_dir: str = None) -> Tuple[bool, str]:
    """
    Install a specific tool by name.
    
    Args:
        tool_name: Name of the tool to install
        tools_dir: Directory to install tools to (default: TOOLS_DIR)
        
    Returns:
        Tuple of (success status, message)
    """
    if tools_dir is None:
        tools_dir = TOOLS_DIR
    
    # Ensure tools directory exists
    os.makedirs(tools_dir, exist_ok=True)
    
    # Check if tool already exists
    tool_dir = get_tool_path(tool_name, tools_dir)
    if os.path.exists(tool_dir):
        return True, f"Tool '{tool_name}' is already installed."
    
    # Download and install the tool
    return download_tool(tool_name, tools_dir)

def list_installed_tools(tools_dir: str = None) -> List[Dict[str, Any]]:
    """
    List all installed tools with their metadata.
    
    Args:
        tools_dir: Directory containing installed tools (default: TOOLS_DIR)
        
    Returns:
        List of tool metadata dictionaries
    """
    if tools_dir is None:
        tools_dir = TOOLS_DIR
    
    if not os.path.exists(tools_dir):
        return []
    
    installed_tools = []
    
    # Iterate through directories in tools_dir
    for item in os.listdir(tools_dir):
        # Skip hidden directories and files
        if item.startswith(".") or item == "README.md":
            continue
        
        tool_dir = get_tool_path(item, tools_dir)
        if not os.path.isdir(tool_dir):
            continue
        
        # Look for metadata.json first
        metadata_path = os.path.join(tool_dir, "metadata.json")
        if os.path.exists(metadata_path):
            try:
                with open(metadata_path, "r") as f:
                    metadata = json.load(f)
                installed_tools.append(metadata)
                continue
            except json.JSONDecodeError:
                # If metadata is invalid, continue to generate it
                pass
        
        # Generate metadata from files
        metadata = generate_metadata_for_tool(tool_dir)
        installed_tools.append(metadata)
        
        # Save metadata
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)
    
    return installed_tools

def upload_tool_to_library(tool_name: str, tools_dir: str = None) -> Tuple[bool, str]:
    """
    Upload a locally created tool to the library.
    
    Args:
        tool_name: Name of the tool to upload
        tools_dir: Directory containing the tool (default: TOOLS_DIR)
        
    Returns:
        Tuple of (success status, message)
    """
    if tools_dir is None:
        tools_dir = TOOLS_DIR
    
    tool_dir = get_tool_path(tool_name, tools_dir)
    
    if not os.path.exists(tool_dir):
        return False, f"Tool '{tool_name}' not found in {tools_dir}."
    
    # Check if metadata.json exists, if not, generate it
    metadata_path = os.path.join(tool_dir, "metadata.json")
    if not os.path.exists(metadata_path):
        metadata = generate_metadata_for_tool(tool_dir)
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)
    
    # Upload the tool
    commit_message = f"Add/update tool: {tool_name}"
    return upload_tool(tool_dir, commit_message)

def _generate_improved_search_terms(query: str) -> str:
    """
    Use LLM to generate improved search terms from a user query.
    
    Args:
        query: User's search query
        
    Returns:
        Improved search terms
    """
    system_instructions = """
    You are a tool search optimizer. Given a user's search query about a tool they want to use,
    extract the essential functionality and generate 2-5 key search terms that would best match
    tools in a library. Focus on the core functionality rather than specific details.
    
    Return ONLY a list of search terms separated by commas.
    Example input: "I want a tool that can help me track my daily expenses and categorize them"
    Example output: expense tracker, budget, finance, accounting
    """
    
    try:
        response = llm_api_call(
            model="google/gemini-2.0-flash-lite-001",
            messages=[{"role": "user", "content": query}],
            system_instructions=system_instructions
        )
        
        if response and "choices" in response and response["choices"]:
            content = response["choices"][0]["message"]["content"]
            # Clean up and return the content
            return content.strip()
        
        return query  # Fallback to original query
    
    except Exception as e:
        logger.error(f"Error generating improved search terms: {str(e)}")
        return query  # Fallback to original query

def get_tool_functions_from_local(tool_name: str, tools_dir: str = None) -> List[Dict[str, Any]]:
    """
    Parse the functions from a locally installed tool.
    
    Args:
        tool_name: Name of the installed tool
        tools_dir: Directory containing installed tools (default: TOOLS_DIR)
        
    Returns:
        List of function metadata dictionaries
    """
    if tools_dir is None:
        tools_dir = TOOLS_DIR
    
    tool_dir = get_tool_path(tool_name, tools_dir)
    
    if not os.path.exists(tool_dir):
        return []
    
    # Check if metadata.json exists with functions
    metadata_path = os.path.join(tool_dir, "metadata.json")
    if os.path.exists(metadata_path):
        try:
            with open(metadata_path, "r") as f:
                metadata = json.load(f)
            if "functions" in metadata and metadata["functions"]:
                return metadata["functions"]
        except (json.JSONDecodeError, KeyError):
            pass
    
    # Parse functions.md
    functions_path = os.path.join(tool_dir, "functions.md")
    if not os.path.exists(functions_path):
        return []
    
    with open(functions_path, "r") as f:
        content = f.read()
    
    # Simple parsing of functions.md
    functions = []
    current_function = None
    
    for line in content.split("\n"):
        if line.startswith("## "):
            # New function definition
            if current_function:
                functions.append(current_function)
            
            function_name = line[3:].strip()
            current_function = {
                "name": function_name,
                "description": "",
                "parameters": []
            }
        elif line.lower().startswith("parameters:") and current_function:
            # Parameters section
            params_str = line[11:].strip()
            params = [p.strip() for p in params_str.split(",")]
            current_function["parameters"] = params
        elif current_function and line.strip():
            # Add description
            current_function["description"] += line.strip() + " "
    
    # Add the last function
    if current_function:
        functions.append(current_function)
    
    return functions

def auto_tag_tool(tool_dir: str) -> List[str]:
    """
    Automatically generate tags for a tool based on its files.
    
    Args:
        tool_dir: Directory containing the tool
        
    Returns:
        List of generated tags
    """
    tags = []
    
    # Read summary for content analysis
    summary_path = os.path.join(tool_dir, "summary.md")
    if os.path.exists(summary_path):
        with open(summary_path, "r") as f:
            summary = f.read()
        
        # Common categories to check for
        categories = {
            "data": ["data", "database", "csv", "excel", "json", "xml", "parse"],
            "communication": ["email", "message", "chat", "notification", "send"],
            "productivity": ["task", "todo", "reminder", "schedule", "calendar", "organize"],
            "web": ["http", "api", "request", "browser", "url", "website"],
            "file": ["file", "directory", "folder", "document", "read", "write"],
            "math": ["math", "calculate", "formula", "equation", "computation"],
            "utility": ["utility", "helper", "convert", "format", "transform"]
        }
        
        for category, keywords in categories.items():
            if any(keyword in summary.lower() for keyword in keywords):
                tags.append(category)
    
    # Check tool code for imports to detect functionality
    tool_py_path = os.path.join(tool_dir, "tool.py")
    if os.path.exists(tool_py_path):
        with open(tool_py_path, "r") as f:
            code = f.read()
        
        # Look for specific imports that suggest functionality
        import_tags = {
            "requests": "api",
            "pandas": "data",
            "numpy": "math",
            "matplotlib": "visualization",
            "tkinter": "gui",
            "flask": "web",
            "datetime": "time",
            "os": "system",
            "json": "json",
            "csv": "csv",
            "email": "email",
            "argparse": "cli"
        }
        
        for module, tag in import_tags.items():
            if re.search(rf"\bimport\s+{module}\b|\bfrom\s+{module}\s+import", code):
                tags.append(tag)
    
    # Remove duplicates and return
    return list(set(tags))