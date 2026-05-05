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
    """Severity levels for review findings."""
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
    2. Uses LLM to analyze code quality
    3. Identifies issues and provides suggestions
    4. Returns detailed review findings
    """
    
    def __init__(self):
        super().__init__(
            name="Reviewer",
            description="Reviews code using LLM-powered analysis"
        )
        # Load prompt from file
        self.prompt = get_prompt("reviewer", default="")
        self.llm = get_llm()
    
    async def execute(self, state: AgentState) -> AgentState:
        """Execute the LLM-powered code review workflow."""
        import time
        start_time = time.time()
        
        # Log input
        self.log_input(state)
        self.log("Starting LLM-powered code review...", {
            "branch": state.branch_name, 
            "files_to_review": list(state.code_changes.keys())
        })
        
        try:
            # Step 1: Get git diff
            git_diff = self._get_git_diff(state.repo_path, state.branch_name)
            state.git_diff = git_diff
            self.log("Got git diff", {"diff_length": len(git_diff)})
            
            # Step 2: Use LLM to review the code changes
            findings = await self._review_with_llm(
                state.code_changes,
                git_diff,
                state.issue,
                state.implementation_plan
            )
            
            self.log("LLM review completed", {"findings_count": len(findings)})
            
            # Step 3: Generate summary
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
            
            self.log(f"Review completed with {len(findings)} findings", {
                "approval_status": approval_status, 
                "summary": review_summary
            })
            
            # Log output
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
        """
        Use LLM to perform comprehensive code review.
        
        This is the core LLM-powered review method.
        """
        all_findings = []
        
        for file_path, content in code_changes.items():
            self.log(f"Reviewing: {file_path}")
            
            # Build the prompt for code review
            prompt = self._build_review_prompt(
                file_path=file_path,
                content=content,
                issue=issue,
                implementation_plan=implementation_plan
            )
            
            try:
                # Call LLM to review the code
                response = await self.llm.generate(
                    prompt=prompt,
                    system_prompt=self.prompt,
                    temperature=0.3
                )
                
                # Parse the response into findings
                findings = self._parse_review_response(response, file_path)
                all_findings.extend(findings)
                
                self.log(f"Found {len(findings)} issues in {file_path}")
                
            except Exception as e:
                self.log(f"LLM review failed for {file_path}: {e}")
                # Fallback to basic checks
                basic_findings = self._basic_code_checks(file_path, content)
                all_findings.extend(basic_findings)
        
        return all_findings
    
    def _build_review_prompt(
        self,
        file_path: str,
        content: str,
        issue: str,
        implementation_plan: Dict[str, Any]
    ) -> str:
        """Build a comprehensive prompt for code review."""
        
        prompt_parts = [
            "Review the following code for quality, security, and best practices.",
            "",
            f"## File: {file_path}",
            "",
            f"## Original Request:",
            issue[:500],
            "",
            "## Code to Review:",
            "```",
            content[:8000],  # Limit to avoid token overflow
            "```",
            ""
        ]
        
        if len(content) > 8000:
            prompt_parts.append("(Code truncated)")
            prompt_parts.append("")
        
        prompt_parts.extend([
            "## Review Criteria:",
            "1. Code Style: Line length, formatting, consistency",
            "2. Security: Hardcoded secrets, dangerous functions, input validation",
            "3. Documentation: Docstrings, comments, clarity",
            "4. Error Handling: Exception handling, edge cases",
            "5. Naming Conventions: PEP 8 compliance (Python)",
            "6. Logic: Potential bugs, edge cases, performance",
            "",
            "## Required Output (JSON format):",
            "Return a JSON array of findings:",
            "```json",
            "[",
            "  {",
            '    "line": 10,',
            '    "severity": "error|warning|info|suggestion",',
            '    "message": "Description of the issue",',
            '    "suggestion": "How to fix it"',
            "  }",
            "]",
            "```",
            "",
            "If no issues found, return an empty array: []",
            "Provide ONLY the JSON array, no additional text."
        ])
        
        return "\n".join(prompt_parts)
    
    def _parse_review_response(self, response: str, file_path: str) -> List[ReviewFinding]:
        """Parse the LLM response into ReviewFinding objects."""
        findings = []
        response = response.strip()
        
        # Remove markdown code blocks if present
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
            # Try to extract JSON from the response
            json_match = re.search(r'\[[\s\S]*\]', response)
            if json_match:
                try:
                    return self._parse_review_response(json_match.group(), file_path)
                except:
                    pass
        
        return findings
    
    def _basic_code_checks(self, file_path: str, content: str) -> List[ReviewFinding]:
        """Basic fallback code checks when LLM fails."""
        findings = []
        
        if not file_path.endswith('.py'):
            return findings
        
        lines = content.split('\n') if content else []
        
        for i, line in enumerate(lines, 1):
            # Check line length
            if len(line) > 120:
                findings.append(ReviewFinding(
                    file=file_path,
                    line=i,
                    severity=Severity.WARNING,
                    message=f"Line exceeds 120 characters ({len(line)} chars)",
                    suggestion="Consider breaking this line into multiple lines"
                ))
            
            # Check for hardcoded passwords/secrets
            if re.search(r'(password|secret|api_key)\s*=\s*["\'][^"\']+["\']', line, re.IGNORECASE):
                findings.append(ReviewFinding(
                    file=file_path,
                    line=i,
                    severity=Severity.ERROR,
                    message="Potential hardcoded secret detected",
                    suggestion="Use environment variables or secure secret management"
                ))
            
            # Check for bare except
            if re.match(r'\s*except\s*:', line):
                findings.append(ReviewFinding(
                    file=file_path,
                    line=i,
                    severity=Severity.WARNING,
                    message="Bare except clause detected",
                    suggestion="Specify the exception type(s) to catch"
                ))
        
        return findings
    
    def _get_git_diff(self, repo_path: str, branch_name: str) -> str:
        """Get the git diff for the current changes."""
        if not repo_path or not os.path.exists(repo_path):
            return ""
        
        try:
            # Get diff against main/master branch
            result = subprocess.run(
                ["git", "diff", "HEAD~1", "--unified=3"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout
        except subprocess.CalledProcessError:
            # Fallback: get diff of staged changes
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
                raise GitNotFoundError("Git is not installed or not found in PATH. Please install Git to continue.")
        except FileNotFoundError:
            # Git is not installed or not in PATH
            self.log("Git not found - stopping execution")
            raise GitNotFoundError("Git is not installed or not found in PATH. Please install Git to continue.")
    
    def _parse_diff(self, diff: str) -> Dict[str, List[Dict[str, Any]]]:
        """Parse git diff into structured data."""
        files = {}
        current_file = None
        current_changes = []
        
        for line in diff.split('\n'):
            if line.startswith('diff --git'):
                if current_file:
                    files[current_file] = current_changes
                # Extract filename
                match = re.search(r'b/(.+)$', line)
                current_file = match.group(1) if match else None
                current_changes = []
            elif line.startswith('+') and not line.startswith('+++'):
                current_changes.append({
                    "type": "addition",
                    "content": line[1:]
                })
            elif line.startswith('-') and not line.startswith('---'):
                current_changes.append({
                    "type": "deletion",
                    "content": line[1:]
                })
        
        if current_file:
            files[current_file] = current_changes
        
        return files
    
    def _review_file(self, file_path: str, changes: List[Dict], full_content: str) -> List[ReviewFinding]:
        """Review a single file and return findings."""
        findings = []
        
        for check in self.checks:
            check_findings = check(file_path, changes, full_content)
            findings.extend(check_findings)
        
        return findings
    
    def _check_code_style(self, file_path: str, changes: List[Dict], content: str) -> List[ReviewFinding]:
        """Check for code style issues."""
        findings = []
        
        if not file_path.endswith('.py'):
            return findings
        
        lines = content.split('\n') if content else []
        
        for i, line in enumerate(lines, 1):
            # Check line length
            if len(line) > 120:
                findings.append(ReviewFinding(
                    file=file_path,
                    line=i,
                    severity=Severity.WARNING,
                    message=f"Line exceeds 120 characters ({len(line)} chars)",
                    suggestion="Consider breaking this line into multiple lines"
                ))
            
            # Check for trailing whitespace
            if line.endswith(' ') or line.endswith('\t'):
                findings.append(ReviewFinding(
                    file=file_path,
                    line=i,
                    severity=Severity.INFO,
                    message="Trailing whitespace detected",
                    suggestion="Remove trailing whitespace"
                ))
        
        return findings
    
    def _check_security_issues(self, file_path: str, changes: List[Dict], content: str) -> List[ReviewFinding]:
        """Check for potential security issues."""
        findings = []
        lines = content.split('\n') if content else []
        
        security_patterns = [
            (r'password\s*=\s*["\'][^"\']+["\']', "Hardcoded password detected"),
            (r'api_key\s*=\s*["\'][^"\']+["\']', "Hardcoded API key detected"),
            (r'secret\s*=\s*["\'][^"\']+["\']', "Hardcoded secret detected"),
            (r'eval\s*\(', "Use of eval() is potentially dangerous"),
            (r'exec\s*\(', "Use of exec() is potentially dangerous"),
            (r'subprocess\.call\s*\([^)]*shell\s*=\s*True', "shell=True in subprocess is dangerous"),
        ]
        
        for i, line in enumerate(lines, 1):
            for pattern, message in security_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    findings.append(ReviewFinding(
                        file=file_path,
                        line=i,
                        severity=Severity.ERROR,
                        message=message,
                        suggestion="Consider using environment variables or secure secret management"
                    ))
        
        return findings
    
    def _check_documentation(self, file_path: str, changes: List[Dict], content: str) -> List[ReviewFinding]:
        """Check for missing documentation."""
        findings = []
        
        if not file_path.endswith('.py'):
            return findings
        
        lines = content.split('\n') if content else []
        
        # Check for module docstring
        if lines and not (lines[0].startswith('"""') or lines[0].startswith("'''")):
            findings.append(ReviewFinding(
                file=file_path,
                line=1,
                severity=Severity.SUGGESTION,
                message="Missing module docstring",
                suggestion="Add a docstring at the beginning of the module"
            ))
        
        # Check for function/class docstrings
        for i, line in enumerate(lines):
            if re.match(r'\s*(def|class)\s+\w+', line):
                # Check if next non-empty line is a docstring
                next_line_idx = i + 1
                while next_line_idx < len(lines) and not lines[next_line_idx].strip():
                    next_line_idx += 1
                
                if next_line_idx < len(lines):
                    next_line = lines[next_line_idx].strip()
                    if not (next_line.startswith('"""') or next_line.startswith("'''")):
                        findings.append(ReviewFinding(
                            file=file_path,
                            line=i + 1,
                            severity=Severity.SUGGESTION,
                            message="Missing docstring for function/class",
                            suggestion="Add a docstring describing the purpose and parameters"
                        ))
        
        return findings
    
    def _check_error_handling(self, file_path: str, changes: List[Dict], content: str) -> List[ReviewFinding]:
        """Check for proper error handling."""
        findings = []
        lines = content.split('\n') if content else []
        
        for i, line in enumerate(lines):
            # Check for bare except
            if re.match(r'\s*except\s*:', line):
                findings.append(ReviewFinding(
                    file=file_path,
                    line=i + 1,
                    severity=Severity.WARNING,
                    message="Bare except clause detected",
                    suggestion="Specify the exception type(s) to catch"
                ))
            
            # Check for pass in except
            if 'except' in line and i + 1 < len(lines) and 'pass' in lines[i + 1].strip():
                findings.append(ReviewFinding(
                    file=file_path,
                    line=i + 2,
                    severity=Severity.WARNING,
                    message="Exception silently ignored",
                    suggestion="Consider logging the exception or handling it appropriately"
                ))
        
        return findings
    
    def _check_naming_conventions(self, file_path: str, changes: List[Dict], content: str) -> List[ReviewFinding]:
        """Check for naming convention issues."""
        findings = []
        
        if not file_path.endswith('.py'):
            return findings
        
        lines = content.split('\n') if content else []
        
        for i, line in enumerate(lines):
            # Check class names (should be CamelCase)
            match = re.match(r'\s*class\s+(\w+)', line)
            if match:
                class_name = match.group(1)
                if not re.match(r'^[A-Z][a-zA-Z0-9]*$', class_name):
                    findings.append(ReviewFinding(
                        file=file_path,
                        line=i + 1,
                        severity=Severity.INFO,
                        message=f"Class name '{class_name}' should use CamelCase",
                        suggestion="Rename to follow PEP 8 naming conventions"
                    ))
            
            # Check function names (should be snake_case)
            match = re.match(r'\s*def\s+(\w+)', line)
            if match:
                func_name = match.group(1)
                if not func_name.startswith('_') and not re.match(r'^[a-z][a-z0-9_]*$', func_name):
                    if func_name not in ('setUp', 'tearDown', 'setUpClass', 'tearDownClass'):
                        findings.append(ReviewFinding(
                            file=file_path,
                            line=i + 1,
                            severity=Severity.INFO,
                            message=f"Function name '{func_name}' should use snake_case",
                            suggestion="Rename to follow PEP 8 naming conventions"
                        ))
        
        return findings
    
    def _generate_review_summary(self, findings: List[ReviewFinding]) -> Dict[str, Any]:
        """Generate a summary of the review findings."""
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
        """Get a recommendation based on findings."""
        if severity_counts["error"] > 0:
            return "Changes required - critical issues found"
        elif severity_counts["warning"] > 3:
            return "Changes suggested - multiple warnings found"
        elif severity_counts["warning"] > 0:
            return "Approve with suggestions"
        else:
            return "Approved - looks good!"
    
    def _determine_approval_status(self, findings: List[ReviewFinding]) -> str:
        """Determine if the code should be approved."""
        error_count = sum(1 for f in findings if f.severity == Severity.ERROR)
        
        if error_count > 0:
            return "changes_requested"
        else:
            return "approved"
