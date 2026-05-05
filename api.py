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
    repo_path: Optional[str] = Field(
        None,
        description="Absolute path to the local repository. Defaults to CWD.",
    )


class ExecuteRequest(BaseModel):
    """
    The full planning state returned by POST /plan.
    Copy the entire response body and post it here unchanged.
    """
    issue: str = ""
    repo_path: str = ""
    branch_name: str = ""
    repo_context: Dict[str, Any] = {}
    file_contents: Dict[str, str] = {}
    implementation_plan: Dict[str, Any] = {}
    files_to_modify: List[str] = []
    code_changes: Dict[str, str] = {}
    git_diff: str = ""
    review_findings: List[Any] = []
    test_files: Dict[str, str] = {}
    pr_url: str = ""
    status: str = "pending"
    errors: List[str] = []
    current_agent: str = ""
    messages: List[Any] = []


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
    repo_path = request.repo_path or os.getcwd()
    pipeline = AgentPipeline(repo_path=repo_path)

    try:
        result = await pipeline.run_planning(request.issue)
        return result
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

    Input: the response body from `POST /plan`.
    Output: PR URL, test results, review findings, and final status.
    """
    pipeline = AgentPipeline(repo_path=request.repo_path or os.getcwd())

    try:
        result = await pipeline.run_execution(request.model_dump())
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8000"))
    reload = os.getenv("API_RELOAD", "false").lower() == "true"

    uvicorn.run("api:app", host=host, port=port, reload=reload)
