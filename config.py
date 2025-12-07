import os
from clients.gemini_client import GeminiClient

def create_llm_client():
    """
    Factory that returns a concrete LLM client.
    Uses environment variables:
    - GEMINI_API_KEY
    - GEMINI_MODEL (optional)
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    model = os.environ.get("GEMINI_MODEL", "gemini-2.5-pro")
    if not api_key:
        raise ValueError("GEMINI_API_KEY (or API_KEY) environment variable is required.")
    return GeminiClient(api_key=api_key, model=model)
