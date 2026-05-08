"""LLM helper — Azure OpenAI via LangChain."""

from __future__ import annotations
from functools import lru_cache

from langchain_openai import AzureChatOpenAI

from config.settings import get_settings
from config.constants import DEFAULT_TEMPERATURE


@lru_cache
def get_llm() -> AzureChatOpenAI:
    settings = get_settings()
    endpoint = settings.azure_openai_endpoint.rstrip("/")
    return AzureChatOpenAI(
        azure_endpoint=endpoint,
        api_key=settings.azure_openai_api_key,
        api_version=settings.azure_openai_api_version,
        azure_deployment=settings.azure_openai_deployment,
        temperature=DEFAULT_TEMPERATURE,
    )
