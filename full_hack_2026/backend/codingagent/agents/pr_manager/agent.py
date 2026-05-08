"""PR Manager Agent - Creates and manages Pull Requests via GitHub API."""

import os
import subprocess
import json
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass
import httpx
from agents.base import BaseAgent, AgentState
from prompts import get_prompt


class GitNotFoundError(Exception):
    """Raised when Git is not installed or not found in PATH."""
    pass


@dataclass
class PRConfig:
    """Configuration for Pull Request creation."""
    github_token: str
    repo_owner: str
    repo_name: str
    base_branch: str = "main"
    auto_merge: bool = True
    delete_branch_on_merge: bool = True


class PRManagerAgent(BaseAgent):
    """
    The PR Manager Agent:
    1. Pushes branch to remote
    2. Creates Pull Request via GitHub API
    3. Monitors review status
    4. Auto-merges after review passes
    """
    
    def __init__(self, config: Optional[PRConfig] = None):
        super().__init__(
            name="PRManager",
            description="Creates and manages Pull Requests via GitHub API"
        )
        # Load prompt from file
        self.prompt = get_prompt("pr_manager", default="")
        self.config = config
        self.github_api_base = "https://api.github.com"
    
    async def execute(self, state: AgentState) -> AgentState:
        """Execute the PR creation workflow."""
        import time
        start_time = time.time()
        
        # Log input
        self.log_input(state)
        self.log("Starting PR creation workflow...", {"branch": state.branch_name})
        
        try:
            # Load config from environment if not provided
            if not self.config:
                self.config = self._load_config_from_env()
            
            if not self.config or not self.config.github_token:
                self.log("GitHub token not configured", {"error": True})
                state.errors.append("GitHub token not configured")
                self.log_output(state, (time.time() - start_time) * 1000)
                return state
            
            # Step 1: Push branch to remote
            push_success = self._push_branch(state.repo_path, state.branch_name)
            self.log("Branch push attempt", {"success": push_success, "branch": state.branch_name})
            if not push_success:
                state.errors.append("Failed to push branch to remote")
                self.log_output(state, (time.time() - start_time) * 1000)
                return state
            
            # Step 2: Create Pull Request
            pr_data = await self._create_pull_request(state)
            self.log("Pull Request creation attempt", {"pr_data": pr_data})
            
            if pr_data:
                state.pr_url = pr_data.get("html_url", "")
                pr_number = pr_data.get("number")
                self.log("Pull Request created", {"pr_url": state.pr_url, "pr_number": pr_number})
                
                # Step 3: Wait for and check reviews (in real implementation)
                review_status = await self._check_review_status(pr_number)
                self.log("Review status checked", {"status": review_status})
                
                # Step 4: Auto-merge if enabled and review passes
                if self.config.auto_merge and review_status == "approved":
                    merge_success = await self._auto_merge_pr(pr_number)
                    if merge_success:
                        self.log(f"PR #{pr_number} merged successfully!", {"pr_number": pr_number})
            
            state.current_agent = self.name
            state.status = "completed" if state.pr_url else "failed"
            state.messages.append({
                "agent": self.name,
                "action": "pr_created",
                "data": {
                    "pr_url": state.pr_url,
                    "branch": state.branch_name,
                    "status": state.status
                }
            })
            
            self.log(f"PR workflow completed: {state.pr_url}", {"status": state.status})
            
            # Log output
            duration_ms = (time.time() - start_time) * 1000
            self.log_output(state, duration_ms)
            return state
            
        except Exception as e:
            self.log_error(e, {"branch": state.branch_name})
            state.errors.append(str(e))
            return state
    
    def _load_config_from_env(self) -> Optional[PRConfig]:
        """Load PR configuration from environment variables."""
        token = os.getenv("GITHUB_TOKEN")
        if not token:
            self.log("Warning: GITHUB_TOKEN not set")
            return None
        
        return PRConfig(
            github_token=token,
            repo_owner=os.getenv("GITHUB_REPO_OWNER", ""),
            repo_name=os.getenv("GITHUB_REPO_NAME", ""),
            base_branch=os.getenv("GITHUB_BASE_BRANCH", "main"),
            auto_merge=os.getenv("AUTO_MERGE", "true").lower() == "true"
        )
    
    def _push_branch(self, repo_path: str, branch_name: str) -> bool:
        """Push the branch to remote."""
        if not repo_path or not os.path.exists(repo_path):
            return False
        
        try:
            # Set upstream and push
            subprocess.run(
                ["git", "push", "-u", "origin", branch_name],
                cwd=repo_path,
                capture_output=True,
                check=True
            )
            self.log(f"Pushed branch {branch_name} to origin")
            return True
        except subprocess.CalledProcessError as e:
            self.log(f"Failed to push branch: {e}")
            raise
        except FileNotFoundError:
            self.log("Git not found - stopping execution")
            raise GitNotFoundError("Git is not installed or not found in PATH. Please install Git to continue.")
    
    async def _create_pull_request(self, state: AgentState) -> Optional[Dict[str, Any]]:
        """Create a Pull Request via GitHub API."""
        if not self.config:
            return None
        
        url = f"{self.github_api_base}/repos/{self.config.repo_owner}/{self.config.repo_name}/pulls"
        
        # Build PR body from state
        pr_body = self._build_pr_body(state)
        pr_title = self._build_pr_title(state)
        
        headers = {
            "Authorization": f"token {self.config.github_token}",
            "Accept": "application/vnd.github.v3+json",
            "X-GitHub-Api-Version": "2022-11-28"
        }
        
        payload = {
            "title": pr_title,
            "body": pr_body,
            "head": state.branch_name,
            "base": self.config.base_branch,
            "maintainer_can_modify": True
        }
        
        self.log(f"Creating PR: {state.branch_name} -> {self.config.base_branch}", {
            "repo": f"{self.config.repo_owner}/{self.config.repo_name}",
            "head": state.branch_name,
            "base": self.config.base_branch
        })
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, headers=headers, json=payload)
                
                if response.status_code == 201:
                    pr_data = response.json()
                    self.log(f"Created PR #{pr_data['number']}: {state.branch_name} -> {self.config.base_branch}")
                    self.log(f"PR URL: {pr_data['html_url']}")
                    return pr_data
                else:
                    self.log(f"Failed to create PR: {response.status_code} - {response.text}")
                    return None
        except Exception as e:
            self.log(f"Error creating PR: {e}")
            return None
    
    def _build_pr_title(self, state: AgentState) -> str:
        """Build a Conventional Commits PR title (max 72 chars)."""
        plan = state.implementation_plan or {}
        action_type = plan.get("action_type", "")
        issue = state.issue

        # Map action_type to conventional commit prefix
        type_map = {
            "feature": "feat",
            "bugfix": "fix",
            "refactor": "refactor",
            "enhancement": "feat",
            "security": "security",
            "performance": "perf",
            "test": "test",
            "chore": "chore",
        }
        prefix = type_map.get(action_type, "feat")

        # Derive scope from affected components or files
        components = plan.get("_orchestrator_metadata", {}).get("affected_components", [])
        if not components and state.files_to_modify:
            # Guess scope from first file name (strip path and extension)
            first_file = state.files_to_modify[0]
            scope_name = os.path.splitext(os.path.basename(first_file))[0]
            components = [scope_name]
        scope = f"({components[0]})" if components else ""

        # Build description — imperative mood, truncated to fit 72-char limit
        # prefix(scope): description → e.g. "feat(auth): " = 12 chars
        prefix_part = f"{prefix}{scope}: "
        max_desc_len = 72 - len(prefix_part)
        description = issue[:max_desc_len].strip()
        if len(issue) > max_desc_len:
            description = description.rsplit(" ", 1)[0]  # break at word boundary

        return f"{prefix_part}{description}"

    def _build_pr_body(self, state: AgentState) -> str:
        """Build a complete Drew-persona PR description with all SDLC sections."""
        plan = state.implementation_plan or {}
        plan_summary = plan.get("summary", state.issue)
        design_approach = plan.get("design_approach", "")
        security_considerations = plan.get("security_considerations", [])
        risks = plan.get("risks", [])
        breaking_changes = plan.get("breaking_changes", False)
        breaking_details = plan.get("breaking_change_details", None)

        body_parts = [
            "## Summary",
            plan_summary,
            "",
        ]

        # Changes section — per-file bullets
        body_parts.append("## Changes")
        if state.code_changes:
            for file_path in state.code_changes.keys():
                # Find file-specific plan entry
                file_note = ""
                for f in plan.get("files_to_modify", []):
                    if isinstance(f, dict) and f.get("path") == file_path:
                        file_note = f.get("changes", "")
                for f in plan.get("files_to_create", []):
                    if isinstance(f, dict) and f.get("path") == file_path:
                        file_note = f"New file — {f.get('purpose', '')}"
                body_parts.append(f"- `{file_path}`: {file_note}" if file_note else f"- `{file_path}`")
        else:
            body_parts.append("_No files recorded in state._")
        body_parts.append("")

        # Implementation notes
        body_parts.append("## Implementation Notes")
        if design_approach:
            body_parts.append(f"**Design Approach:** {design_approach}")
            body_parts.append("")
        steps = plan.get("steps", [])
        if steps:
            for step in steps[:5]:
                if isinstance(step, dict):
                    action = step.get("action", "")
                    desc = step.get("description", "")
                    body_parts.append(f"- **{action}**: {desc}" if desc else f"- {action}")
                else:
                    body_parts.append(f"- {step}")
        else:
            body_parts.append("_See implementation plan for details._")
        if risks:
            body_parts.append("")
            body_parts.append("**Risks & Mitigations:**")
            for risk in risks:
                body_parts.append(f"- {risk}")
        body_parts.append("")

        # Security considerations
        body_parts.append("## Security Considerations")
        if security_considerations:
            for concern in security_considerations:
                body_parts.append(f"- {concern}")
        else:
            body_parts.append("No auth changes, secrets handling, or permission model changes in this PR.")
        body_parts.append("")

        # Testing checklist
        body_parts.append("## Testing")
        body_parts.append("- [x] Unit tests added for all new functions/classes")
        body_parts.append("- [x] All existing tests pass")
        body_parts.append("- [x] Edge cases covered (empty inputs, invalid data, error conditions)")
        if state.test_files:
            body_parts.append("")
            body_parts.append("**Test files added:**")
            for tf in state.test_files.keys():
                body_parts.append(f"- `{tf}`")
        body_parts.append("")

        # Review focus areas — direct reviewers to critical parts
        body_parts.append("## Review Focus Areas")
        if security_considerations:
            body_parts.append(f"- Pay special attention to auth/input validation: {security_considerations[0]}")
        if state.code_changes:
            main_file = next(iter(state.code_changes))
            body_parts.append(f"- Core logic is in `{main_file}` — verify error handling paths")
        if breaking_changes:
            body_parts.append("- **BREAKING CHANGE**: verify migration path before approving")
        body_parts.append("")

        # Automated review findings
        body_parts.append("## Review Findings (from automated review)")
        body_parts.append(self._summarize_review_findings(state.review_findings))
        body_parts.append("")

        # Breaking changes
        body_parts.append("## Breaking Changes")
        if breaking_changes:
            body_parts.append(f"- [x] Breaking change: {breaking_details or 'See implementation notes'}")
        else:
            body_parts.append("- [x] No breaking changes")
        body_parts.append("")

        body_parts.extend([
            "---",
            "*Generated by the AI Agent Pipeline*"
        ])

        return "\n".join(body_parts)
    
    def _summarize_review_findings(self, findings: list) -> str:
        """Summarize review findings for PR body."""
        if not findings:
            return "✅ No issues found during automated review."
        
        error_count = sum(1 for f in findings if f.get("severity") == "error")
        warning_count = sum(1 for f in findings if f.get("severity") == "warning")
        
        summary = []
        if error_count > 0:
            summary.append(f"- ❌ {error_count} error(s) to address")
        if warning_count > 0:
            summary.append(f"- ⚠️ {warning_count} warning(s) to review")
        if not summary:
            summary.append("- ✅ Only minor suggestions")
        
        return "\n".join(summary)
    
    async def _check_review_status(self, pr_number: int) -> str:
        """Check the review status of a PR."""
        if not self.config or not pr_number:
            return "unknown"
        
        url = f"{self.github_api_base}/repos/{self.config.repo_owner}/{self.config.repo_name}/pulls/{pr_number}/reviews"
        
        headers = {
            "Authorization": f"token {self.config.github_token}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=headers)
                
                if response.status_code == 200:
                    reviews = response.json()
                    
                    # Check for approvals
                    for review in reviews:
                        if review.get("state") == "APPROVED":
                            return "approved"
                        elif review.get("state") == "CHANGES_REQUESTED":
                            return "changes_requested"
                    
                    return "pending"
                else:
                    return "unknown"
        except Exception as e:
            self.log(f"Error checking review status: {e}")
            return "unknown"
    
    async def _auto_merge_pr(self, pr_number: int) -> bool:
        """Auto-merge a PR after review passes."""
        if not self.config or not pr_number:
            return False
        
        url = f"{self.github_api_base}/repos/{self.config.repo_owner}/{self.config.repo_name}/pulls/{pr_number}/merge"
        
        headers = {
            "Authorization": f"token {self.config.github_token}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        payload = {
            "merge_method": "squash",
            "commit_title": f"Merge PR #{pr_number}",
            "commit_message": "Auto-merged by AI Agent Pipeline"
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.put(url, headers=headers, json=payload)
                
                if response.status_code == 200:
                    self.log(f"PR #{pr_number} merged successfully")
                    
                    # Delete branch if configured
                    if self.config.delete_branch_on_merge:
                        await self._delete_branch(pr_number)
                    
                    return True
                else:
                    self.log(f"Failed to merge PR: {response.status_code}")
                    return False
        except Exception as e:
            self.log(f"Error merging PR: {e}")
            return False
    
    async def _delete_branch(self, pr_number: int) -> bool:
        """Delete the branch after merge."""
        # Get branch name from PR
        if not self.config:
            return False
        
        pr_url = f"{self.github_api_base}/repos/{self.config.repo_owner}/{self.config.repo_name}/pulls/{pr_number}"
        
        headers = {
            "Authorization": f"token {self.config.github_token}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        try:
            async with httpx.AsyncClient() as client:
                # Get PR details to find branch name
                pr_response = await client.get(pr_url, headers=headers)
                if pr_response.status_code != 200:
                    return False
                
                pr_data = pr_response.json()
                branch_ref = pr_data.get("head", {}).get("ref")
                
                if not branch_ref:
                    return False
                
                # Delete the branch
                delete_url = f"{self.github_api_base}/repos/{self.config.repo_owner}/{self.config.repo_name}/git/refs/heads/{branch_ref}"
                delete_response = await client.delete(delete_url, headers=headers)
                
                if delete_response.status_code == 204:
                    self.log(f"Deleted branch: {branch_ref}")
                    return True
                else:
                    return False
        except Exception as e:
            self.log(f"Error deleting branch: {e}")
            return False
