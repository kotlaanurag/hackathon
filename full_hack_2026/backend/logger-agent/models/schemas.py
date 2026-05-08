"""Request/Response models for the Logger Agent API."""

from __future__ import annotations
from typing import Any
from pydantic import BaseModel


class AnalyzeRequest(BaseModel):
    """Manual trigger to analyze logs on-demand."""
    lookback_hours: int = 24  # Default: current day
    excel_mapping_path: str | None = None


class ClassifiedError(BaseModel):
    """A single consolidated & classified error."""
    error_type: str  # "missing_or_incorrect_mapping" | "code_error"
    error_description: str
    field_name: str | None = None  # Relevant for mapping errors
    suggested_next_step: str
    severity: str = "medium"  # "high" | "medium" | "low"
    occurrence_count: int = 1  # How many raw errors consolidated into this
    raw_error_sample: str = ""


class AnalyzeResponse(BaseModel):
    """Response from the logger agent analysis."""
    correlation_id: str  # Unique ID to track across all agents
    status: str
    total_raw_errors: int  # Total raw errors fetched from App Insights
    total_distinct_patterns: int  # Consolidated distinct error patterns
    classified_errors: list[ClassifiedError]
    cosmos_document_ids: list[str] = []


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
