"""Log analyzer node: fetch & cluster Azure errors, extract root causes."""

from __future__ import annotations
import json

from langchain_core.messages import HumanMessage, SystemMessage

from graph.state import AgentState
from utils.azure_logs import fetch_error_logs
from utils.llm import get_llm


LOG_ANALYSIS_PROMPT = """You are an expert error analyst. Given a set of error logs, perform:
1. Cluster similar errors together
2. Identify the root cause for each cluster
3. Rank clusters by frequency and severity

Return a JSON object with:
- "clusters": array of {"pattern": "...", "count": N, "sample": "...", "severity": "high|medium|low"}
- "root_causes": array of concise root cause strings

Output ONLY valid JSON."""


def log_analyzer_node(state: AgentState) -> dict:
    """Fetch error logs from Azure and cluster/analyze them."""
    raw_input = state.get("raw_input", "")

    # Try fetching from Azure if configured, otherwise use provided logs
    logs = fetch_error_logs() or raw_input

    if not logs:
        return {"error_clusters": [], "root_causes": []}

    llm = get_llm()
    response = llm.invoke([
        SystemMessage(content=LOG_ANALYSIS_PROMPT),
        HumanMessage(content=f"Error Logs:\n{logs[:10000]}"),  # Truncate to avoid token limits
    ])

    try:
        parsed = json.loads(response.content)
    except json.JSONDecodeError:
        parsed = {"clusters": [], "root_causes": [response.content]}

    return {
        "error_clusters": parsed.get("clusters", []),
        "root_causes": parsed.get("root_causes", []),
    }
