# Step 1: Decide which function of the tool should be ran based on the user message
    # 1a: Check through the functions.md, and choose which function/s should be ran
    # 1b: Gather the nessesary information from the message, or cancel and ask for them to repeat with the required information
    # 1c: Run the tool with the nessesary information

import os
import importlib.util
import re
from typing import Any, Dict, List, Tuple

# Import tool path helper
from tool_library.installer import TOOLS_DIR, get_tool_path

def run_tool(tool_name: str, user_message: str) -> str:
    """
    Run the specified tool based on user input.

    Args:
        tool_name (str): The name of the tool to run.
        user_message (str): The message from the user containing the necessary information.
        
    Returns:
        str: The result of running the tool, or an error message if the tool could not be run.
    """
    try:
        # Normalize tool name (case insensitive, handle spaces/underscores)
        normalized_name = tool_name.lower().replace(" ", "_").strip()
        
        # Find tool directory by normalized name
        tool_dir = None
        for dir_name in os.listdir(TOOLS_DIR):
            if dir_name.lower().replace(" ", "_").strip() == normalized_name:
                tool_dir = get_tool_path(dir_name)
                break
                
        if not tool_dir:
            return f"Error: Tool '{tool_name}' not found. Please check the tool name or install it first."
            
        functions_md_path = os.path.join(tool_dir, "functions.md")
        code_path = os.path.join(tool_dir, "tool.py")
        requirements_path = os.path.join(tool_dir, "requirements.txt")

        # Check for required files
        if not os.path.exists(functions_md_path):
            return f"Error: functions.md not found for tool {tool_name}. The tool may be corrupted."

        if not os.path.exists(code_path):
            return f"Error: tool.py not found for tool {tool_name}. The tool may be corrupted."
            
        # Install requirements if they exist and haven't been installed yet
        if os.path.exists(requirements_path):
            try:
                # Create a marker file to track if requirements were installed
                marker_file = os.path.join(tool_dir, ".requirements_installed")
                if not os.path.exists(marker_file):
                    import subprocess
                    print(f"Installing requirements for {tool_name}...")
                    subprocess.run(["pip", "install", "-r", requirements_path], 
                                  check=True, capture_output=True)
                    # Create marker file to avoid reinstalling
                    with open(marker_file, 'w') as f:
                        f.write("installed")
            except Exception as e:
                print(f"Warning: Failed to install requirements: {str(e)}")

        # Load the tool's code with proper error handling
        try:
            spec = importlib.util.spec_from_file_location("tool_module", code_path)
            tool_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(tool_module)
        except Exception as e:
            import traceback
            return f"Error loading tool: {str(e)}\n{traceback.format_exc()}"

        # Parse functions.md to get function signatures
        functions = parse_functions_md(functions_md_path)
        if not functions:
            return f"Error: No functions defined for tool {tool_name}"

        # Determine which function to run based on user message
        function_to_run, args = determine_function_and_args(functions, user_message)

        if function_to_run:
            if not hasattr(tool_module, function_to_run):
                return f"Error: Function '{function_to_run}' is defined in documentation but not implemented in the tool code."
                
            try:
                # Call the function with the gathered arguments
                result = getattr(tool_module, function_to_run)(*args)
                return f"Result from {function_to_run}: {result}"
            except Exception as e:
                import traceback
                return f"Error running function {function_to_run}: {str(e)}\n{traceback.format_exc()}"
        else:
            # If no function found or arguments missing, provide helpful message
            function_list = "\n".join([f"- {f['name']}: {', '.join(f['parameters'])}" for f in functions])
            return f"No suitable function found to run. Available functions for {tool_name}:\n{function_list}"
    except Exception as e:
        import traceback
        return f"Unexpected error running tool {tool_name}: {str(e)}\n{traceback.format_exc()}"

def parse_functions_md(functions_md_path: str) -> List[Dict[str, Any]]:
    """
    Parse the functions.md file to extract function definitions and their details.

    Args:
        functions_md_path (str): Path to the functions.md file.

    Returns:
        List[Dict[str, Any]]: List of dictionaries containing function details.
    """
    functions = []
    with open(functions_md_path, 'r') as f:
        content = f.read()

    # Split content into function sections
    function_sections = re.split(r'##\s+', content)[1:]  # Skip the first split which is the header

    for section in function_sections:
        function_name = section.split('\n')[0].strip()
        # Extract parameters (assuming they are listed under "Parameters:")
        params_match = re.search(r'Parameters:\s*(.*?)(?=\n\s*\w+:|$)', section, re.DOTALL)
        params = params_match.group(1).strip().split(',') if params_match else []
        functions.append({
            'name': function_name,
            'parameters': [param.strip() for param in params]
        })

    return functions

def determine_function_and_args(functions: List[Dict[str, Any]], user_message: str) -> Tuple[str, List[Any]]:
    """
    Determine which function to run based on the user message and extract necessary arguments.

    Args:
        functions (List[Dict[str, Any]]): List of available functions and their parameters.
        user_message (str): The message from the user containing the necessary information.

    Returns:
        Tuple[str, List[Any]]: The name of the function to run and the arguments to pass.
    """
    from llm_api import llm_api_call
    import json
    
    # Use LLM to determine the most appropriate function
    system_instructions = """
    You are a function selection system. Analyze the user message and determine which function best matches their intent.
    Return ONLY a JSON object with:
    1. "function_name": The selected function name or null if none match
    2. "reason": A brief explanation of your choice
    Example: {"function_name": "add_event", "reason": "User wants to add a calendar event"}
    """
    
    function_names = [f['name'] for f in functions]
    function_descriptions = [f"{f['name']}: Parameters: {', '.join(f['parameters'])}" for f in functions]
    
    response = llm_api_call(
        model="google/gemini-2.0-flash-lite-001",
        messages=[{
            "role": "user", 
            "content": f"Select the most appropriate function for this user message: '{user_message}'\n\nAvailable functions:\n" + "\n".join(function_descriptions)
        }],
        system_instructions=system_instructions
    )
    
    try:
        content = response['choices'][0]['message']['content']
        result = json.loads(content)
        selected_function = result.get('function_name')
        
        if selected_function:
            # Find the function in our list
            for function in functions:
                if function['name'] == selected_function:
                    # Extract arguments for the selected function
                    args = extract_args_from_message(user_message, function['parameters'])
                    
                    # Check if any required arguments are missing
                    if None in args:
                        print(f"Missing arguments for function {function['name']}. Please provide values for all parameters.")
                        return None, []
                    
                    return function['name'], args
    except (KeyError, json.JSONDecodeError) as e:
        print(f"Error determining function: {e}")
    
    # Fallback to simpler keyword matching if LLM selection fails
    for function in functions:
        if function['name'].lower() in user_message.lower():
            args = extract_args_from_message(user_message, function['parameters'])
            if None not in args:  # Only return if we have all arguments
                return function['name'], args

    return None, []

def extract_args_from_message(user_message: str, parameters: List[str]) -> List[Any]:
    """
    Extract arguments from the user message based on the expected parameters.

    Args:
        user_message (str): The message from the user.
        parameters (List[str]): The list of expected parameters for the function.

    Returns:
        List[Any]: The extracted arguments.
    """
    from llm_api import llm_api_call
    import json
    import re

    if not parameters:
        return []
    
    # Try regex pattern matching for common parameter formats first (faster)
    args = []
    for param in parameters:
        # Convert parameter name to lowercase for case-insensitive matching
        param_lower = param.lower().strip()
        # Create patterns to match parameter values
        patterns = [
            rf'{param_lower}\s*[:=]\s*"([^"]+)"',  # param: "value"
            rf'{param_lower}\s*[:=]\s*\'([^\']+)\'',  # param: 'value'
            rf'{param_lower}\s*[:=]\s*(\w+)',  # param: value
            rf'{param_lower}\s+(is|as|of|for|to)\s+([^,.]+)',  # param is/as/of/for value
            rf'(?:use|with|set)\s+{param_lower}\s+(?:as|to|of)\s+([^,.]+)',  # use param as value
            rf'([^,.]+)\s+(?:for|as)\s+(?:the\s+)?{param_lower}'  # value for/as the param
        ]
        
        value = None
        for pattern in patterns:
            match = re.search(pattern, user_message.lower())
            if match:
                # Get the captured group (the actual value)
                value = match.group(1) if len(match.groups()) == 1 else match.group(2)
                args.append(value.strip())
                break
        
        if value is None:
            # If no match found through regex, fall back to LLM extraction
            system_instructions = f"""
            You are a parameter extraction system. Extract the value for the parameter '{param}' from the user message.
            If you cannot find a value, respond with null.
            Return ONLY a JSON object with a single key 'value' containing the extracted value or null.
            Example: {{"value": "extracted value"}} or {{"value": null}}
            """
            
            response = llm_api_call(
                model="google/gemini-2.0-flash-lite-001",
                messages=[{"role": "user", "content": f"Extract the value for parameter '{param}' from this message: {user_message}"}],
                system_instructions=system_instructions
            )
            
            try:
                content = response['choices'][0]['message']['content']
                extracted = json.loads(content)
                args.append(extracted['value'] if extracted['value'] is not None else None)
            except (KeyError, json.JSONDecodeError):
                args.append(None)
    
    return args

# Example usage
if __name__ == "__main__":
    tool_name = "Wardrobe Tool"  # Replace with the actual tool name
    user_message = "Please run the function to add an item to the wardrobe."  # Example user message
    run_tool(tool_name, user_message)