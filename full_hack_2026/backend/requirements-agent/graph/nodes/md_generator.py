"""MD generator node: render final structured MD prompt + JIRA stories."""

from __future__ import annotations
import json
from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage

from graph.state import AgentState
from utils.llm import get_llm

# ─── Few-Shot Examples ───────────────────────────────────────────────────────

EXAMPLES_DIR = Path(__file__).resolve().parent.parent.parent / "prompts" / "examples" / "markdown files"


def _load_few_shot_examples(max_examples: int = 2, max_chars_per_example: int = 3000) -> str:
    """Load example markdown files for few-shot learning."""
    if not EXAMPLES_DIR.exists():
        return ""

    examples = []
    for md_file in sorted(EXAMPLES_DIR.glob("*.md"))[:max_examples]:
        content = md_file.read_text(encoding="utf-8", errors="replace")
        if len(content) > max_chars_per_example:
            content = content[:max_chars_per_example] + "\n\n[... truncated for brevity ...]"
        examples.append(f"### Example: {md_file.stem}\n\n{content}")

    if not examples:
        return ""

    return (
        "\n\n---\n\n## FEW-SHOT EXAMPLES\n\n"
        "Below are examples of well-structured specification documents. "
        "Use the same style, depth, and section structure in your output.\n\n"
        + "\n\n---\n\n".join(examples)
    )


MD_SYSTEM_PROMPT = """You are a senior technical lead generating a structured Markdown specification document.

Based on the assembled context, generate a comprehensive Markdown document that includes all relevant sections:
- Problem Statement / Feature Overview
- Root Cause Analysis (for errors) or Motivation (for features)
- Affected Components & Dependencies
- Proposed Solution / Implementation Design
- API Changes (if applicable, reference field mappings)
- Files to Modify/Create
- Testing Requirements
- Acceptance Criteria

Be thorough, precise, and reference specific code paths, field names, and error patterns from the context.
Match the tone, structure, and level of detail shown in the few-shot examples provided.
Output ONLY the Markdown content."""

JIRA_SYSTEM_PROMPT = """You are a project manager creating JIRA stories from a technical specification.

Break the specification into implementable JIRA stories. Output a JSON array where each story has:
- "title": concise story title
- "description": detailed description with context
- "acceptance_criteria": array of testable acceptance criteria
- "story_points": estimated complexity (1, 2, 3, 5, 8, 13)
- "labels": relevant labels array

Output ONLY valid JSON array."""


def md_generator_node(state: AgentState) -> dict:
    """Generate final Markdown specification and JIRA stories."""
    llm = get_llm()
    context = state.get("unified_context", "")

    # Load few-shot examples for style/structure guidance
    few_shot = _load_few_shot_examples()

    # Generate MD
    md_response = llm.invoke([
        SystemMessage(content=MD_SYSTEM_PROMPT + few_shot),
        HumanMessage(content=context),
    ])
    md_output = md_response.content

    # Generate JIRA stories
    jira_response = llm.invoke([
        SystemMessage(content=JIRA_SYSTEM_PROMPT),
        HumanMessage(content=f"Specification:\n{md_output}"),
    ])
    try:
        jira_stories = json.loads(jira_response.content)
    except json.JSONDecodeError:
        jira_stories = [{"title": "Implement specification", "description": jira_response.content, "acceptance_criteria": [], "story_points": 5, "labels": []}]

    if not isinstance(jira_stories, list):
        jira_stories = [jira_stories]

    return {"md_output": md_output, "jira_output": jira_stories}
