"""Context assembler node: merge all gathered context into unified model."""

from __future__ import annotations
import json

from graph.state import AgentState


def context_assembler_node(state: AgentState) -> dict:
    """Assemble all gathered data into a unified context string for the generator."""
    sections = []

    # Request info
    sections.append(f"## Request Type\n{state.get('request_type', 'unknown')}")
    sections.append(f"## User Input\n{state.get('raw_input', '')}")

    # Repo context
    if state.get("code_snippets"):
        snippets_text = json.dumps(state["code_snippets"][:20], indent=2)
        sections.append(f"## Repository Code Context\n```\n{snippets_text}\n```")

    if state.get("dependency_map"):
        sections.append(f"## Dependency Map\n```json\n{json.dumps(state['dependency_map'], indent=2)}\n```")

    # Error logs context
    if state.get("error_clusters"):
        sections.append(f"## Error Clusters\n```json\n{json.dumps(state['error_clusters'], indent=2)}\n```")

    if state.get("root_causes"):
        causes = "\n".join(f"- {c}" for c in state["root_causes"])
        sections.append(f"## Root Causes\n{causes}")

    # JIRA context
    if state.get("jira_stories"):
        stories_text = json.dumps(state["jira_stories"][:10], indent=2)
        sections.append(f"## Related JIRA Stories\n```json\n{stories_text}\n```")

    # Excel mapping context
    if state.get("field_mapping"):
        mapping_text = json.dumps(state["field_mapping"][:30], indent=2)
        sections.append(f"## API Field Mapping\n```json\n{mapping_text}\n```")

    if state.get("validation_rules"):
        rules_text = json.dumps(state["validation_rules"], indent=2)
        sections.append(f"## Validation Rules\n```json\n{rules_text}\n```")

    unified = "\n\n".join(sections)
    return {"unified_context": unified}
