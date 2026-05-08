"""Shared agent state definition for the LangGraph."""

from __future__ import annotations
from typing import Any, TypedDict


class AgentState(TypedDict, total=False):
    """Shared state passed between all graph nodes."""

    # ─── Inputs ──────────────────────────────────────────────────────────────
    request_type: str  # "error_analysis" | "feature_request"
    raw_input: str  # Original user input (error logs or feature description)
    github_repo_url: str
    jira_project_key: str
    excel_mapping_path: str

    # ─── Data Router Decisions ───────────────────────────────────────────────
    sources_needed: list[str]  # e.g. ["repo", "logs", "jira", "excel"]

    # ─── Repo Parser Output ──────────────────────────────────────────────────
    repo_structure: dict[str, Any]  # file tree
    code_snippets: list[dict[str, str]]  # relevant code fragments
    dependency_map: dict[str, list[str]]  # module -> dependencies

    # ─── JIRA Fetcher Output ─────────────────────────────────────────────────
    jira_stories: list[dict[str, Any]]

    # ─── Excel Mapper Output ─────────────────────────────────────────────────
    field_mapping: list[dict[str, Any]]  # parsed Excel rows
    validation_rules: list[dict[str, str]]

    # ─── Context Assembler Output ────────────────────────────────────────────
    unified_context: str  # merged context ready for prompt

    # ─── MD Generator Output ─────────────────────────────────────────────────
    md_output: str  # final structured Markdown
    jira_output: list[dict[str, Any]]  # generated JIRA stories
