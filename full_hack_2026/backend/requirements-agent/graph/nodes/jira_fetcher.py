"""JIRA fetcher node: pull stories and acceptance criteria."""

from __future__ import annotations
from graph.state import AgentState
from utils.jira_client import fetch_stories


def jira_fetcher_node(state: AgentState) -> dict:
    """Fetch related JIRA stories for context."""
    project_key = state.get("jira_project_key", "")
    if not project_key:
        return {"jira_stories": state.get("jira_stories", [])}

    stories = fetch_stories(project_key)
    return {"jira_stories": stories}
