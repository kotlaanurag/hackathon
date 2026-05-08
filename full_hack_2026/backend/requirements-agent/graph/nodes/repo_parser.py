"""Repo parser node: clone repo, AST parse, build dependency map."""

from __future__ import annotations
from graph.state import AgentState
from utils.github_client import clone_repo, get_file_tree
from parsers.python_parser import extract_module_info
from parsers.dependency_graph import build_dependency_map


def repo_parser_node(state: AgentState) -> dict:
    """Clone repository and extract code structure."""
    repo_url = state.get("github_repo_url", "")
    if not repo_url:
        return {"repo_structure": {}, "code_snippets": [], "dependency_map": {}}

    # Clone and get file tree
    repo_path = clone_repo(repo_url)
    file_tree = get_file_tree(repo_path)

    # Parse Python files for structure
    code_snippets = []
    for file_path in file_tree:
        if file_path.endswith(".py"):
            info = extract_module_info(repo_path / file_path)
            if info:
                code_snippets.append(info)

    # Build dependency map
    dep_map = build_dependency_map(repo_path)

    return {
        "repo_structure": {"files": file_tree},
        "code_snippets": code_snippets,
        "dependency_map": dep_map,
    }
