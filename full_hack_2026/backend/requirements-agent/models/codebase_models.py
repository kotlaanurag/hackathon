"""Models for parsed code structures."""

from __future__ import annotations
from typing import Any

from pydantic import BaseModel, Field


class ParsedClass(BaseModel):
    name: str
    methods: list[str] = Field(default_factory=list)
    line: int = 0
    file: str = ""


class ParsedFunction(BaseModel):
    name: str
    line: int = 0
    file: str = ""


class ModuleInfo(BaseModel):
    file: str
    classes: list[ParsedClass] = Field(default_factory=list)
    functions: list[ParsedFunction] = Field(default_factory=list)
    imports: list[str] = Field(default_factory=list)


class CodebaseStructure(BaseModel):
    """Complete parsed codebase representation."""
    modules: list[ModuleInfo] = Field(default_factory=list)
    dependency_map: dict[str, list[str]] = Field(default_factory=dict)
    schemas: list[dict[str, Any]] = Field(default_factory=list)
