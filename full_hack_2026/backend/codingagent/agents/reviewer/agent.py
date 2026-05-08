"""Reviewer Agent - Reviews code changes using LLM-powered analysis."""

import os
import subprocess
import re
import json
from typing import Dict, Any, List
from dataclasses import dataclass
from enum import Enum
from agents.base import BaseAgent, AgentState
from prompts import get_prompt
from model import get_llm


class GitNotFoundError(Exception):
    """Raised when Git is not installed or not found in PATH."""
    pass


class Severity(Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    SUGGESTION = "suggestion"


@dataclass
class ReviewFinding:
    """A single review finding."""
    file: str
    line: int
    severity: Severity
    message: str
    suggestion: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file": self.file,
            "line": self.line,
            "severity": self.severity.value,
            "message": self.message,
            "suggestion": self.suggestion
        }


class ReviewerAgent(BaseAgent):
    """
    The Reviewer Agent using LLM-powered code review:
    1. Reads git diff of changes
    2. Uses LLM to analyse code quality
    3. Identifies issues and provides suggestions
    4. Returns detailed review findings
    """

    def __init__(self):
        super().__init__(
            name="Reviewer",
            description="Reviews code using LLM-powered analysis"
        )
        self.prompt = get_prompt("reviewer", default="")
        self.llm = get_llm()

    async def execute(self, state: AgentState) -> AgentState:
        """Execute the LLM-powered code review workflow."""
        import time
        start_time = time.time()

        self.log_input(state)
        self.log("Starting LLM-powered code review...", {
            "branch": state.branch_name,
            "files_to_review": list(state.code_changes.keys())
        })

        try:
            git_diff = self._get_git_diff(state.repo_path, state.branch_name)
            state.git_diff = git_diff
            self.log("Got git diff", {"diff_length": len(git_diff)})

            findings = await self._review_with_llm(
                state.code_changes,
                git_diff,
                state.issue,
                state.implementation_plan
            )
            self.log("LLM review completed", {"findings_count": len(findings)})

            review_summary = self._generate_review_summary(findings)
            approval_status = self._determine_approval_status(findings)

            state.review_findings = [f.to_dict() for f in findings]
            state.current_agent = self.name
            state.messages.append({
                "agent": self.name,
                "action": "review_completed",
                "data": {
                    "findings_count": len(findings),
                    "summary": review_summary,
                    "approval_status": approval_status
                }
            })

            self.log(f"Review completed: {len(findings)} findings, status={approval_status}")

            duration_ms = (time.time() - start_time) * 1000
            self.log_output(state, duration_ms)
            return state

        except Exception as e:
            self.log_error(e, {"branch": state.branch_name})
            state.errors.append(str(e))
            return state

    async def _review_with_llm(
        self,
        code_changes: Dict[str, str],
        git_diff: str,
        issue: str,
        implementation_plan: Dict[str, Any]
    ) -> List[ReviewFinding]:
        """Use LLM to perform comprehensive code review of every changed file."""
        all_findings = []

        for file_path, content in code_changes.items():
            self.log(f"Reviewing: {file_path}")

            prompt = self._build_review_prompt(
                file_path=file_path,
                content=content,
                issue=issue,
                implementation_plan=implementation_plan
            )

            try:
                response = await self.llm.generate(
                    prompt=prompt,
                    system_prompt=self.prompt,
                    temperature=0.3
                )
                findings = self._parse_review_response(response, file_path)
                all_findings.extend(findings)
                self.log(f"Found {len(findings)} issues in {file_path}")

            except Exception as e:
                self.log(f"LLM review failed for {file_path}, running basic checks: {e}")
                all_findings.extend(self._basic_code_checks(file_path, content))

        return all_findings

    def _build_review_prompt(
        self,
        file_path: str,
        content: str,
        issue: str,
        implementation_plan: Dict[str, Any]
    ) -> str:
        """Build an SDLC-aware, OWASP-informed prompt for production code review."""

        plan_summary = implementation_plan.get("summary", "") if implementation_plan else ""
        security_considerations = implementation_plan.get("security_considerations", []) if implementation_plan else []
        action_type = implementation_plan.get("action_type", "feature") if implementation_plan else "feature"

        prompt_parts = [
            "You are Riley, Senior Code Reviewer and Application Security Engineer in the QA & Review phase of the SDLC.",
            "You are the last line of defence before code reaches production.",
            "Priority order: security > correctness > maintainability > style.",
            "Do not rubber-stamp. Do not nitpick style while missing real bugs.",
            "",
            f"## File Under Review: {file_path}",
            f"## Change Type: {action_type}",
            "",
            "## Original Request:",
            issue[:500],
        ]

        if plan_summary:
            prompt_parts.extend(["", f"## Implementation Plan Summary: {plan_summary}"])

        if security_considerations:
            prompt_parts.extend([
                "",
                "## Security Requirements from Analyst (verify these are met):",
                *[f"- {s}" for s in security_considerations],
            ])

        prompt_parts.extend([
            "",
            "## Code to Review:",
            "```",
            content[:8000],
            "```",
        ])

        if len(content) > 8000:
            prompt_parts.append("(Code truncated — review what is visible)")

        prompt_parts.extend([
            "",
            "## Review Dimensions (in priority order):",
            "",
            "1. CORRECTNESS",
            "   - Does it solve the stated problem completely?",
            "   - Logic errors, off-by-one, incorrect conditionals?",
            "   - Edge cases handled: empty collections, None, zero, negative numbers?",
            "   - Return values consistent with function signatures?",
            "",
            "2. SECURITY (OWASP Top 10)",
            "   - Injection: are ALL DB queries parameterised? No string-concatenated SQL?",
            "   - Auth: passwords hashed with bcrypt/argon2? Not MD5/SHA1/plaintext?",
            "   - Secrets: no hardcoded passwords, tokens, API keys in code?",
            "   - Input Validation: ALL user input validated before use?",
            "   - Access Control: auth checks present before every data operation?",
            "   - Error Messages: no stack traces or system info leaked to caller?",
            "   - eval()/exec(): flag as critical if present",
            "",
            "3. ERROR HANDLING",
            "   - Specific exception types caught (no bare `except:` or `except Exception`)?",
            "   - Exceptions logged with context before handling?",
            "   - Resources (files, DB connections) properly closed in error paths?",
            "",
            "4. CODE QUALITY",
            "   - Single Responsibility per function/class?",
            "   - DRY: duplicated logic that should be centralised?",
            "   - Functions longer than 30 lines or nested deeper than 3 levels?",
            "   - Magic literals that should be named constants?",
            "   - Dead code: unreachable branches, unused imports?",
            "",
            "5. DOCUMENTATION",
            "   - Public classes and functions have docstrings?",
            "   - Type hints on all parameters and return types?",
            "",
            "6. PERFORMANCE",
            "   - DB queries inside loops (N+1 problem)?",
            "   - Synchronous operations that should be async?",
            "",
            "## Required Output (JSON format):",
            "Return a JSON array. Report each issue ONCE at first occurrence. Include praise for exceptional code.",
            "```json",
            "[",
            "  {",
            '    "line": 10,',
            '    "severity": "error|warning|info|suggestion",',
            '    "category": "security|correctness|error_handling|code_quality|documentation|performance|style",',
            '    "message": "Specific description of the issue with the problematic code quoted",',
            '    "suggestion": "Concrete corrected code pattern or fix"',
            "  }",
            "]",
            "```",
            "",
            "Severity guide:",
            "- error: MUST fix before merge — security issue, functional bug, data corruption risk",
            "- warning: SHOULD fix — potential bug, poor error handling, significant quality issue",
            "- info: NICE to fix — minor quality improvement, documentation gap",
            "- suggestion: OPTIONAL — style, readability, minor refactoring",
            "",
            "If no issues found, return: []",
            "Provide ONLY the JSON array, no additional text."
        ])

        return "\n".join(prompt_parts)

    def _parse_review_response(self, response: str, file_path: str) -> List[ReviewFinding]:
        """Parse the LLM response into ReviewFinding objects."""
        findings = []
        response = response.strip()

        if response.startswith("```"):
            lines = response.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            response = "\n".join(lines)

        try:
            items = json.loads(response)
            if isinstance(items, list):
                for item in items:
                    severity_str = item.get("severity", "info").lower()
                    try:
                        severity = Severity(severity_str)
                    except ValueError:
                        severity = Severity.INFO
                    findings.append(ReviewFinding(
                        file=file_path,
                        line=item.get("line", 0),
                        severity=severity,
                        message=item.get("message", ""),
                        suggestion=item.get("suggestion", "")
                    ))
        except json.JSONDecodeError:
            json_match = re.search(r'\[[\s\S]*\]', response)
            if json_match:
                try:
                    return self._parse_review_response(json_match.group(), file_path)
                except Exception:
                    pass

        return findings

    def _basic_code_checks(self, file_path: str, content: str) -> List[ReviewFinding]:
        """Fallback static checks used when LLM call fails."""
        findings = []

        if not file_path.endswith('.py'):
            return findings

        lines = content.split('\n') if content else []

        for i, line in enumerate(lines, 1):
            if len(line) > 120:
                findings.append(ReviewFinding(
                    file=file_path, line=i, severity=Severity.WARNING,
                    message=f"Line exceeds 120 characters ({len(line)} chars)",
                    suggestion="Break this line into multiple lines"
                ))

            if re.search(r'(password|secret|api_key)\s*=\s*["\'][^"\']+["\']', line, re.IGNORECASE):
                findings.append(ReviewFinding(
                    file=file_path, line=i, severity=Severity.ERROR,
                    message="Potential hardcoded secret detected",
                    suggestion="Use environment variables or a secrets manager"
                ))

            if re.match(r'\s*except\s*:', line):
                findings.append(ReviewFinding(
                    file=file_path, line=i, severity=Severity.WARNING,
                    message="Bare except clause detected",
                    suggestion="Specify the exception type(s) to catch"
                ))

        return findings

    def _get_git_diff(self, repo_path: str, branch_name: str) -> str:
        """Get the git diff for the current branch changes."""
        if not repo_path or not os.path.exists(repo_path):
            return ""

        try:
            result = subprocess.run(
                ["git", "diff", "HEAD~1", "--unified=3"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout
        except subprocess.CalledProcessError:
            try:
                result = subprocess.run(
                    ["git", "diff", "--cached", "--unified=3"],
                    cwd=repo_path,
                    capture_output=True,
                    text=True,
                    check=True
                )
                return result.stdout
            except (subprocess.CalledProcessError, FileNotFoundError):
                raise GitNotFoundError(
                    "Git is not installed or not found in PATH."
                )
        except FileNotFoundError:
            self.log("Git not found")
            raise GitNotFoundError("Git is not installed or not found in PATH.")

    def _generate_review_summary(self, findings: List[ReviewFinding]) -> Dict[str, Any]:
        """Generate a summary of all review findings."""
        severity_counts = {s.value: 0 for s in Severity}
        for finding in findings:
            severity_counts[finding.severity.value] += 1

        return {
            "total_findings": len(findings),
            "by_severity": severity_counts,
            "files_reviewed": len(set(f.file for f in findings)) if findings else 0,
            "recommendation": self._get_recommendation(severity_counts)
        }

    def _get_recommendation(self, severity_counts: Dict[str, int]) -> str:
        """Produce a human-readable recommendation from severity counts."""
        if severity_counts["error"] > 0:
            return "Changes required - critical issues found"
        elif severity_counts["warning"] > 3:
            return "Changes suggested - multiple warnings found"
        elif severity_counts["warning"] > 0:
            return "Approve with suggestions"
        return "Approved - looks good!"

    def _determine_approval_status(self, findings: List[ReviewFinding]) -> str:
        """Return approval status based on whether any errors were found."""
        if any(f.severity == Severity.ERROR for f in findings):
            return "changes_requested"
        return "approved"
