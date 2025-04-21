"""
Tool Library Package for Hephestus

This package provides functionality for:
1. Searching and installing tools from a GitHub-based library
2. Uploading user-created tools to the library
3. Managing installed tools
"""

from tool_library.github_library import (
    search_tools, download_tool, get_tool_metadata,
    upload_tool, generate_metadata_for_tool, ToolMetadata
)

from tool_library.installer import (
    find_and_install_tool, install_tool_by_name,
    list_installed_tools, upload_tool_to_library,
    get_tool_functions_from_local, auto_tag_tool
)