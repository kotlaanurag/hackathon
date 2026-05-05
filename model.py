"""Azure OpenAI LLM Integration for all agents."""

import os
import json
import httpx
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv
from langchain_core.language_models.base import BaseLanguageModel
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.callbacks.manager import CallbackManagerForLLMRun
from pydantic import Field

load_dotenv()


class AzureOpenAILLM:
    """
    Azure OpenAI LLM client using the Responses API.
    
    This class provides a simple interface to call Azure OpenAI models
    using the API endpoint and configuration from environment variables.
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        endpoint: Optional[str] = None,
        api_version: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: int = 16384,
        temperature: float = 0.7
    ):
        """
        Initialize the Azure OpenAI LLM.
        
        Args:
            api_key: Azure API key (defaults to AZURE_API_KEY env var)
            endpoint: Azure endpoint (defaults to AZURE_ENDPOINT env var)
            api_version: API version (defaults to AZURE_API_VERSION env var)
            model: Model name (defaults to AZURE_MODEL env var)
            max_tokens: Maximum completion tokens
            temperature: Temperature for generation
        """
        self.api_key = api_key or os.getenv("AZURE_API_KEY", "")
        self.endpoint = endpoint or os.getenv("AZURE_ENDPOINT", "")
        self.api_version = api_version or os.getenv("AZURE_API_VERSION", "2025-04-01-preview")
        self.model = model or os.getenv("AZURE_MODEL", "gpt-5.2-codex")
        self.max_tokens = max_tokens
        self.temperature = temperature
        
        # Validate configuration
        if not self.api_key:
            raise ValueError("AZURE_API_KEY is required")
        if not self.endpoint:
            raise ValueError("AZURE_ENDPOINT is required")
    
    def _build_url(self) -> str:
        """Build the API URL with version parameter."""
        base = self.endpoint.rstrip("/")
        if "?" not in base:
            return f"{base}?api-version={self.api_version}"
        return f"{base}&api-version={self.api_version}"
    
    def _build_headers(self) -> Dict[str, str]:
        """Build the request headers."""
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
    
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None
    ) -> str:
        """
        Generate a completion from the LLM.
        
        Args:
            prompt: The user prompt/message
            system_prompt: Optional system prompt for context
            max_tokens: Override max tokens
            temperature: Override temperature
            
        Returns:
            The generated text response
        """
        messages = []
        
        if system_prompt:
            messages.append({
                "role": "system",
                "content": system_prompt
            })
        
        messages.append({
            "role": "user",
            "content": prompt
        })
        
        return await self.chat(
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature
        )
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None
    ) -> str:
        """
        Send a chat completion request.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            max_tokens: Override max tokens
            temperature: Override temperature
            
        Returns:
            The generated text response
        """
        url = self._build_url()
        headers = self._build_headers()
        
        payload = {
            "messages": messages,
            "max_completion_tokens": max_tokens or self.max_tokens,
            "model": self.model,
            "temperature": temperature if temperature is not None else self.temperature
        }
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            
            if response.status_code != 200:
                raise Exception(f"Azure API error: {response.status_code} - {response.text}")
            
            result = response.json()
            
            # Handle different response formats
            if "choices" in result and len(result["choices"]) > 0:
                choice = result["choices"][0]
                if "message" in choice:
                    return choice["message"].get("content", "")
                elif "text" in choice:
                    return choice["text"]
            elif "output" in result:
                # Handle responses API format
                output = result["output"]
                if isinstance(output, list) and len(output) > 0:
                    for item in output:
                        if item.get("type") == "message":
                            content = item.get("content", [])
                            for c in content:
                                if c.get("type") == "output_text":
                                    return c.get("text", "")
            
            return str(result)
    
    def generate_sync(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None
    ) -> str:
        """
        Synchronous version of generate.
        
        Args:
            prompt: The user prompt/message
            system_prompt: Optional system prompt for context
            max_tokens: Override max tokens
            temperature: Override temperature
            
        Returns:
            The generated text response
        """
        messages = []
        
        if system_prompt:
            messages.append({
                "role": "system",
                "content": system_prompt
            })
        
        messages.append({
            "role": "user",
            "content": prompt
        })
        
        return self.chat_sync(
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature
        )
    
    def chat_sync(
        self,
        messages: List[Dict[str, str]],
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None
    ) -> str:
        """
        Synchronous version of chat.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            max_tokens: Override max tokens
            temperature: Override temperature
            
        Returns:
            The generated text response
        """
        url = self._build_url()
        headers = self._build_headers()
        
        payload = {
            "messages": messages,
            "max_completion_tokens": max_tokens or self.max_tokens,
            "model": self.model,
            "temperature": temperature if temperature is not None else self.temperature
        }
        
        with httpx.Client(timeout=120.0) as client:
            response = client.post(url, headers=headers, json=payload)
            
            if response.status_code != 200:
                raise Exception(f"Azure API error: {response.status_code} - {response.text}")
            
            result = response.json()
            
            # Handle different response formats
            if "choices" in result and len(result["choices"]) > 0:
                choice = result["choices"][0]
                if "message" in choice:
                    return choice["message"].get("content", "")
                elif "text" in choice:
                    return choice["text"]
            elif "output" in result:
                # Handle responses API format
                output = result["output"]
                if isinstance(output, list) and len(output) > 0:
                    for item in output:
                        if item.get("type") == "message":
                            content = item.get("content", [])
                            for c in content:
                                if c.get("type") == "output_text":
                                    return c.get("text", "")
            
            return str(result)


# Global LLM instance (lazy initialization)
_llm_instance: Optional[AzureOpenAILLM] = None


def get_llm() -> AzureOpenAILLM:
    """
    Get the global LLM instance.
    
    Returns:
        AzureOpenAILLM: The global LLM instance
    """
    global _llm_instance
    if _llm_instance is None:
        _llm_instance = AzureOpenAILLM()
    return _llm_instance


def create_llm(
    max_tokens: int = 16384,
    temperature: float = 0.7
) -> AzureOpenAILLM:
    """
    Create a new LLM instance with custom settings.
    
    Args:
        max_tokens: Maximum completion tokens
        temperature: Temperature for generation
        
    Returns:
        AzureOpenAILLM: A new LLM instance
    """
    return AzureOpenAILLM(
        max_tokens=max_tokens,
        temperature=temperature
    )


# Export for easy imports
__all__ = ["AzureOpenAILLM", "get_llm", "create_llm"]
