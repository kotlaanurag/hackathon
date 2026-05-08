"""Extract DB models/schemas from ORM definitions."""

from __future__ import annotations
import ast
from pathlib import Path
from typing import Any


def extract_schemas(repo_path: Path) -> list[dict[str, Any]]:
    """Extract Pydantic/SQLAlchemy model definitions from Python files."""
    schemas = []

    for py_file in repo_path.rglob("*.py"):
        try:
            source = py_file.read_text(encoding="utf-8")
            tree = ast.parse(source)
        except (SyntaxError, UnicodeDecodeError):
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Check if inherits from BaseModel, Base, DeclarativeBase, etc.
                base_names = [
                    getattr(b, "id", getattr(b, "attr", ""))
                    for b in node.bases
                ]
                orm_bases = {"BaseModel", "Base", "DeclarativeBase", "SQLModel"}
                if any(b in orm_bases for b in base_names):
                    fields = []
                    for item in node.body:
                        if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                            fields.append(item.target.id)
                    schemas.append({
                        "file": str(py_file.relative_to(repo_path)),
                        "class": node.name,
                        "bases": base_names,
                        "fields": fields,
                    })

    return schemas
