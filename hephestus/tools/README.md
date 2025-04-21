# Hephestus Tools Directory

This directory contains the tools available to the Hephestus system. 

## Directory Structure

Each tool should be a subdirectory with the following structure:

```
tools/
  ├── tool_name/
  │   ├── tool.py           # Main tool implementation
  │   ├── functions.md      # Function definitions and parameters
  │   ├── documentation.md  # Full documentation
  │   └── summary.md        # Brief summary of the tool
```

## Adding New Tools

New tools are added by the create_tool module in the Hephestus system.