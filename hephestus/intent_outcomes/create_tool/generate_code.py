import os # Module for interacting with the operating system, mainly for file path manipulation.
import re # Module for regular expressions, used for pattern matching and code extraction.
from llm_api import llm_api_call # Imports the function to call the Language Model API.

def strip_code_fences(code: str) -> str:
    """
    Removes markdown code block markers (```) and content outside of them.

    This function uses regular expressions to find and extract the content within markdown
    code fences (```python ... ``` or ``` ... ```). This is useful for cleaning up responses
    from LLMs that often include code blocks in markdown format.

    Args:
        code (str): A string that may contain markdown code blocks.

    Returns:
        str: The code content extracted from within the code fences, or the original string
             stripped of leading/trailing whitespace if no code fences are found.
    """
    # Find content between code fences using regex
    match = re.search(r'```(?:python)?\s*(.*?)\s*```', code, re.DOTALL) # Regex to find code blocks, optionally starting with ```python.
    if match:
        # If code fences found, return only the content between them
        return match.group(1).strip() # Returns the captured group (content inside fences), removing leading/trailing whitespace.
    # If no code fences found, return the original string stripped
    return code.strip() # If no fences, returns the original string with leading/trailing whitespace removed.

def generate_code(tool_name: str) -> None:
    """
    Generates Python code for a given tool based on its documentation and function definitions.

    This function reads the 'functions.md' and 'documentation.md' files for a specified tool,
    constructs a prompt for an LLM, and uses the LLM to generate Python code for the tool.
    The generated code is then saved to 'tool.py' in the tool's directory, and a 'requirements.txt'
    file is created based on imported libraries in the generated code.

    Args:
        tool_name (str): The name of the tool for which to generate code. This is used to locate
                         the tool's documentation files and where to save the generated code.
    """

    tool_dir = os.path.join("tools", tool_name) # Constructs the path to the tool's directory.
    functions_md_path = os.path.join(tool_dir, "functions.md") # Path to the functions documentation file.
    documentation_md_path = os.path.join(tool_dir, "documentation.md") # Path to the general documentation file.

    if not os.path.exists(functions_md_path): # Checks if functions.md exists.
        print(f"Error: functions.md not found for tool {tool_name}")
        return

    if not os.path.exists(documentation_md_path): # Checks if documentation.md exists.
        print(f"Error: documentation.md not found for tool {tool_name}")
        return

    with open(functions_md_path, "r") as f: # Opens and reads the content of functions.md.
        functions_md_content = f.read()

    with open(documentation_md_path, "r") as f: # Opens and reads the content of documentation.md.
        documentation_md_content = f.read()

    # 2a: Generate code based on functions.md (with documentation.md as context)
    system_instructions = """
        You are an expert python software developer tasked with generating the code for a tool.

        **Task:**
        Generate the complete Python code for the tool based on the provided function definitions and documentation.

        **Input:**
        - **functions.md:** Contains a list of required functions with their signatures, purpose, logic, parameters, return values, and error handling.
        - **documentation.md:** Provides overall context, use cases, and example scenarios for the tool.

        **Instructions:**
        1.  Carefully read and understand the function definitions in `functions.md`.
        2.  Use the `documentation.md` file to understand the overall purpose and usage of the tool.
        3.  Generate clean, well-documented Python code that implements all the functions defined in `functions.md`.
        4.  Ensure that the code includes proper docstrings, error handling, and adheres to best practices.
        5.  Any code that requires the input of the user will be provided, please do not do any code involving input(), and put it direclty in the function (i.e: def function(req_info1, req_info2, req_info3):).
        6.  Please include progress messages in the code, so the user knows what's happening with the tool process.
        7.  Prioritize function and efficiency.
        8.  If the tool requires external libraries, use them and add them to a `requirements.txt` file.
            6a. Be creative with the libraries you choose, so you don't overrely on LLM APIs.
        9.  Use SQLite for database operations when needed.
        10.  Use ```from llm_api import llm_api_call``` for LLM interactions when needed.
            10a. Below is the code of llm_api:
            ```
                import os
                import requests
                from fastapi import HTTPException
                from dotenv import load_dotenv

                # Load environment variables from .env if available
                load_dotenv()
                OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

                def llm_api_call(model: str, messages: list, system_instructions: str = None, personality: str = None):
                    try:
                        # If system instructions are provided, include them first
                        system_message_content = system_instructions if system_instructions else ""

                        # If personality is provided, append it after system instructions, otherwise, leave it out
                        if personality:
                            system_message_content += f" Your personality: {personality}"

                        # Create the system message with the prioritized instructions
                        system_message = {
                            "role": "system",
                            "content": system_message_content
                        }

                        # Add the system message to the top of the messages list
                        messages = [system_message] + messages

                        # Make the API request
                        response = requests.post(
                            url="https://openrouter.ai/api/v1/chat/completions",
                            headers={
                                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                                "Content-Type": "application/json"
                            },
                            json={
                                "model": model,
                                "messages": messages
                            }
                        )
                        response.raise_for_status()
                        return response.json()
                    except requests.exceptions.RequestException as e:
                        raise HTTPException(status_code=500, detail=str(e))
            ```
            10b. DO NOT WRITE YOUR OWN llm_api_call FUNCTION. IMPORT THE ONE I HAVE PROVIDED TO YOU ABOVE, AND USE IT FROM THE IMPORT.
        11.  All functions should be public.
        12. At the end of the code, you must write a debug_testing function that test each function
            12a. For each function, there should me multiple calls which contain appropriate test arguments that the function can use.
                12a_I. The functions should enter the values to test automatically, without user involvment.
                12a_II. There should be a "success" function(s) which should contain arguments that ensure the function works as intended
                12a_III. There should be an "error" function which should contain arguments that create errors for the function
        13. Add it to the bottom of the file

        **Output Format:**
        Return the complete Python code for the tool, and only the code, nothing else. Do not include any introductory or concluding text.  Do not use markdown formatting (e.g., ```python ... ```). Just return the raw Python code.
        *Example Output:*
        <code>
    """

    code_generation_prompt = f"""
        Generate the Python code for the tool: {tool_name}

        Here is the tool's functions.md:
        {functions_md_content}

        Here is the tool's documentation.md:
        {documentation_md_content}
    """

    code_generation_response = llm_api_call( # Calls the LLM API to generate the tool code.
        model="google/gemini-2.0-flash-001", # Specifies the LLM model.
        messages=[{"role": "user", "content": code_generation_prompt}], # The user prompt for code generation.
        system_instructions=system_instructions # System instructions to guide the LLM.
    )

    if isinstance(code_generation_response, dict) and 'choices' in code_generation_response: # Handles different possible response structures from the LLM API.
        generated_code = code_generation_response['choices'][0]['message']['content']
    elif isinstance(code_generation_response, dict) and 'content' in code_generation_response:
        generated_code = code_generation_response['content']
    else:
        generated_code = str(code_generation_response)

    # Extract python code
    generated_code = strip_code_fences(generated_code) # Removes markdown code fences from the generated code.

    # 2b: Put all the code in one file
    code_file_path = os.path.join(tool_dir, f"tool.py") # Path to save the generated Python code file.
    with open(code_file_path, "w") as f: # Opens the file in write mode and saves the generated code.
        f.write(generated_code)

    # Extract libraries
    libs = re.findall(r"import\s+(\w+)|from\s+(\w+)", generated_code) # Uses regex to find import statements and extract library names.

    # Create a set to store unique library names
    unique_libs = set() # Uses a set to automatically handle unique library names.

    # Standard library modules to exclude from requirements
    std_libs = {
        "os", "sys", "re", "json", "csv", "time", "datetime", "math", "random", 
        "collections", "itertools", "functools", "hashlib", "io", "pathlib", 
        "subprocess", "threading", "multiprocessing", "typing", "traceback",
        "contextlib", "tempfile", "shutil", "glob", "argparse", "inspect", "abc",
        "locale", "pickle", "calendar", "uuid", "importlib"
    }
    
    # Internal modules that should be excluded
    internal_modules = {"llm_api"}

    # Iterate through the extracted libraries and add them to the set
    for match in libs: # Iterates through the matches found by the regex.
        if match[0] and match[0] not in std_libs and match[0] not in internal_modules:
            unique_libs.add(match[0]) # Adds the library name from "import library" format.
        if match[1] and match[1] not in std_libs and match[1] not in internal_modules:
            unique_libs.add(match[1]) # Adds the library name from "from library import ..." format.

    # Print the unique libraries
    print("Libraries used:", unique_libs)

    # Get latest library versions and create requirements.txt
    req_file_path = os.path.join(tool_dir, "requirements.txt") # Path to the requirements.txt file.
    
    # Check if pip is available to get versions
    try:
        import subprocess
        import json
        
        # Use pip to list all packages in JSON format
        result = subprocess.run(
            ["pip", "list", "--format=json"],
            capture_output=True,
            text=True,
            check=True
        )
        
        # Parse the JSON output
        installed_packages = json.loads(result.stdout)
        installed_dict = {pkg["name"].lower(): pkg["version"] for pkg in installed_packages}
        
        # Create requirements.txt with versions
        with open(req_file_path, "w") as f:
            for lib in unique_libs:
                lib_lower = lib.lower()
                if lib_lower in installed_dict:
                    f.write(f"{lib}>={installed_dict[lib_lower]}\n")
                else:
                    f.write(f"{lib}\n")
                    
    except (subprocess.SubprocessError, json.JSONDecodeError, KeyError) as e:
        # Fallback if pip command fails
        print(f"Warning: Could not determine package versions: {str(e)}")
        with open(req_file_path, "w") as f:
            for lib in unique_libs:
                f.write(f"{lib}\n")

    print(f"Code generated and cleaned for tool {tool_name} and saved to {code_file_path}")
    print(f"Requirements saved to {req_file_path}")