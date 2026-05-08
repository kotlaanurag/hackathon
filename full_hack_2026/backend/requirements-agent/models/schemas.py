"""Request/response Pydantic models for the API."""

from __future__ import annotations
from typing import Any

from pydantic import BaseModel, Field


class GeneratePromptRequest(BaseModel):
    """Request to generate a structured MD prompt."""
    request_type: str = Field(
        default="",
        description="Type of request: 'error_analysis' or 'feature_request'. Auto-detected if empty.",
    )
    raw_input: str = Field(..., description="Error logs or feature request description")
    github_repo_url: str = Field(default="", description="GitHub repository URL")
    jira_project_key: str = Field(default="", description="JIRA project key for fetching related stories")
    excel_mapping_path: str = Field(default="", description="Path to Excel field mapping file")


class GeneratePromptResponse(BaseModel):
    """Response containing generated MD and JIRA stories."""
    md_output: str = Field(default="", description="Generated Markdown specification")
    jira_output: list[dict[str, Any]] = Field(default_factory=list, description="Generated JIRA stories")
    sources_used: list[str] = Field(default_factory=list, description="Data sources that were consulted")


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
