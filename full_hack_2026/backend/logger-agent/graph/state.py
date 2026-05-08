"""Shared state for the Logger Agent LangGraph."""

from __future__ import annotations
from typing import Any, TypedDict


class LoggerAgentState(TypedDict, total=False):
    """State passed between logger agent graph nodes."""

    # ─── Tracking ────────────────────────────────────────────────────────────
    correlation_id: str  # Unique ID to track this process across all agents

    # ─── Inputs ──────────────────────────────────────────────────────────────
    lookback_hours: int  # Default 24 (current day)
    excel_mapping_path: str

    # ─── Log Fetcher Output ──────────────────────────────────────────────────
    raw_logs: str  # Raw error logs from App Insights
    log_entries: list[dict[str, Any]]  # Parsed individual log entries
    total_raw_errors: int  # Total number of raw errors fetched

    # ─── Excel Loader Output ─────────────────────────────────────────────────
    field_mappings: list[dict[str, Any]]  # PCS <-> IRIS field mappings from Excel

    # ─── Error Classifier Output ─────────────────────────────────────────────
    classified_errors: list[dict[str, Any]]  # Consolidated & classified errors

    # ─── Cosmos Writer Output ────────────────────────────────────────────────
    cosmos_document_ids: list[str]  # IDs of written Cosmos DB documents (one per error)
    stage: str  # Current stage for tracking
    status: str  # Current status for tracking
