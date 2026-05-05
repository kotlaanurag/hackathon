"""Analyst Agent - Reads repo structure and drafts implementation plan using LLM."""

import os
import re
import json
from typing import Dict, Any, List
from agents.base import BaseAgent, AgentState
from prompts import get_prompt
from model import get_llm


class AnalystAgent(BaseAgent):
    """
    The Analyst Agent using LLM-powered analysis:
    1. Uses repository context from RepoReader
    2. Understands the codebase structure and contents
    3. Uses LLM to create detailed implementation plans
    4. Identifies relevant files based on user's request
    """

    def __init__(self):
        super().__init__(
            name="Analyst",
            description="Analyzes repository and creates LLM-powered implementation plans"
        )
        self.prompt = get_prompt("analyst", default="")
        self.llm = get_llm()
        self.ignored_dirs = {
            '.git', 'node_modules', '__pycache__', 'venv', 'env',
            '.venv', 'dist', 'build'
        }
        self.code_extensions = {
            '.py', '.js', '.ts', '.jsx', '.tsx',
            '.java', '.go', '.rs', '.cpp', '.c', '.h'
        }

    async def execute(self, state: AgentState) -> AgentState:
        """Analyze the repo and create an LLM-powered implementation plan."""
        import time
        start_time = time.time()

        self.log_input(state)
        self.log("Analyzing repository with LLM...", {"repo_path": state.repo_path})

        try:
            # Use state fields directly — RepoReader writes here, no message-scanning needed
            repo_context = state.repo_context
            file_contents = state.file_contents

            if file_contents:
                repo_structure = {
                    "files": list(file_contents.keys()),
                    "file_count": len(file_contents)
                }
                self.log("Using file list from RepoReader", {"file_count": len(file_contents)})
            else:
                repo_structure = self._read_repo_structure(state.repo_path)
                self.log("Repository structure read from disk", {
                    "file_count": repo_structure.get("file_count", 0)
                })

            safe_issue = self._sanitize_input(state.issue)

            # Let the LLM decide which files to create/modify — no regex pre-filtering
            implementation_plan = await self._create_implementation_plan_with_llm(
                safe_issue,
                repo_structure,
                repo_context,
                file_contents
            )

            state.implementation_plan = implementation_plan

            # Extract paths from LLM-chosen file lists (entries may be dicts or plain strings)
            def _paths(entries: list) -> list:
                return [f["path"] if isinstance(f, dict) else f for f in entries]

            files_to_create = _paths(implementation_plan.get("files_to_create", []))
            files_to_modify = _paths(implementation_plan.get("files_to_modify", []))
            # Preserve order, deduplicate
            seen: set = set()
            combined = []
            for p in files_to_create + files_to_modify:
                if p not in seen:
                    seen.add(p)
                    combined.append(p)
            state.files_to_modify = combined

            state.current_agent = self.name
            state.messages.append({
                "agent": self.name,
                "action": "created_implementation_plan",
                "data": {
                    "plan": implementation_plan,
                    "repo_context": repo_context
                }
            })

            self.log(f"LLM selected {len(state.files_to_modify)} files", {
                "files": state.files_to_modify
            })

            duration_ms = (time.time() - start_time) * 1000
            self.log_output(state, duration_ms)
            return state

        except Exception as e:
            self.log_error(e, {"repo_path": state.repo_path})
            state.errors.append(str(e))
            return state

    async def _create_implementation_plan_with_llm(
        self,
        issue: str,
        repo_structure: Dict,
        repo_context: Dict,
        file_contents: Dict
    ) -> Dict[str, Any]:
        """Use LLM to create a comprehensive implementation plan."""
        prompt = self._build_planning_prompt(
            issue=issue,
            repo_structure=repo_structure,
            repo_context=repo_context,
            file_contents=file_contents
        )

        try:
            response = await self.llm.generate(
                prompt=prompt,
                system_prompt=self.prompt,
                temperature=0.4
            )
            plan = self._parse_plan_response(response)
            self.log("LLM generated implementation plan", {
                "summary": plan.get("summary", "")[:100]
            })
            return plan

        except Exception as e:
            self.log(f"LLM planning failed, using fallback: {e}", {"error": str(e)})
            state_errors = [f"LLM planning failed: {e}"]
            return self._create_fallback_plan(issue, repo_context, state_errors)

    def _build_planning_prompt(
        self,
        issue: str,
        repo_structure: Dict,
        repo_context: Dict,
        file_contents: Dict
    ) -> str:
        """Build a comprehensive SDLC-aware prompt for implementation planning."""

        orchestrator_data = repo_context.get("_orchestrator_metadata", {})
        acceptance_criteria = orchestrator_data.get("acceptance_criteria", [])
        risk_level = orchestrator_data.get("risk_level", "medium")
        requires_security = orchestrator_data.get("requires_security_review", False)
        tech_considerations = orchestrator_data.get("technical_considerations", [])
        breaking_changes = orchestrator_data.get("breaking_changes", False)

        all_files = repo_structure.get("files", [])
        code_files = [f for f in all_files if os.path.splitext(f)[1] in self.code_extensions]

        prompt_parts = [
            "You are Sam, Senior Solutions Architect operating in the Design & Planning phase of the SDLC.",
            "",
            "Create a precise, executable implementation plan. Your plan is the contract between requirements and code —",
            "it must be detailed enough that a developer can implement without asking questions.",
            "",
            "## User Request:",
            issue,
            "",
            "## Repository Context:",
            f"- Main Language: {repo_context.get('main_language', 'Unknown')}",
            f"- Project Type: {repo_context.get('project_type', 'Unknown')}",
            f"- Frameworks: {', '.join(repo_context.get('frameworks', [])) or 'Unknown'}",
            f"- Total Files: {len(all_files)} ({len(code_files)} code files)",
            f"- Risk Level: {risk_level}",
            f"- Requires Security Review: {requires_security}",
            f"- Breaking Changes: {breaking_changes}",
            "",
        ]

        if acceptance_criteria:
            prompt_parts.append("## Acceptance Criteria (from Requirements Analysis):")
            for criterion in acceptance_criteria:
                prompt_parts.append(f"- {criterion}")
            prompt_parts.append("")

        if tech_considerations:
            prompt_parts.append("## Technical Considerations:")
            for tc in tech_considerations:
                prompt_parts.append(f"- {tc}")
            prompt_parts.append("")

        if code_files:
            prompt_parts.append("## All Code Files in Repository (YOU decide which to create/modify):")
            for f in code_files[:50]:
                prompt_parts.append(f"- {f}")
            if len(code_files) > 50:
                prompt_parts.append(f"... and {len(code_files) - 50} more")
            prompt_parts.append("")

        if file_contents:
            # Show a sample of actual file contents so the LLM can match style/patterns
            shown = 0
            prompt_parts.append("## Sample File Contents (match these patterns):")
            for file_path, content in file_contents.items():
                if shown >= 4:
                    break
                ext = os.path.splitext(file_path)[1]
                if ext not in self.code_extensions or not content or content.startswith("["):
                    continue
                prompt_parts.append(f"\n### {file_path}:")
                prompt_parts.append("```")
                prompt_parts.append(content[:1200])
                if len(content) > 1200:
                    prompt_parts.append("... (truncated)")
                prompt_parts.append("```")
                shown += 1
            prompt_parts.append("")

        prompt_parts.extend([
            "## Design Principles to Apply:",
            "- SOLID: Single Responsibility — each function/class does one thing",
            "- DRY: Reuse existing components; do not duplicate logic",
            "- YAGNI: Plan only what is required, no speculative abstractions",
            "- Fail Fast: validate inputs at entry points, return clear errors early",
            "- Security by Design: auth checks, input validation, secrets via env vars",
            "",
            "## Required Output (JSON format):",
            "```json",
            "{",
            '  "summary": "2-3 sentence description of what is built and WHY",',
            '  "design_approach": "Architectural pattern used and reason it fits (e.g. service layer, repository pattern)",',
            '  "action_type": "feature|bugfix|refactor|enhancement|security|performance",',
            '  "steps": [',
            '    {',
            '      "step": 1,',
            '      "action": "Imperative description (e.g. Add JWT validation middleware)",',
            '      "description": "Why this step is needed and what it achieves",',
            '      "files": ["path/to/file.py"]',
            '    }',
            '  ],',
            '  "files_to_create": [',
            '    {"path": "new_file.py", "purpose": "What this file does", "exports": ["ClassName", "function_name"]}',
            '  ],',
            '  "files_to_modify": [',
            '    {"path": "existing.py", "current_state": "Brief what it does now", "changes": "What changes and why"}',
            '  ],',
            '  "api_contracts": [',
            '    {"endpoint": "/api/v1/resource", "method": "POST", "request_schema": {}, "response_schema": {}, "auth_required": true}',
            '  ],',
            '  "data_structures": [',
            '    {"name": "ModelName", "fields": {"field": "type"}, "purpose": "what it represents"}',
            '  ],',
            '  "error_handling_strategy": "What errors to catch, log, surface — specific exception types",',
            '  "security_considerations": ["auth check needed at X", "validate Y input", "sanitise Z"],',
            '  "dependencies": [{"package": "name", "reason": "why needed"}],',
            '  "estimated_complexity": "low|medium|high",',
            '  "risks": ["Risk 1 and mitigation", "Risk 2 and mitigation"],',
            '  "testing_requirements": {',
            '    "unit_tests": ["test X behaviour", "test Y edge case"],',
            '    "integration_tests": ["test A with B"],',
            '    "security_tests": ["test auth bypass", "test injection"]',
            '  },',
            '  "breaking_changes": false,',
            '  "breaking_change_details": null',
            "}",
            "```",
            "",
            "Provide ONLY the JSON object, no additional text."
        ])

        return "\n".join(prompt_parts)

    def _parse_plan_response(self, response: str) -> Dict[str, Any]:
        """Parse the LLM response into a structured plan."""
        response = response.strip()

        if response.startswith("```"):
            lines = response.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            response = "\n".join(lines)

        try:
            return json.loads(response)
        except json.JSONDecodeError:
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                try:
                    return json.loads(json_match.group())
                except json.JSONDecodeError:
                    pass

            return {
                "summary": response[:200],
                "action_type": "enhancement",
                "steps": [{"step": 1, "action": "Implement the requested changes"}],
                "files_to_create": [],
                "files_to_modify": [],
                "dependencies": [],
                "estimated_complexity": "medium",
                "risks": [],
                "testing_requirements": "Add appropriate tests"
            }

    def _create_fallback_plan(
        self,
        issue: str,
        repo_context: Dict,
        errors: List[str]
    ) -> Dict[str, Any]:
        """Create a minimal fallback plan when LLM fails — signals to the user that manual review is needed."""
        return {
            "summary": f"[FALLBACK — LLM planning failed] {issue[:150]}",
            "action_type": self._detect_issue_type(issue),
            "steps": [
                {"step": 1, "action": "Review the issue and identify files to change"},
                {"step": 2, "action": "Implement requested changes"},
                {"step": 3, "action": "Add error handling and tests"},
            ],
            "files_to_create": [],
            "files_to_modify": [],
            "dependencies": [],
            "estimated_complexity": "medium",
            "risks": ["LLM planning failed — plan was auto-generated and requires manual review"],
            "fallback_errors": errors,
            "testing_requirements": "Add appropriate unit tests"
        }

    def _detect_issue_type(self, issue: str) -> str:
        """Detect the type of issue."""
        issue_lower = issue.lower()
        if any(word in issue_lower for word in ["bug", "fix", "error", "broken"]):
            return "bugfix"
        elif any(word in issue_lower for word in ["add", "create", "implement", "new"]):
            return "feature"
        elif any(word in issue_lower for word in ["refactor", "improve", "optimize"]):
            return "refactor"
        return "enhancement"

    def _read_repo_structure(self, repo_path: str) -> Dict[str, Any]:
        """Read repository structure from disk (fallback when RepoReader hasn't run)."""
        structure = {
            "root": repo_path,
            "directories": [],
            "files": [],
            "file_count": 0,
            "dir_count": 0
        }

        if not repo_path or not os.path.exists(repo_path):
            return structure

        for root, dirs, files in os.walk(repo_path):
            dirs[:] = [d for d in dirs if d not in self.ignored_dirs]
            rel_root = os.path.relpath(root, repo_path)
            if rel_root != ".":
                structure["directories"].append(rel_root)
                structure["dir_count"] += 1
            for file in files:
                rel_path = os.path.join(rel_root, file) if rel_root != "." else file
                structure["files"].append(rel_path)
                structure["file_count"] += 1

        return structure


