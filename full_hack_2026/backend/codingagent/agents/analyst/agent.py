"""Analyst Agent - Reads repo structure and drafts implementation plan using LLM."""

import os
import re
import json
from typing import Dict, Any, List, Optional
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
            repo_context = self._get_repo_context_from_messages(state)
            file_contents = self._get_file_contents_from_messages(state)

            if repo_context:
                self.log("Using repo context from RepoReader", {
                    "main_language": repo_context.get("main_language"),
                    "project_type": repo_context.get("project_type"),
                    "total_files": repo_context.get("total_files")
                })

            if file_contents:
                repo_structure = {
                    "files": list(file_contents.keys()),
                    "file_count": len(file_contents)
                }
                self.log("Using file contents from RepoReader", {"file_count": len(file_contents)})
            else:
                repo_structure = self._read_repo_structure(state.repo_path)
                self.log("Repository structure read from disk", {
                    "file_count": repo_structure.get("file_count", 0)
                })

            relevant_files = self._identify_relevant_files_with_context(
                repo_structure,
                state.issue,
                file_contents
            )
            self.log("Relevant files identified", {
                "count": len(relevant_files),
                "files": relevant_files[:5]
            })

            implementation_plan = await self._create_implementation_plan_with_llm(
                state.issue,
                repo_structure,
                relevant_files,
                repo_context,
                file_contents
            )

            state.implementation_plan = implementation_plan

            # Extract file paths from files_to_create (may be dicts with 'path' key or strings)
            files_to_create_raw = implementation_plan.get("files_to_create", [])
            files_to_create = []
            for f in files_to_create_raw:
                if isinstance(f, dict):
                    files_to_create.append(f.get("path", ""))
                else:
                    files_to_create.append(f)
            files_to_create = [f for f in files_to_create if f]  # Remove empty strings

            # Extract file paths from files_to_modify (may be dicts with 'path' key or strings)
            files_to_modify_raw = implementation_plan.get("files_to_modify", relevant_files)
            files_to_modify = []
            for f in files_to_modify_raw:
                if isinstance(f, dict):
                    files_to_modify.append(f.get("path", ""))
                else:
                    files_to_modify.append(f)
            files_to_modify = [f for f in files_to_modify if f]  # Remove empty strings

            all_files = list(set(files_to_create + files_to_modify))
            state.files_to_modify = all_files if all_files else relevant_files

            state.current_agent = self.name
            state.messages.append({
                "agent": self.name,
                "action": "created_implementation_plan",
                "data": {
                    "repo_structure": repo_structure,
                    "relevant_files": relevant_files,
                    "suggested_new_files": files_to_create,
                    "plan": implementation_plan,
                    "repo_context": repo_context
                }
            })

            self.log(f"Implementation plan created with {len(state.files_to_modify)} files", {
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
        relevant_files: List[str],
        repo_context: Dict,
        file_contents: Dict
    ) -> Dict[str, Any]:
        """Use LLM to create a comprehensive implementation plan."""
        prompt = self._build_planning_prompt(
            issue=issue,
            repo_structure=repo_structure,
            relevant_files=relevant_files,
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
            self.log(f"LLM planning failed, using fallback: {e}")
            return self._create_fallback_plan(issue, relevant_files, repo_context)

    def _build_planning_prompt(
        self,
        issue: str,
        repo_structure: Dict,
        relevant_files: List[str],
        repo_context: Dict,
        file_contents: Dict
    ) -> str:
        """Build a comprehensive SDLC-aware prompt for implementation planning."""

        # Extract orchestrator metadata if available (passed through repo_context)
        orchestrator_data = repo_context.get("_orchestrator_metadata", {})
        acceptance_criteria = orchestrator_data.get("acceptance_criteria", [])
        risk_level = orchestrator_data.get("risk_level", "medium")
        requires_security = orchestrator_data.get("requires_security_review", False)
        tech_considerations = orchestrator_data.get("technical_considerations", [])
        breaking_changes = orchestrator_data.get("breaking_changes", False)

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
            f"- Total Files: {len(repo_structure.get('files', []))}",
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

        if relevant_files:
            prompt_parts.append("## Relevant Files (identified by RepoReader):")
            for f in relevant_files[:10]:
                prompt_parts.append(f"- {f}")
            prompt_parts.append("")

        if file_contents:
            prompt_parts.append("## Existing Code (for context — match these patterns):")
            for file_path in relevant_files[:5]:
                content = file_contents.get(file_path, "")
                if content and not content.startswith("["):
                    prompt_parts.append(f"\n### {file_path}:")
                    prompt_parts.append("```")
                    prompt_parts.append(content[:1500])
                    if len(content) > 1500:
                        prompt_parts.append("... (truncated)")
                    prompt_parts.append("```")
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
        relevant_files: List[str],
        repo_context: Dict
    ) -> Dict[str, Any]:
        """Create a basic fallback plan when LLM fails."""
        return {
            "summary": f"Implementation plan for: {issue[:100]}",
            "action_type": self._detect_issue_type(issue),
            "steps": [
                {"step": 1, "action": "Analyze existing code", "files": relevant_files[:5]},
                {"step": 2, "action": "Implement requested changes"},
                {"step": 3, "action": "Add error handling"},
                {"step": 4, "action": "Write tests"},
                {"step": 5, "action": "Add documentation"}
            ],
            "files_to_create": self._suggest_new_files(issue),
            "files_to_modify": relevant_files,
            "dependencies": [],
            "estimated_complexity": "medium",
            "risks": [],
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

    def _suggest_new_files(self, issue: str) -> List[str]:
        """Suggest new files that might need to be created."""
        suggestions = []
        issue_lower = issue.lower()

        if "login" in issue_lower or "auth" in issue_lower:
            suggestions.extend(["auth.py", "auth_utils.py"])
        if "api" in issue_lower or "endpoint" in issue_lower:
            suggestions.extend(["routes.py", "handlers.py"])
        if "test" in issue_lower:
            suggestions.append("tests/test_feature.py")
        if "model" in issue_lower or "database" in issue_lower:
            suggestions.append("models.py")
        if "config" in issue_lower:
            suggestions.append("config.py")

        return suggestions

    def _get_repo_context_from_messages(self, state: AgentState) -> Dict[str, Any]:
        """Get repo context from RepoReader messages."""
        for msg in state.messages:
            if msg.get("agent") == "RepoReader" and msg.get("action") == "repo_loaded":
                return msg.get("data", {}).get("context_summary", {})
        return {}

    def _get_file_contents_from_messages(self, state: AgentState) -> Dict[str, str]:
        """Get file contents from RepoReader messages."""
        for msg in state.messages:
            if msg.get("agent") == "RepoReader" and msg.get("action") == "repo_loaded":
                return msg.get("data", {}).get("file_contents", {})
        return {}

    def _identify_relevant_files_with_context(
        self,
        repo_structure: Dict,
        issue: str,
        file_contents: Dict
    ) -> List[str]:
        """Identify files relevant to the issue using both structure and content."""
        relevant = []
        issue_lower = issue.lower()
        keywords = self._extract_keywords(issue_lower)

        # Prioritise any file explicitly named in the issue
        target_file = self._extract_target_file(issue)
        if target_file:
            for file_path in repo_structure.get("files", []):
                if file_path.lower().endswith(target_file.lower()):
                    relevant.append(file_path)
                    self.log(f"Target file identified from issue: {file_path}")
                    break
            if not relevant:
                relevant.append(target_file)
                self.log(f"Target file not in repo, will create: {target_file}")

        # Match file names against keywords
        for file_path in repo_structure.get("files", []):
            if file_path in relevant:
                continue
            ext = os.path.splitext(file_path)[1]
            if ext in self.code_extensions:
                if any(kw in file_path.lower() for kw in keywords):
                    relevant.append(file_path)

        # Search file contents for keyword matches
        if file_contents:
            for file_path, content in file_contents.items():
                if file_path in relevant or not content or content.startswith("["):
                    continue
                content_lower = content.lower()
                for keyword in keywords:
                    if keyword in content_lower:
                        relevant.append(file_path)
                        break

        # Fall back to main entry points if nothing found
        if not relevant:
            for file_path in repo_structure.get("files", []):
                if any(entry in file_path.lower() for entry in ['main', 'app', 'index', '__init__']):
                    relevant.append(file_path)

        return relevant[:15]

    def _extract_target_file(self, issue: str) -> Optional[str]:
        """Extract a specific file name explicitly mentioned in the issue."""
        patterns = [
            r'in\s+(\w+\.py)',
            r'to\s+(\w+\.py)',
            r'file\s+(\w+\.py)',
            r'(\w+\.py)\s+file',
            r'modify\s+(\w+\.py)',
            r'update\s+(\w+\.py)',
            r'edit\s+(\w+\.py)',
            r'change\s+(\w+\.py)',
            r'create\s+(\w+\.py)',
            r'add.*?(\w+\.py)',
        ]
        for pattern in patterns:
            match = re.search(pattern, issue.lower())
            if match:
                return match.group(1)
        return None

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

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract relevant keywords from issue text."""
        stopwords = {
            'a', 'an', 'the', 'is', 'are', 'was', 'were', 'be', 'been',
            'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
            'would', 'could', 'should', 'may', 'might', 'must', 'shall',
            'can', 'need', 'to', 'of', 'in', 'for', 'on', 'with', 'at',
            'by', 'from', 'as', 'into', 'through', 'during', 'before',
            'after', 'above', 'below', 'between', 'under', 'again',
            'further', 'then', 'once', 'and', 'but', 'or', 'nor', 'so',
            'yet', 'both', 'each', 'few', 'more', 'most', 'other', 'some',
            'such', 'no', 'not', 'only', 'own', 'same', 'than', 'too',
            'very', 'just', 'create', 'add', 'implement', 'feature'
        }
        words = text.replace(',', ' ').replace('.', ' ').split()
        return [w for w in words if w not in stopwords and len(w) > 2][:10]
