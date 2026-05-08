"""
Multi-Agent Development Pipeline API

Two endpoints:
  POST /plan    — Phase 1: Orchestrator → RepoReader → Analyst
  POST /execute — Phase 2: Coder → Reviewer → Tester → PRManager
"""

import os
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from workflow.pipeline import AgentPipeline

load_dotenv()

# Derive repo_path from .env GitHub configuration
def get_repo_path() -> str:
    """Get the local repo path based on GitHub config from .env"""
    repo_name = os.getenv("GITHUB_REPO_NAME", "")
    if repo_name:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(base_dir, ".repos", repo_name)
    return os.getcwd()

app = FastAPI(
    title="Multi-Agent Development Pipeline",
    description=(
        "Two-phase AI pipeline.\n\n"
        "1. **POST /plan** — submit an issue; get back an implementation plan.\n"
        "2. **POST /execute** — pass the plan response to generate code, review, tests, and a PR."
    ),
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class PlanRequest(BaseModel):
    issue: str = Field(
        ...,
        description="The feature request or bug report to implement.",
        examples=["Add user authentication with JWT tokens"],
    )


class ExecuteRequest(BaseModel):
    """
    The implementation plan returned by POST /plan.
    Pass the implementation_plan object to execute.
    """
    implementation_plan: Dict[str, Any] = Field(
        ...,
        description="The implementation plan from POST /plan response.",
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.post("/plan", summary="Phase 1 — Plan")
async def plan(request: PlanRequest) -> Dict[str, Any]:
    """
    **Phase 1 — Planning**

    Agents executed in order:
    1. **Orchestrator** — parses the issue, detects type and complexity
    2. **RepoReader** — clones the GitHub repo and indexes file contents
    3. **Analyst** — uses the repo context to produce a detailed implementation plan

    Returns the full pipeline state. Pass this response body directly to
    `POST /execute` to continue.
    """
    repo_path = get_repo_path()
    pipeline = AgentPipeline(repo_path=repo_path)

    try:
        result = await pipeline.run_planning(request.issue)
        # Return only the implementation_plan field
        return {
            "implementation_plan": result.get("implementation_plan", {})
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/execute", summary="Phase 2 — Execute")
async def execute(request: ExecuteRequest) -> Dict[str, Any]:
    """
    **Phase 2 — Execution**

    Agents executed in order:
    1. **Coder** — creates a feature branch and generates code changes
    2. **Reviewer** — reviews the diff; loops back to Coder if errors are found
    3. **Tester** — generates and commits pytest test files
    4. **PRManager** — pushes the branch and opens a GitHub Pull Request

    Input: the implementation_plan from `POST /plan` response.
    Output: PR URL, test results, review findings, and final status.
    """
    repo_path = get_repo_path()
    pipeline = AgentPipeline(repo_path=repo_path)

    # Extract files to modify/create from implementation_plan
    impl_plan = request.implementation_plan
    files_to_create = [f.get("path") for f in impl_plan.get("files_to_create", []) if f.get("path")]
    files_to_modify = [f.get("path") for f in impl_plan.get("files_to_modify", []) if f.get("path")]
    all_files = files_to_create + files_to_modify
    
    # Debug logging
    print(f"[API] repo_path: {repo_path}")
    print(f"[API] files_to_create: {files_to_create}")
    print(f"[API] files_to_modify: {files_to_modify}")
    print(f"[API] all_files ({len(all_files)}): {all_files}")

    # Build full planning state from implementation_plan
    planning_state = {
        "issue": impl_plan.get("summary", ""),
        "repo_path": repo_path,
        "branch_name": "",
        "repo_context": {},
        "file_contents": {},
        "implementation_plan": impl_plan,
        "files_to_modify": all_files,
        "code_changes": {},
        "git_diff": "",
        "review_findings": [],
        "test_files": {},
        "test_results": {},
        "test_iteration": 0,
        "pr_url": "",
        "status": "planning_complete",
        "errors": [],
        "current_agent": "",
        "messages": []
    }

    try:
        result = await pipeline.run_execution(planning_state)
        
        # Build a user-friendly summary of what the agents did
        summary = _build_execution_summary(result)
        
        return {
            "summary": summary,
            "details": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _build_execution_summary(result: Dict[str, Any]) -> Dict[str, Any]:
    """Build a user-friendly summary of the execution results."""
    
    status = result.get("status", "unknown")
    pr_url = result.get("pr_url", "")
    branch_name = result.get("branch_name", "")
    files_modified = result.get("files_to_modify", [])
    review_findings_count = len(result.get("review_findings", []))
    test_results = result.get("test_results", {})
    errors = result.get("errors", [])
    
    # Determine overall outcome
    if status == "completed" and pr_url:
        outcome = "✅ SUCCESS"
        message = "The agents have successfully completed the implementation!"
    elif status == "error":
        outcome = "❌ ERROR"
        message = "The pipeline encountered errors during execution."
    else:
        outcome = "⚠️ PARTIAL"
        message = "The pipeline completed with some issues."
    
    # Build agent actions summary
    agent_actions = []
    
    # Coder summary
    if files_modified:
        agent_actions.append({
            "agent": "Coder",
            "action": f"Modified/created {len(files_modified)} file(s)",
            "files": files_modified[:10]  # Show first 10 files
        })
    
    # Reviewer summary
    if review_findings_count > 0:
        agent_actions.append({
            "agent": "Reviewer",
            "action": f"Found {review_findings_count} issue(s) during code review"
        })
    else:
        agent_actions.append({
            "agent": "Reviewer",
            "action": "Code review passed with no critical issues"
        })
    
    # Tester summary
    test_status = test_results.get("status", "skipped")
    if test_status == "passed":
        agent_actions.append({
            "agent": "Tester",
            "action": "All tests passed"
        })
    elif test_status == "failed":
        agent_actions.append({
            "agent": "Tester",
            "action": "Some tests failed (see details)"
        })
    else:
        agent_actions.append({
            "agent": "Tester",
            "action": f"Tests {test_status}"
        })
    
    # PR Manager summary
    if pr_url:
        agent_actions.append({
            "agent": "PRManager",
            "action": "Pull Request created successfully"
        })
    
    # Build the summary
    summary = {
        "outcome": outcome,
        "message": message,
        "branch_name": branch_name,
        "pull_request": {
            "url": pr_url,
            "suggestion": f"🔗 Please review the Pull Request: {pr_url}" if pr_url else "No PR was created"
        },
        "agent_actions": agent_actions,
        "files_changed_count": len(files_modified),
        "review_findings_count": review_findings_count,
    }
    
    if errors:
        summary["errors"] = errors
    
    return summary


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8000"))
    reload = os.getenv("API_RELOAD", "false").lower() == "true"

    uvicorn.run("api:app", host=host, port=port, reload=reload)
