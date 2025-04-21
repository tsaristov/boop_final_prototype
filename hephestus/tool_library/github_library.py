"""
GitHub-based Tool Library for Hephestus

This module provides functions to:
1. Search for tools in a GitHub repository
2. Download tools from the repository
3. Upload new tools to the repository
4. Index and catalog available tools
"""

import os
import json
import base64
import tempfile
import shutil
import requests
import time
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# GitHub API configuration
GITHUB_API_URL = "https://api.github.com"
GITHUB_REPO_OWNER = os.environ.get("HEPHESTUS_GITHUB_OWNER", "tsaristov")
GITHUB_REPO_NAME = os.environ.get("HEPHESTUS_GITHUB_REPO", "hephestus-tools")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "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")

# Caching to reduce API calls
CACHE_TTL = 3600  # 1 hour
tools_cache = {}
last_cache_update = 0

# Tool metadata schema fields
METADATA_FIELDS = [
    "name", "description", "version", "author", "tags", 
    "created_at", "updated_at", "functions"
]

class ToolMetadata:
    """Tool metadata structure for the library."""
    def __init__(
        self,
        name: str,
        description: str,
        version: str = "1.0.0",
        author: str = "Hephestus",
        tags: List[str] = None,
        created_at: Optional[str] = None,
        updated_at: Optional[str] = None,
        functions: List[Dict[str, Any]] = None
    ):
        self.name = name
        self.description = description
        self.version = version
        self.author = author
        self.tags = tags or []
        self.created_at = created_at or datetime.now().isoformat()
        self.updated_at = updated_at or datetime.now().isoformat()
        self.functions = functions or []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metadata to dictionary for storage."""
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "author": self.author,
            "tags": self.tags,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "functions": self.functions
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ToolMetadata':
        """Create ToolMetadata instance from dictionary."""
        return cls(
            name=data.get("name", ""),
            description=data.get("description", ""),
            version=data.get("version", "1.0.0"),
            author=data.get("author", "Hephestus"),
            tags=data.get("tags", []),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
            functions=data.get("functions", [])
        )

def get_github_headers() -> Dict[str, str]:
    """Get headers for GitHub API requests."""
    headers = {
        "Accept": "application/vnd.github.v3+json"
    }
    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"
    return headers

def search_tools(query: str = "", tags: List[str] = None) -> List[Dict[str, Any]]:
    """
    Search for tools in the GitHub repository based on query and tags.
    
    Args:
        query: Search term to match against tool names and descriptions
        tags: List of tags to filter tools by
        
    Returns:
        List of matching tool metadata dictionaries
    """
    global tools_cache, last_cache_update
    
    # Check if cache is valid
    current_time = time.time()
    if current_time - last_cache_update < CACHE_TTL and tools_cache:
        logger.info("Using cached tool index")
        all_tools = tools_cache
    else:
        # Fetch fresh tool index
        try:
            all_tools = get_tool_index()
            tools_cache = all_tools
            last_cache_update = current_time
        except Exception as e:
            logger.error(f"Error fetching tool index: {str(e)}")
            return []
    
    # Filter tools based on query and tags
    matched_tools = []
    
    for tool in all_tools:
        # If query is provided, check if it matches name or description
        if query and query.lower() not in tool.get("name", "").lower() and query.lower() not in tool.get("description", "").lower():
            continue
        
        # If tags are provided, check if the tool has at least one matching tag
        if tags and not any(tag.lower() in [t.lower() for t in tool.get("tags", [])] for tag in tags):
            continue
        
        matched_tools.append(tool)
    
    return matched_tools

def get_tool_index() -> List[Dict[str, Any]]:
    """
    Get the full index of tools from the repository.
    
    Returns:
        List of tool metadata dictionaries
    """
    # Construct GitHub API request to list directories in tools folder
    url = f"{GITHUB_API_URL}/repos/{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}/contents/tools"
    headers = get_github_headers()
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            logger.error(f"GitHub API error: {response.status_code} - {response.text}")
            # Simulate empty repository if we can't access it
            return []
        
        directories = [item for item in response.json() if item["type"] == "dir"]
        tools = []
        
        # For each tool directory, get its metadata
        for directory in directories:
            tool_name = directory["name"]
            metadata = get_tool_metadata(tool_name)
            if metadata:
                tools.append(metadata)
        
        return tools
    
    except Exception as e:
        logger.error(f"Error getting tool index: {str(e)}")
        return []

def get_tool_metadata(tool_name: str) -> Optional[Dict[str, Any]]:
    """
    Get metadata for a specific tool.
    
    Args:
        tool_name: Name of the tool (directory name)
        
    Returns:
        Tool metadata dictionary or None if not found
    """
    url = f"{GITHUB_API_URL}/repos/{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}/contents/tools/{tool_name}/metadata.json"
    headers = get_github_headers()
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            logger.error(f"GitHub API error: {response.status_code} - {response.text}")
            return None
        
        # GitHub API returns the file content as base64 encoded string
        content = response.json()
        file_content = base64.b64decode(content["content"]).decode("utf-8")
        metadata = json.loads(file_content)
        
        # Validate metadata has required fields
        for field in METADATA_FIELDS:
            if field not in metadata:
                metadata[field] = "" if field not in ["tags", "functions"] else []
        
        return metadata
    
    except Exception as e:
        logger.error(f"Error getting tool metadata: {str(e)}")
        return None

def download_tool(tool_name: str, target_dir: str = None) -> Tuple[bool, str]:
    """
    Download a tool from the GitHub repository.
    
    Args:
        tool_name: Name of the tool to download
        target_dir: Directory to save the tool (default: tools dir)
        
    Returns:
        Tuple of (success status, message/error description)
    """
    if target_dir is None:
        target_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools")
    
    # Ensure the target directory exists
    os.makedirs(target_dir, exist_ok=True)
    
    tool_dir = os.path.join(target_dir, tool_name)
    
    # Check if tool already exists
    if os.path.exists(tool_dir):
        return True, f"Tool '{tool_name}' is already installed."
    
    try:
        # Create temporary directory for downloading
        with tempfile.TemporaryDirectory() as temp_dir:
            # Download all files in the tool directory
            if not _download_tool_files(tool_name, temp_dir):
                return False, f"Failed to download tool '{tool_name}'"
            
            # Create tool directory and copy files
            os.makedirs(tool_dir, exist_ok=True)
            
            # Copy all files from temp directory to tool directory
            for item in os.listdir(temp_dir):
                src = os.path.join(temp_dir, item)
                dst = os.path.join(tool_dir, item)
                if os.path.isdir(src):
                    shutil.copytree(src, dst)
                else:
                    shutil.copy2(src, dst)
            
        return True, f"Tool '{tool_name}' downloaded and installed successfully."
    
    except Exception as e:
        logger.error(f"Error downloading tool: {str(e)}")
        # Clean up any partial download
        if os.path.exists(tool_dir):
            shutil.rmtree(tool_dir)
        return False, f"Error downloading tool: {str(e)}"

def _download_tool_files(tool_name: str, target_dir: str) -> bool:
    """
    Download all files for a tool from GitHub.
    
    Args:
        tool_name: Name of the tool
        target_dir: Target directory to save files
        
    Returns:
        Boolean indicating success
    """
    url = f"{GITHUB_API_URL}/repos/{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}/contents/tools/{tool_name}"
    headers = get_github_headers()
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            logger.error(f"GitHub API error: {response.status_code} - {response.text}")
            return False
        
        files = response.json()
        
        # Download each file
        for file in files:
            if file["type"] == "file":
                file_url = file["download_url"]
                file_path = os.path.join(target_dir, file["name"])
                
                # Download file
                file_response = requests.get(file_url)
                if file_response.status_code == 200:
                    with open(file_path, "wb") as f:
                        f.write(file_response.content)
                else:
                    logger.error(f"Error downloading file {file['name']}: {file_response.status_code}")
            
            elif file["type"] == "dir":
                # Handle subdirectories (optional)
                subdir = os.path.join(target_dir, file["name"])
                os.makedirs(subdir, exist_ok=True)
                
                # Recursive call to download subdirectory
                _download_tool_files(f"{tool_name}/{file['name']}", subdir)
        
        return True
    
    except Exception as e:
        logger.error(f"Error downloading tool files: {str(e)}")
        return False

def upload_tool(tool_dir: str, commit_message: str = None) -> Tuple[bool, str]:
    """
    Upload a tool to the GitHub repository.
    
    Args:
        tool_dir: Directory containing the tool
        commit_message: Optional commit message
        
    Returns:
        Tuple of (success status, message/error description)
    """
    # Get tool name from directory name
    tool_name = os.path.basename(tool_dir)
    
    if not commit_message:
        commit_message = f"Add/update tool: {tool_name}"
    
    try:
        # Check if tool already exists to determine if this is an update
        url = f"{GITHUB_API_URL}/repos/{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}/contents/tools/{tool_name}"
        headers = get_github_headers()
        
        # List of files to upload
        files_to_upload = []
        
        # Add all files from the tool directory
        for root, _, files in os.walk(tool_dir):
            for file in files:
                # Skip any hidden files
                if file.startswith("."):
                    continue
                
                file_path = os.path.join(root, file)
                with open(file_path, "rb") as f:
                    content = f.read()
                
                # Calculate relative path to the tool directory
                rel_path = os.path.relpath(file_path, tool_dir)
                github_path = f"tools/{tool_name}/{rel_path}"
                
                # For subdirectories, ensure they exist
                if os.path.dirname(rel_path):
                    os.makedirs(os.path.join(tool_dir, os.path.dirname(rel_path)), exist_ok=True)
                
                files_to_upload.append({
                    "path": github_path,
                    "content": base64.b64encode(content).decode("utf-8")
                })
        
        # Upload each file
        for file_data in files_to_upload:
            file_path = file_data["path"]
            content = file_data["content"]
            
            # Check if file already exists
            file_url = f"{GITHUB_API_URL}/repos/{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}/contents/{file_path}"
            response = requests.get(file_url, headers=headers)
            
            if response.status_code == 200:
                # File exists, update it
                file_info = response.json()
                data = {
                    "message": commit_message,
                    "content": content,
                    "sha": file_info["sha"]
                }
            else:
                # File doesn't exist, create it
                data = {
                    "message": commit_message,
                    "content": content
                }
            
            # Make the API call to create/update the file
            update_response = requests.put(file_url, headers=headers, json=data)
            
            if update_response.status_code not in [200, 201]:
                logger.error(f"GitHub API error: {update_response.status_code} - {update_response.text}")
                return False, f"Error uploading file {file_path}: {update_response.text}"
        
        # Clear cache after upload
        global last_cache_update
        last_cache_update = 0
        
        return True, f"Tool '{tool_name}' uploaded successfully."
    
    except Exception as e:
        logger.error(f"Error uploading tool: {str(e)}")
        return False, f"Error uploading tool: {str(e)}"

def get_tool_functions(tool_name: str) -> List[Dict[str, Any]]:
    """
    Get the functions available in a tool.
    
    Args:
        tool_name: Name of the tool
        
    Returns:
        List of function descriptions
    """
    metadata = get_tool_metadata(tool_name)
    if metadata and "functions" in metadata:
        return metadata["functions"]
    return []

def generate_metadata_for_tool(tool_dir: str) -> Dict[str, Any]:
    """
    Generate metadata for a tool by examining its files.
    
    Args:
        tool_dir: Directory containing the tool
        
    Returns:
        Metadata dictionary
    """
    tool_name = os.path.basename(tool_dir)
    
    # Default metadata values
    metadata = {
        "name": tool_name,
        "description": "",
        "version": "1.0.0",
        "author": "Hephestus",
        "tags": [],
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "functions": []
    }
    
    # Read summary.md for description
    summary_path = os.path.join(tool_dir, "summary.md")
    if os.path.exists(summary_path):
        with open(summary_path, "r") as f:
            metadata["description"] = f.read().strip()
    
    # Parse functions.md for function definitions
    functions_path = os.path.join(tool_dir, "functions.md")
    if os.path.exists(functions_path):
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
        
        metadata["functions"] = functions
    
    return metadata

def create_github_tool_library(owner: str, repo: str, token: str) -> Tuple[bool, str]:
    """
    Initialize a new GitHub repository as a tool library.
    Used for first-time setup.
    
    Args:
        owner: GitHub username
        repo: Repository name
        token: GitHub personal access token
        
    Returns:
        Tuple of (success status, message/error description)
    """
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    # Check if repo already exists
    url = f"{GITHUB_API_URL}/repos/{owner}/{repo}"
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        return True, f"Repository '{owner}/{repo}' already exists."
    
    # Create new repository
    create_url = f"{GITHUB_API_URL}/user/repos"
    data = {
        "name": repo,
        "description": "Hephestus Tool Library - Repository of tools for the Hephestus API",
        "private": False,
        "has_issues": True,
        "has_projects": False,
        "has_wiki": False,
        "auto_init": True
    }
    
    response = requests.post(create_url, headers=headers, json=data)
    
    if response.status_code not in [200, 201]:
        return False, f"Error creating repository: {response.text}"
    
    # Create basic README
    readme_content = """# Hephestus Tool Library

A repository of tools for the Hephestus API.

## Structure

Each tool is stored in its own directory under `/tools` with the following structure:

- `tool.py` - The main tool implementation
- `functions.md` - Documentation of available functions
- `documentation.md` - Detailed documentation
- `summary.md` - Brief description of the tool
- `metadata.json` - Tool metadata
- `requirements.txt` (optional) - Dependencies

## Adding Tools

Tools can be added via the Hephestus API or by creating a pull request.
"""
    
    readme_url = f"{GITHUB_API_URL}/repos/{owner}/{repo}/contents/README.md"
    readme_data = {
        "message": "Initial commit: Add README",
        "content": base64.b64encode(readme_content.encode()).decode()
    }
    
    response = requests.put(readme_url, headers=headers, json=readme_data)
    
    if response.status_code not in [200, 201]:
        return False, f"Error creating README: {response.text}"
    
    # Create tools directory
    tools_url = f"{GITHUB_API_URL}/repos/{owner}/{repo}/contents/tools"
    tools_data = {
        "message": "Create tools directory",
        "content": base64.b64encode(b"# Tools Directory").decode()
    }
    
    response = requests.put(tools_url, headers=headers, json=tools_data)
    
    if response.status_code not in [200, 201]:
        return False, f"Error creating tools directory: {response.text}"
    
    return True, f"Repository '{owner}/{repo}' created successfully as a tool library."