# Orchestrates the tool creation pipeline.
# Step 1: Generate documentation files (documentation.md, functions.md, summary.md) based on intent detection.
# Step 2: Generate Python code (tool.py) based on the function definitions in functions.md.
# Step 3: Debug and test the generated code using the debug system.
# Step 4: Upload the tool to the GitHub-based tool library for future use.

import os
import json
import logging
from typing import Tuple

from intent_outcomes.create_tool.generate_docs import create_tool_definitions # Imports the function to generate documentation files.
from intent_outcomes.create_tool.generate_code import generate_code # Imports the function to generate Python code.
from intent_outcomes.create_tool.debug_code import debug_code  # Imports the function to debug the generated code.

# Import tool library functionality if available
try:
    from tool_library.installer import (
        generate_metadata_for_tool, upload_tool_to_library, auto_tag_tool
    )
    TOOL_LIBRARY_AVAILABLE = True
except ImportError:
    TOOL_LIBRARY_AVAILABLE = False

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def tool_pipeline(tool_name: str, details: str) -> str:
    """
    Executes the pipeline to create a new tool.

    This function takes a tool name and details as input, and then orchestrates the
    process of generating documentation, code, and debugging for the new tool.
    After successful creation, it uploads the tool to the library.

    Args:
        tool_name (str): The name of the tool to be created.
        details (str): A detailed description of the tool's functionality and purpose.
        
    Returns:
        str: A message describing the outcome of the tool creation process.
    """
    # Step 1: Generate documentation files
    create_tool_definitions(tool_name=tool_name, details=details)
    logger.info(f"Generated documentation for tool: {tool_name}")
    
    # Step 2: Generate Python code
    print("Writing tool code")
    generate_code(tool_name=tool_name)
    logger.info(f"Generated code for tool: {tool_name}")
    
    # Step 3: Debug and test the generated code
    print("Testing and debugging tool")
    debug_code(tool_name=tool_name)
    logger.info(f"Debugged code for tool: {tool_name}")
    
    # Step 4: Create metadata and upload to library
    try:
        if TOOL_LIBRARY_AVAILABLE:
            # Generate metadata for the tool
            from tool_library.installer import get_tool_path
            tool_dir = get_tool_path(tool_name)
            metadata = generate_metadata_for_tool(tool_dir)
            
            # Auto-generate tags for the tool
            tags = auto_tag_tool(tool_dir)
            metadata["tags"] = tags
            
            # Save metadata
            metadata_path = os.path.join(tool_dir, "metadata.json")
            with open(metadata_path, "w") as f:
                json.dump(metadata, f, indent=2)
            
            # Upload tool to library
            success, message = upload_tool_to_library(tool_name)
            
            if success:
                logger.info(f"Tool {tool_name} uploaded to library: {message}")
                return f"Tool '{tool_name}' created and uploaded to the library. You can now use it with: 'Use the {tool_name} tool to...'"
            else:
                logger.warning(f"Failed to upload tool to library: {message}")
                return f"Tool '{tool_name}' created successfully, but upload to library failed: {message}. You can still use it with: 'Use the {tool_name} tool to...'"
    except Exception as e:
        logger.error(f"Error in library integration: {str(e)}")
    
    # Return success even if upload fails
    return f"Tool '{tool_name}' created successfully. You can now use it with: 'Use the {tool_name} tool to...'"