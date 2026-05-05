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

# ── Required environment variables ──────────────────────────────────────────
_REQUIRED_ENV = [
    "GITHUB_TOKEN",
    "GITHUB_REPO_OWNER",
    "GITHUB_REPO_NAME",
]

_OPTIONAL_ENV_DEFAULTS = {
    "GITHUB_BASE_BRANCH": "main",
}

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


@app.on_event("startup")
async def validate_env() -> None:
    """Fail fast on startup if required environment variables are missing.

    Without this, the pipeline runs Orchestrator and RepoReader successfully
    before discovering that GITHUB_TOKEN is missing when PRManager runs —
    wasting minutes of LLM calls.
    """
    missing = [v for v in _REQUIRED_ENV if not os.getenv(v)]
    if missing:
        raise RuntimeError(
            f"Missing required environment variables: {missing}. "
            "Check your .env file before starting the server."
        )


# ── Internal-field filter ────────────────────────────────────────────────────
# These fields are used as an inter-agent bus and must never be returned to
# the API caller: they carry raw file contents (potentially MBs of text) and
# the full message log that is only useful for internal debugging.
_INTERNAL_FIELDS = {"messages", "file_contents"}


def _public_response(state: Dict[str, Any]) -> Dict[str, Any]:
    """Strip internal pipeline fields from a state dict before returning it."""
    return {k: v for k, v in state.items() if k not in _INTERNAL_FIELDS}


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
    Pass the response from POST /plan here — optionally edit implementation_plan before submitting.
    """
    issue: str = ""
    repo_path: str = ""
    repo_context: Dict[str, Any] = {}
    implementation_plan: Dict[str, Any] = {}
    files_to_modify: List[str] = []


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
    3. **Analyst** — produces a detailed implementation plan (LLM picks the files)

    Returns the plan for user review. Edit `implementation_plan` or `files_to_modify`
    as needed, then pass the full response to `POST /execute`.
    """
    repo_path = request.repo_path or os.getcwd()
    pipeline = AgentPipeline(repo_path=repo_path)

    try:
        full_state = await pipeline.run_planning(request.issue)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # Return only what the user needs to review — strip internal blobs
    return {
        "issue": full_state.get("issue", request.issue),
        "repo_path": full_state.get("repo_path", repo_path),
        "repo_context": {
            k: v for k, v in full_state.get("repo_context", {}).items()
            if k != "_orchestrator_metadata"
        },
        "implementation_plan": full_state.get("implementation_plan", {}),
        "files_to_modify": full_state.get("files_to_modify", []),
        "status": full_state.get("status", ""),
        "errors": full_state.get("errors", []),
    }


@app.post("/execute", summary="Phase 2 — Execute")
async def execute(request: ExecuteRequest) -> Dict[str, Any]:
    """
    **Phase 2 — Execution**

    Agents executed in order:
    1. **Coder** — creates a feature branch and generates code changes
    2. **Reviewer** — reviews the diff; loops back to Coder if errors are found
    3. **Tester** — generates and commits pytest test files
    4. **PRManager** — pushes the branch and opens a GitHub Pull Request

    Input: the response from `POST /plan` (optionally with `implementation_plan` edited).
    Output: PR URL, test results, review findings, and final status.
    """
    pipeline = AgentPipeline(repo_path=request.repo_path or os.getcwd())

    try:
        result = await pipeline.run_execution(request.model_dump())
        return _public_response(result)
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
