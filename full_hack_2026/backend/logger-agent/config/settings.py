"""Application settings loaded from environment variables."""

from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Azure OpenAI
    azure_openai_endpoint: str = ""
    azure_openai_api_key: str = ""
    azure_openai_deployment: str = "gpt-4o"
    azure_openai_api_version: str = "2024-06-01"

    # Azure App Insights (REST API)
    azure_appinsights_app_id: str = ""
    azure_appinsights_api_key: str = ""

    # Azure Cosmos DB
    cosmos_endpoint: str = ""
    cosmos_key: str = ""
    cosmos_database: str = "hackathon"
    cosmos_container: str = "error_events"

    # Excel field mapping path
    excel_mapping_path: str = "config/FieldMappings.xlsx"

    # Polling interval (seconds)
    poll_interval_seconds: int = 60

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()
