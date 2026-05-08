"""Data router node: LLM-powered decision on which data sources are needed."""

from __future__ import annotations
import json

from langchain_core.messages import HumanMessage, SystemMessage

from graph.state import AgentState
from utils.llm import get_llm


DATA_ROUTER_PROMPT = """You are a planning agent. Given a user request, decide which data sources 
need to be consulted to generate a complete specification prompt.

Available sources:
- "repo": GitHub repository code parsing (use when code context is needed)
- "jira": JIRA stories fetching (use when existing stories provide context)
- "excel": Excel field mapping (use when API payload/field validation is needed)

Return a JSON array of source names needed. Example: ["repo", "logs"]
Return ONLY the JSON array."""


def data_router_node(state: AgentState) -> dict:
    """Use LLM to decide which sources to fetch."""
    llm = get_llm()
    response = llm.invoke([
        SystemMessage(content=DATA_ROUTER_PROMPT),
        HumanMessage(content=(
            f"Request type: {state.get('request_type', '')}\n"
            f"Input: {state.get('raw_input', '')}\n"
            f"GitHub URL provided: {bool(state.get('github_repo_url'))}\n"
            f"Excel path provided: {bool(state.get('excel_mapping_path'))}\n"
            f"JIRA project: {bool(state.get('jira_project_key'))}"
        )),
    ])
    try:
        sources = json.loads(response.content)
    except json.JSONDecodeError:
        # Default: fetch all available sources
        sources = []
        if state.get("github_repo_url"):
            sources.append("repo")
        if state.get("jira_project_key"):
            sources.append("jira")
        if state.get("excel_mapping_path"):
            sources.append("excel")

    return {"sources_needed": sources}


def route_sources(state: AgentState) -> str:
    """Route to the first needed source or go straight to assemble."""
    sources = state.get("sources_needed", [])
    if "repo" in sources:
        return "repo"
    if "jira" in sources:
        return "jira"
    if "excel" in sources:
        return "excel"
    return "assemble"
