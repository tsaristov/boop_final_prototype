"""
Tool Debugging System for Hephestus

This module provides functionality to automatically test and fix tool code.
"""

import importlib.util
import inspect
import os
import re
import sys
import traceback
import logging
from typing import Dict, List, Tuple, Any, Optional, Callable
import time

from llm_api import llm_api_call

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def debug_code(tool_name: str, max_attempts: int = 5) -> bool:
    """
    Debugs tool code by testing all functions and automatically fixing any errors.
    
    This function:
    1. Analyzes the tool code to identify all functions
    2. Generates test cases for each function
    3. Executes tests and identifies errors
    4. Uses LLM to fix any errors encountered
    5. Repeats until all tests pass or max attempts reached
    
    Args:
        tool_name: The name of the tool to debug
        max_attempts: Maximum number of debugging iterations
        
    Returns:
        bool: True if debugging succeeded, False otherwise
    """
    start_time = time.time()
    
    # Use the correct tool directory path
    from tool_library.installer import get_tool_path
    tool_dir = get_tool_path(tool_name)
    code_path = os.path.join(tool_dir, "tool.py")
    
    if not os.path.exists(code_path):
        logger.error(f"Error: tool.py not found for {tool_name}")
        return False
    
    # Get tool documentation for LLM context
    documentation = get_tool_documentation(tool_dir)
    
    # Keep track of our progress
    success = False
    attempts = 0
    
    while attempts < max_attempts:
        attempts += 1
        logger.info(f"Debug iteration {attempts}/{max_attempts}")
        
        # 1. Analyze the tool code
        module, functions_info = analyze_tool_code(code_path)
        
        if not module or not functions_info:
            logger.error("Failed to analyze tool code")
            return False
        
        # 2. Test all functions and collect errors
        test_results = test_all_functions(module, functions_info)
        
        # 3. Check if all tests passed
        if all(result["success"] for result in test_results.values()):
            logger.info(f"All {len(test_results)} functions passed tests")
            success = True
            break
        
        # 4. If errors, fix the code
        failed_functions = [name for name, result in test_results.items() if not result["success"]]
        logger.info(f"Functions with errors: {', '.join(failed_functions)}")
        
        # Get the current code
        with open(code_path, 'r') as f:
            current_code = f.read()
        
        # Fix the code using LLM
        fixed_code = fix_tool_code(
            tool_name=tool_name,
            current_code=current_code,
            test_results=test_results,
            documentation=documentation
        )
        
        if not fixed_code:
            logger.error("Failed to get fixed code from LLM")
            return False
        
        # Write the fixed code back to file
        with open(code_path, 'w') as f:
            f.write(fixed_code)
        
        logger.info("Updated code with fixes")
    
    # Report final results
    execution_time = time.time() - start_time
    
    if success:
        logger.info(f"Debugging completed successfully in {execution_time:.2f} seconds")
        return True
    else:
        logger.error(f"Failed to fix all issues after {max_attempts} attempts")
        return False

def analyze_tool_code(code_path: str) -> Tuple[Optional[Any], Dict[str, Dict[str, Any]]]:
    """
    Analyzes the tool code to identify all functions and their signatures.
    
    Args:
        code_path: Path to the tool.py file
        
    Returns:
        Tuple containing:
        - The imported module object (or None if import failed)
        - Dictionary mapping function names to their information
    """
    try:
        # Import the module
        spec = importlib.util.spec_from_file_location("tool_module", code_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Get all functions from the module
        functions_info = {}
        
        for name, obj in inspect.getmembers(module):
            # Skip internal and non-function objects
            if name.startswith('_') or not inspect.isfunction(obj):
                continue
                
            # Get function signature and docstring
            signature = inspect.signature(obj)
            docstring = obj.__doc__ or ""
            
            # Collect parameter info
            parameters = {}
            for param_name, param in signature.parameters.items():
                parameters[param_name] = {
                    "annotation": param.annotation.__name__ if param.annotation != inspect.Parameter.empty else "any",
                    "default": param.default if param.default != inspect.Parameter.empty else None
                }
            
            # Store function info
            functions_info[name] = {
                "signature": str(signature),
                "docstring": docstring,
                "parameters": parameters,
                "return_annotation": signature.return_annotation.__name__ if signature.return_annotation != inspect.Parameter.empty else "any"
            }
        
        return module, functions_info
        
    except Exception as e:
        logger.error(f"Error analyzing tool code: {str(e)}")
        logger.error(traceback.format_exc())
        return None, {}

def test_all_functions(module: Any, functions_info: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """
    Tests all functions in the module with automatically generated inputs.
    
    Args:
        module: The imported module object
        functions_info: Dictionary of function information
        
    Returns:
        Dictionary mapping function names to test results
    """
    test_results = {}
    
    for func_name, func_info in functions_info.items():
        logger.info(f"Testing function: {func_name}")
        
        # Get the function object
        func = getattr(module, func_name)
        
        # Generate test cases
        test_cases = generate_test_cases(func_name, func_info)
        
        # Test the function with each test case
        function_results = {
            "success": True,
            "test_cases": [],
            "error": None
        }
        
        for test_case in test_cases:
            args = test_case["args"]
            kwargs = test_case["kwargs"]
            expected = test_case.get("expected")
            
            try:
                # Execute the function with the test case
                start_time = time.time()
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                
                test_outcome = {
                    "args": args,
                    "kwargs": kwargs,
                    "success": True,
                    "result": str(result),
                    "execution_time": execution_time
                }
                
                if expected is not None:
                    # If we have an expected result, check if the result matches
                    try:
                        matches = result == expected
                        test_outcome["matches_expected"] = matches
                        if not matches:
                            test_outcome["success"] = False
                            test_outcome["expected"] = str(expected)
                            function_results["success"] = False
                    except Exception:
                        # If comparison fails, just continue
                        test_outcome["matches_expected"] = False
                
            except Exception as e:
                # Function execution failed
                function_results["success"] = False
                test_outcome = {
                    "args": args,
                    "kwargs": kwargs,
                    "success": False,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "traceback": traceback.format_exc()
                }
            
            function_results["test_cases"].append(test_outcome)
            
            # If any test case fails, mark the function as failed
            if not test_outcome["success"]:
                function_results["error"] = test_outcome.get("error_message") or f"Test failed with args: {args}, kwargs: {kwargs}"
        
        test_results[func_name] = function_results
    
    return test_results

def generate_test_cases(func_name: str, func_info: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Generates test cases for a function based on its signature and docstring.
    
    Args:
        func_name: Name of the function
        func_info: Information about the function
        
    Returns:
        List of test case dictionaries, each containing args, kwargs, and optional expected result
    """
    # Generate at least 3 test cases per function, more for complex functions
    parameters = func_info["parameters"]
    num_params = len(parameters)
    
    # Basic test cases based on parameter types
    test_cases = []
    
    # Basic test with default values or simple values
    basic_args = []
    basic_kwargs = {}
    
    for param_name, param_info in parameters.items():
        # Choose appropriate test values based on parameter type
        param_type = param_info["annotation"].lower()
        default = param_info["default"]
        
        if default is not None:
            # Use default value if available
            basic_kwargs[param_name] = default
        else:
            # Generate appropriate value based on type
            if param_type == "str":
                basic_kwargs[param_name] = f"test_{param_name}"
            elif param_type == "int":
                basic_kwargs[param_name] = 1
            elif param_type == "float":
                basic_kwargs[param_name] = 1.0
            elif param_type == "bool":
                basic_kwargs[param_name] = True
            elif param_type == "list":
                basic_kwargs[param_name] = []
            elif param_type == "dict":
                basic_kwargs[param_name] = {}
            else:
                basic_kwargs[param_name] = None
    
    # Add basic test case
    test_cases.append({
        "args": [],
        "kwargs": basic_kwargs
    })
    
    # Add edge cases for common types
    for param_name, param_info in parameters.items():
        param_type = param_info["annotation"].lower()
        
        # Edge cases for strings
        if param_type == "str":
            # Test with empty string
            kwargs_copy = basic_kwargs.copy()
            kwargs_copy[param_name] = ""
            test_cases.append({"args": [], "kwargs": kwargs_copy})
            
            # Test with long string
            kwargs_copy = basic_kwargs.copy()
            kwargs_copy[param_name] = "a" * 100
            test_cases.append({"args": [], "kwargs": kwargs_copy})
        
        # Edge cases for numbers
        elif param_type in ("int", "float"):
            # Test with zero
            kwargs_copy = basic_kwargs.copy()
            kwargs_copy[param_name] = 0
            test_cases.append({"args": [], "kwargs": kwargs_copy})
            
            # Test with negative value
            kwargs_copy = basic_kwargs.copy()
            kwargs_copy[param_name] = -1
            test_cases.append({"args": [], "kwargs": kwargs_copy})
            
            # Test with large value
            kwargs_copy = basic_kwargs.copy()
            kwargs_copy[param_name] = 1000000
            test_cases.append({"args": [], "kwargs": kwargs_copy})
        
        # Edge cases for collections
        elif param_type in ("list", "dict"):
            # Test with empty collection
            kwargs_copy = basic_kwargs.copy()
            kwargs_copy[param_name] = [] if param_type == "list" else {}
            test_cases.append({"args": [], "kwargs": kwargs_copy})
            
            # Test with non-empty collection
            kwargs_copy = basic_kwargs.copy()
            kwargs_copy[param_name] = [1, 2, 3] if param_type == "list" else {"a": 1, "b": 2}
            test_cases.append({"args": [], "kwargs": kwargs_copy})
    
    # Generate realistic test cases based on function name and docstring
    if func_name.startswith(("add", "sum", "calculate")):
        test_cases.append({"args": [], "kwargs": {"a": 5, "b": 3}, "expected": 8})
        test_cases.append({"args": [], "kwargs": {"a": -1, "b": 1}, "expected": 0})
    
    elif func_name.startswith(("subtract", "minus")):
        test_cases.append({"args": [], "kwargs": {"a": 5, "b": 3}, "expected": 2})
        test_cases.append({"args": [], "kwargs": {"a": 3, "b": 5}, "expected": -2})
    
    elif func_name.startswith(("multiply", "times")):
        test_cases.append({"args": [], "kwargs": {"a": 5, "b": 3}, "expected": 15})
        test_cases.append({"args": [], "kwargs": {"a": -2, "b": 3}, "expected": -6})
    
    elif func_name.startswith(("divide", "div")):
        test_cases.append({"args": [], "kwargs": {"a": 6, "b": 3}, "expected": 2})
        test_cases.append({"args": [], "kwargs": {"a": 5, "b": 2}, "expected": 2.5})
        # Test division by zero error
        test_cases.append({"args": [], "kwargs": {"a": 1, "b": 0}})
    
    return test_cases

def fix_tool_code(tool_name: str, current_code: str, test_results: Dict[str, Dict[str, Any]], documentation: Dict[str, str]) -> Optional[str]:
    """
    Uses LLM to fix errors in the tool code.
    
    Args:
        tool_name: Name of the tool
        current_code: Current tool code
        test_results: Results of function tests
        documentation: Tool documentation
        
    Returns:
        Fixed code or None if fixing failed
    """
    # Prepare error summary for LLM
    error_summary = []
    for func_name, result in test_results.items():
        if not result["success"]:
            error_summary.append(f"Function '{func_name}' failed:")
            
            # Include details about failed test cases
            for i, test_case in enumerate(result["test_cases"]):
                if not test_case["success"]:
                    args_str = ", ".join([str(arg) for arg in test_case["args"]])
                    kwargs_str = ", ".join([f"{k}={v}" for k, v in test_case["kwargs"].items()])
                    call_str = f"{func_name}({args_str}{', ' if args_str and kwargs_str else ''}{kwargs_str})"
                    
                    if "error_type" in test_case:
                        error_summary.append(f"  Test case {i+1}: {call_str} raised {test_case['error_type']}: {test_case['error_message']}")
                        error_summary.append(f"  Traceback:\n{test_case['traceback']}")
                    elif "matches_expected" in test_case and not test_case["matches_expected"]:
                        error_summary.append(f"  Test case {i+1}: {call_str} returned {test_case['result']}, expected {test_case['expected']}")
    
    error_summary_text = "\n".join(error_summary)
    
    # Prompt the LLM to fix the code
    system_instructions = f"""
    You are an expert Python debugger specialized in fixing tool code for the Hephestus system.
    
    TASK: Fix the errors in the {tool_name} tool code based on the test results.
    
    INSTRUCTIONS:
    1. Analyze the error information carefully
    2. Identify the root causes of the issues
    3. Fix ALL functions that failed tests
    4. Ensure your fixes maintain the original functionality described in the documentation
    5. Ensure the code handles edge cases properly
    6. Do not change the function signatures or parameter names
    7. Add proper error handling where needed
    
    TOOL DESCRIPTION:
    {documentation.get('summary', 'No summary available')}
    
    FUNCTION SPECIFICATIONS:
    {documentation.get('functions', 'No function specifications available')}
    
    OUTPUT FORMAT:
    Return ONLY the complete fixed Python code without ANY explanation or markdown formatting.
    """
    
    messages = [{
        "role": "user",
        "content": f"""
        Here is the current code with errors:
        
        ```python
        {current_code}
        ```
        
        Here are the test results that show the errors:
        
        {error_summary_text}
        
        Please fix all the errors in the code and return the complete fixed version.
        """
    }]
    
    try:
        response = llm_api_call(
            model="google/gemini-2.0-flash-001",
            messages=messages,
            system_instructions=system_instructions
        )
        
        # Extract code from response
        if isinstance(response, dict):
            choices = response.get('choices', [])
            if choices:
                content = choices[0].get('message', {}).get('content', '')
            else:
                content = response.get('content', '')
        else:
            content = str(response)
        
        # Extract code between python markers if present
        code_match = re.search(r'```(?:python)?\s*(.*?)\s*```', content, re.DOTALL)
        fixed_code = code_match.group(1).strip() if code_match else content.strip()
        
        # Basic validation of the fixed code
        if "def " not in fixed_code:
            logger.error("Invalid fixed code: no function definitions found")
            return None
        
        return fixed_code
    
    except Exception as e:
        logger.error(f"Error getting fixed code: {str(e)}")
        return None

def get_tool_documentation(tool_dir: str) -> Dict[str, str]:
    """
    Gets documentation files for the tool.
    
    Args:
        tool_dir: Path to the tool directory
        
    Returns:
        Dictionary with documentation contents
    """
    docs = {}
    
    for doc_type in ['documentation', 'functions', 'summary']:
        path = os.path.join(tool_dir, f"{doc_type}.md")
        if os.path.exists(path):
            with open(path) as f:
                docs[doc_type] = f.read()
                
    return docs