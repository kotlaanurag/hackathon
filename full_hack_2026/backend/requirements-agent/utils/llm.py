"""LLM wrapper using Azure OpenAI Responses API."""

from __future__ import annotations
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

import httpx
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage, AIMessage, HumanMessage, SystemMessage
from langchain_core.outputs import ChatResult, ChatGeneration

from config.settings import get_settings
from config.constants import DEFAULT_TEMPERATURE


class AzureResponsesLLM(BaseChatModel):
    """Custom LangChain chat model that uses Azure OpenAI Responses API."""

    endpoint: str = ""
    api_key: str = ""
    api_version: str = ""
    model: str = ""
    temperature: float = DEFAULT_TEMPERATURE

    @property
    def _llm_type(self) -> str:
        return "azure-responses-api"

    def _generate(self, messages: list[BaseMessage], stop: list[str] | None = None, **kwargs: Any) -> ChatResult:
        """Call the Azure OpenAI Responses API."""
        # Convert LangChain messages to a single input string
        # The Responses API takes 'input' as a string or list of content blocks
        input_parts = []
        system_prompt = ""
        for msg in messages:
            if isinstance(msg, SystemMessage):
                system_prompt = msg.content
            elif isinstance(msg, HumanMessage):
                input_parts.append(msg.content)
            else:
                input_parts.append(msg.content)

        user_input = "\n\n".join(input_parts)

        payload: dict[str, Any] = {
            "model": self.model,
            "input": user_input,
        }
        if system_prompt:
            payload["instructions"] = system_prompt

        url = f"{self.endpoint}?api-version={self.api_version}"
        headers = {
            "api-key": self.api_key,
            "Content-Type": "application/json",
        }

        response = httpx.post(url, headers=headers, json=payload, timeout=120)
        response.raise_for_status()
        data = response.json()

        # Extract text from response
        output_text = ""
        for item in data.get("output", []):
            if item.get("type") == "message":
                for content in item.get("content", []):
                    if content.get("type") == "output_text":
                        output_text += content.get("text", "")

        if not output_text:
            # Fallback: try direct text field
            output_text = data.get("output_text", str(data.get("output", "")))

        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=output_text))])


@lru_cache
def get_llm(temperature: float = DEFAULT_TEMPERATURE) -> AzureResponsesLLM:
    """Get a configured Azure OpenAI Responses API LLM instance."""
    settings = get_settings()
    return AzureResponsesLLM(
        endpoint=settings.azure_openai_endpoint,
        api_key=settings.azure_openai_api_key,
        api_version=settings.azure_openai_api_version,
        model=settings.azure_openai_deployment,
        temperature=temperature,
    )
