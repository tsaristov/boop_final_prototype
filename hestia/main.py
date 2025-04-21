import uvicorn
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import the API from our hestia package
from hestia.api import app

if __name__ == "__main__":
    print("Starting Hestia Knowledge and Memory API server...")
    
    # Check if OpenRouter API key is set
    if not os.getenv("OPENROUTER_API_KEY"):
        print("WARNING: OPENROUTER_API_KEY environment variable is not set.")
        print("LLM-based features will not work properly.")
        print("Please set this variable in your .env file or environment.")
    
    # Run the FastAPI server
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8002,
        reload=True
    )