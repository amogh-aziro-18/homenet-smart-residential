"""
LLM Configuration for LangGraph Agents - OpenRouter
"""
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

# Load environment variables
load_dotenv()

def get_llm(model="meta-llama/llama-3.1-70b-instruct", temperature=0):
    """
    Get configured OpenRouter LLM instance
    
    Popular models on OpenRouter:
    - meta-llama/llama-3.1-70b-instruct (powerful)
    - meta-llama/llama-3.1-8b-instruct (fast)
    - anthropic/claude-3.5-sonnet (best reasoning)
    - google/gemini-pro (good balance)
    - mistralai/mixtral-8x7b-instruct (efficient)
    """
    api_key = os.getenv("OPENROUTER_API_KEY")
    
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY not found in .env file")
    
    return ChatOpenAI(
        model=model,
        temperature=temperature,
        openai_api_key=api_key,
        openai_api_base="https://openrouter.ai/api/v1",
        default_headers={
            "HTTP-Referer": "https://homenet-poc.local",
            "X-Title": "HomeNet Predictive Maintenance POC"
        }
    )
