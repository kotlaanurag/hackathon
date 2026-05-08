"""Excel mapper node: parse field mapping & validation rules."""

from __future__ import annotations
from graph.state import AgentState
from utils.excel_parser import parse_field_mapping


def excel_mapper_node(state: AgentState) -> dict:
    """Load and parse Excel field mapping file."""
    path = state.get("excel_mapping_path", "")
    if not path:
        return {"field_mapping": [], "validation_rules": []}

    mapping, rules = parse_field_mapping(path)
    return {
        "field_mapping": mapping,
        "validation_rules": rules,
    }
