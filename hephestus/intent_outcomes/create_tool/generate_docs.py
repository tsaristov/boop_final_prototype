import os # Module for interacting with the operating system, mainly for file path manipulation.
from llm_api import llm_api_call # Imports the function to call the Language Model API.

def create_tool_definitions(tool_name: str, details: str) -> None:
    """
    Generates documentation files (documentation.md, functions.md, summary.md) for a new tool using LLM.

    This function takes the tool name and a detailed description of the tool, and uses an LLM
    to generate three documentation files: 'documentation.md' (overall tool description),
    'functions.md' (detailed function definitions), and 'summary.md' (a concise summary of both).
    These files are saved in a directory named after the tool under 'installed_tools/'.

    Args:
        tool_name (str): The name of the tool for which to generate documentation.
        details (str): A detailed description of the tool's functionality and purpose.
                       This description is provided to the LLM to generate the documentation.
    """
    # Create the tool directory if it doesn't exist
    tool_dir = os.path.join("tools", tool_name) # Constructs the path to the tool's directory.
    os.makedirs(tool_dir, exist_ok=True) # Creates the directory if it doesn't exist, and does not raise an error if it does.

    # Generate tool documentation using LLM, requesting markdown output directly
    system_instructions = f"""
        You are an expert python software developer tasked with creating documentation and outline for a new tool.

        **Task:**
        Create a markdown file for the tool (It will either be documentation.md, functions.md, or summary.md), following the rules.

        **documentation.md (optimize it for easier understanding for the bot):**
        - Overall purpose of the tool
        - List of use cases
        - Example scenarios

        **functions.md (optimize it for easier understanding for the bot):**
        - List of required functions
        - For each function:
            - Function signature
            - Purpose
            - Detailed logic/steps
            - Parameters
            - Return values
            - Error handling
        - Make the output of this as modular as possilbe, so that it's easy for a bot to read through and gather each individual function in a dictionary.

        **summary.md (optimize it for easier understanding for the bot):**
            - A summary of the documentation.md file and the functions.md file
            - Meant to be provided as context for what the tool is meant to be

        **Important Notes:**
        - All functions should be public (not start with _)
        - Include docstrings
        - Include error handling
        - Use SQLite for database operations when needed
        - Use llm_api_call for LLM interactions when needed

        **Tool Details:**
        Tool Name: {tool_name}
        Tool Details: {details}

        **Output Format:**
        Return the content for file, and only the content for the file, nothing else.

        Example output:
            <Content of required tool>

        Do not include any text before or after the markdown content.
    """

    def extract_content(response):
        """Helper function to extract content from OpenRouter API response.

        This function attempts to extract the main text content from a response object
        received from the OpenRouter API. It handles different response formats,
        including those with 'choices' and 'content' keys. It also includes basic
        error handling to return a default message if content extraction fails.

        Args:
            response: The response object from the llm_api_call function.

        Returns:
            str: The extracted text content from the response, or an error message
                 if content extraction fails.
        """
        try:
            if isinstance(response, dict): # Checks if the response is a dictionary (expected API response format).
                # OpenRouter API response format
                if 'choices' in response and len(response['choices']) > 0: # Checks for 'choices' structure in response.
                    return response['choices'][0]['message']['content'] # Extracts content from 'choices' structure.
                elif 'content' in response: # Checks for direct 'content' in response.
                    return response['content'] # Extracts content directly.
            return str(response) # If response is not a dict, attempts to convert it to string.
        except Exception as e: # Catches any exceptions during content extraction.
            return "Error extracting content from response" # Returns an error message if extraction fails.

    # Get documentation response and extract content
    documentation_response = llm_api_call( # Calls the LLM API to generate documentation.md content.
        model="google/gemini-2.0-flash-lite-001", # Specifies the LLM model to use for documentation.
        messages=[{"role": "user", "content": f"Create the documentation.md for the tool: {tool_name}"}], # User prompt for documentation.md.
        system_instructions=system_instructions # System instructions to guide the LLM for documentation.md.
    )
    print("Saving documentation")
    documentation_content = extract_content(documentation_response) # Extracts content from the LLM response for documentation.md.
    if not documentation_content: # Handles cases where no content is generated.
        documentation_content = "No content generated"

    doc_path = os.path.join(tool_dir, "documentation.md") # Path to save documentation.md.
    with open(doc_path, "w") as f: # Opens the file in write mode and saves the documentation content.
        f.write(documentation_content)

    # Get functions response and extract content
    functions_response = llm_api_call( # Calls the LLM API to generate functions.md content.
        model="google/gemini-2.0-flash-lite-001", # Specifies the LLM model to use for functions.md.
        messages=[{"role": "user", "content": f"Create the functions.md for the tool: {tool_name}"}], # User prompt for functions.md.
        system_instructions=system_instructions # System instructions to guide the LLM for functions.md.
    )

    print("Saving functions")
    functions_content = extract_content(functions_response) # Extracts content from the LLM response for functions.md.
    if not functions_content: # Handles cases where no content is generated.
        functions_content = "No content generated"

    func_path = os.path.join(tool_dir, "functions.md") # Path to save functions.md.
    with open(func_path, "w") as f: # Opens the file in write mode and saves the functions content.
        f.write(functions_content)

    # Get summary response and extract content
    summary_response = llm_api_call( # Calls the LLM API to generate summary.md content.
        model="google/gemini-2.0-flash-lite-001", # Specifies the LLM model to use for summary.md.
        messages=[{"role": "user", "content": f""" # User prompt for summary.md, including context from documentation.md and functions.md.
            Create the summary.md for the tool: {tool_name}

            Here is the documentation content for context:
            {documentation_content}

            Here is the functions content for context:
            {functions_content}

            Please create a concise summary that combines the key points from both documents.
        """}],
        system_instructions=system_instructions # System instructions to guide the LLM for summary.md.
    )

    print("Saving summary")
    summary_content = extract_content(summary_response) # Extracts content from the LLM response for summary.md.
    if not summary_content: # Handles cases where no content is generated.
        summary_content = "No content generated"

    summary_path = os.path.join(tool_dir, "summary.md") # Path to save summary.md.
    with open(summary_path, "w") as f: # Opens the file in write mode and saves the summary content.
        f.write(summary_content)