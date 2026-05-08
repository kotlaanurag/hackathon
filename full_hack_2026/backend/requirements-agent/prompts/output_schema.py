"""Pydantic model defining MD section structure (output schema)."""

from __future__ import annotations
from pydantic import BaseModel, Field


class MDSection(BaseModel):
    """A section in the generated Markdown document."""
    heading: str
    content: str
    subsections: list["MDSection"] = Field(default_factory=list)


class MDDocument(BaseModel):
    """Structure of the final output Markdown document."""
    title: str
    sections: list[MDSection] = Field(default_factory=list)

    def render(self) -> str:
        """Render the document as Markdown text."""
        lines = [f"# {self.title}", ""]
        for section in self.sections:
            lines.extend(_render_section(section, level=2))
        return "\n".join(lines)


def _render_section(section: MDSection, level: int) -> list[str]:
    prefix = "#" * level
    lines = [f"{prefix} {section.heading}", "", section.content, ""]
    for sub in section.subsections:
        lines.extend(_render_section(sub, level + 1))
    return lines
