"""AST-based Python parser: extract classes, functions, imports."""

from __future__ import annotations
import ast
from pathlib import Path
from typing import Any


def extract_module_info(file_path: Path) -> dict[str, Any] | None:
    """Parse a Python file and extract structural information."""
    if not file_path.exists():
        return None

    try:
        source = file_path.read_text(encoding="utf-8")
        tree = ast.parse(source)
    except (SyntaxError, UnicodeDecodeError):
        return None

    classes = []
    functions = []
    imports = []

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            methods = [m.name for m in node.body if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef))]
            classes.append({"name": node.name, "methods": methods, "line": node.lineno})
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            # Only top-level functions (not methods)
            if isinstance(node, ast.FunctionDef) and not any(
                isinstance(parent, ast.ClassDef) for parent in ast.walk(tree)
            ):
                functions.append({"name": node.name, "line": node.lineno})
        elif isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            imports.append(module)

    return {
        "file": str(file_path),
        "classes": classes,
        "functions": functions,
        "imports": imports,
    }
