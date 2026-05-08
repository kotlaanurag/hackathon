"""Intake node: parse initial request, normalize inputs."""

from __future__ import annotations
from graph.state import AgentState


def intake_node(state: AgentState) -> dict:
    """Normalize and validate the initial request inputs."""
    raw = state.get("raw_input", "").strip()
    request_type = state.get("request_type", "")

    # Auto-detect request type if not specified
    if not request_type:
        error_keywords = ["error", "exception", "traceback", "failed", "500", "timeout"]
        if any(kw in raw.lower() for kw in error_keywords):
            request_type = "error_analysis"
        else:
            request_type = "feature_request"

    return {
        "request_type": request_type,
        "raw_input": raw,
    }
