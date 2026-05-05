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
        """Build a descriptive PR title."""
        # Extract issue type and create title
        issue_summary = state.issue[:60].strip()
        if len(state.issue) > 60:
            issue_summary += "..."
        
        return f"feat: {issue_summary}"
    
    def _build_pr_body(self, state: AgentState) -> str:
        """Build a detailed PR body with all relevant information."""
        body_parts = [
            "## Summary",
            f"This PR addresses: {state.issue}",
            "",
            "## Changes Made",
        ]
        
        # List files changed
        if state.code_changes:
            body_parts.append("")
            body_parts.append("### Files Modified")
            for file_path in state.code_changes.keys():
                body_parts.append(f"- `{file_path}`")
        
        # Add implementation plan summary
        if state.implementation_plan:
            body_parts.append("")
            body_parts.append("### Implementation Details")
            for step in state.implementation_plan.get("steps", [])[:3]:
                body_parts.append(f"- {step.get('action', '')}: {step.get('description', '')}")
        
        # Add review findings summary
        if state.review_findings:
            body_parts.append("")
            body_parts.append("### Code Review Notes")
            findings_summary = self._summarize_review_findings(state.review_findings)
            body_parts.append(findings_summary)
        
        # Add test information
        if state.test_files:
            body_parts.append("")
            body_parts.append("### Tests Added")
            for test_file in state.test_files.keys():
                body_parts.append(f"- `{test_file}`")
        
        # Add footer
        body_parts.extend([
            "",
            "---",
            "*This PR was automatically generated by the AI Agent Pipeline.*"
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
