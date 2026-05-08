"""Build call graph & module dependency tree."""

from __future__ import annotations
import ast
from pathlib import Path


def build_dependency_map(repo_path: Path) -> dict[str, list[str]]:
    """Build a module-level dependency map from Python imports."""
    dep_map: dict[str, list[str]] = {}

    for py_file in repo_path.rglob("*.py"):
        relative = str(py_file.relative_to(repo_path))
        try:
            source = py_file.read_text(encoding="utf-8")
            tree = ast.parse(source)
        except (SyntaxError, UnicodeDecodeError):
            continue

        deps = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    deps.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    deps.append(node.module)

        if deps:
            dep_map[relative] = sorted(set(deps))

    return dep_map
