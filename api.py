"""
Multi-Agent Development Pipeline API

This FastAPI application provides endpoints to interact with
an AI-powered development pipeline that automates code implementation,
review, testing, and PR creation using specialized agents.

Agents Overview:
- Orchestrator: Coordinates the pipeline and delegates tasks
- Analyst: Analyzes repository and creates implementation plans
- Coder: Implements code changes and commits to git
- Reviewer: Reviews code for quality, security, and best practices
- Tester: Generates and runs tests for new code
- PRManager: Creates and manages Pull Requests via GitHub API
"""

import os
import uuid
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from enum import Enum

# Import agents and pipeline
from agents import (
    OrchestratorAgent,
    RepoReaderAgent,
    AnalystAgent,
    CoderAgent,
    ReviewerAgent,
    TesterAgent,
    PRManagerAgent
)
from agents.base import AgentState
from workflow.pipeline import AgentPipeline
from logger import agent_logger

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="Multi-Agent Development Pipeline API",
    description="""
    AI-powered automated development workflow with specialized agents.
    
    ## Features
    - **Full Pipeline Execution**: Run complete development workflow from issue to PR
    - **Individual Agent Execution**: Run specific agents independently
    - **Background Processing**: Long-running tasks execute in background
    - **Real-time Status**: Track pipeline progress
    
    ## Agents
    - **Orchestrator**: Parses requirements and coordinates workflow
    - **Analyst**: Analyzes repo structure and creates implementation plans
    - **Coder**: Creates branches, implements code, and commits changes
    - **Reviewer**: Reviews code for quality, security, and documentation
    - **Tester**: Generates and runs unit tests
    - **PRManager**: Creates Pull Requests via GitHub API
    """,
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== Enums ====================

class PipelineStatus(str, Enum):
    """Pipeline execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    ERROR = "error"


class AgentType(str, Enum):
    """Available agent types."""
    ORCHESTRATOR = "orchestrator"
    REPO_READER = "repo_reader"
    ANALYST = "analyst"
    CODER = "coder"
    REVIEWER = "reviewer"
    TESTER = "tester"
    PR_MANAGER = "pr_manager"


# ==================== Request Models ====================

class IssueRequest(BaseModel):
    """Request model for creating a new pipeline run."""
    issue: str = Field(
        ..., 
        description="The issue or feature request to implement",
        json_schema_extra={"example": "Create a login feature with password validation"}
    )
    repo_path: Optional[str] = Field(
        None, 
        description="Path to the repository (defaults to current working directory)"
    )


class AgentExecuteRequest(BaseModel):
    """Request model for executing a specific agent."""
    issue: str = Field(..., description="The issue or task description")
    repo_path: Optional[str] = Field(None, description="Path to the repository")
    state: Optional[Dict[str, Any]] = Field(
        None, 
        description="Optional initial state to pass to the agent"
    )


# ==================== Response Models ====================

class AgentInfoResponse(BaseModel):
    """Information about an agent."""
    name: str
    description: str
    responsibilities: List[str]


class PipelineRunResponse(BaseModel):
    """Response model for pipeline execution."""
    run_id: str
    status: str
    current_agent: str
    messages: List[Dict[str, Any]] = []
    pr_url: Optional[str] = None
    errors: List[str] = []


class PipelineResultResponse(BaseModel):
    """Response model for completed pipeline results."""
    status: str
    implementation_plan: Dict[str, Any] = {}
    files_modified: List[str] = []
    review_findings: List[Dict[str, Any]] = []
    test_files: List[str] = []
    pr_url: Optional[str] = None
    messages: List[Dict[str, Any]] = []
    errors: List[str] = []


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str
    agents_available: int


# ==================== Storage ====================

# In-memory storage for pipeline runs (use Redis/DB in production)
pipeline_runs: Dict[str, Dict[str, Any]] = {}


# ==================== Helper Functions ====================

def get_agent_by_type(agent_type: AgentType):
    """Get an agent instance by type."""
    agent_map = {
        AgentType.ORCHESTRATOR: OrchestratorAgent,
        AgentType.REPO_READER: RepoReaderAgent,
        AgentType.ANALYST: AnalystAgent,
        AgentType.CODER: CoderAgent,
        AgentType.REVIEWER: ReviewerAgent,
        AgentType.TESTER: TesterAgent,
        AgentType.PR_MANAGER: PRManagerAgent,
    }
    return agent_map.get(agent_type)()


def create_initial_state(issue: str, repo_path: str) -> AgentState:
    """Create an initial agent state."""
    return AgentState(
        issue=issue,
        repo_path=repo_path,
        status="pending"
    )


# ==================== API Endpoints ====================

@app.get("/", tags=["Info"])
async def root():
    """
    Root endpoint with API information and available endpoints.
    """
    return {
        "name": "Multi-Agent Development Pipeline API",
        "version": "2.0.0",
        "description": "AI-powered automated development workflow",
        "agents": [agent.value for agent in AgentType],
        "endpoints": {
            "GET /": "API information",
            "GET /health": "Health check",
            "GET /agents": "List all agents",
            "GET /agents/{agent_type}": "Get specific agent info",
            "POST /pipeline/run": "Start async pipeline run",
            "GET /pipeline/{run_id}": "Get pipeline status",
            "POST /pipeline/sync": "Run pipeline synchronously",
            "POST /agents/{agent_type}/execute": "Execute specific agent",
            "GET /workflow": "Get workflow visualization"
        }
    }


@app.get("/health", response_model=HealthResponse, tags=["Info"])
async def health_check():
    """
    Health check endpoint to verify API status.
    """
    return HealthResponse(
        status="healthy",
        version="2.0.0",
        agents_available=len(AgentType)
    )


# ==================== Agent Endpoints ====================

@app.get("/agents", response_model=List[AgentInfoResponse], tags=["Agents"])
async def list_agents():
    """
    List all available agents with their descriptions and responsibilities.
    """
    agents_info = [
        AgentInfoResponse(
            name="Orchestrator",
            description="Coordinates the development pipeline and delegates tasks to specialized agents",
            responsibilities=[
                "Parse issue/requirements",
                "Detect issue type (feature, bugfix, refactor)",
                "Estimate complexity",
                "Delegate tasks to specialized agents",
                "Monitor workflow progress"
            ]
        ),
        AgentInfoResponse(
            name="Analyst",
            description="Analyzes repository structure and creates implementation plans",
            responsibilities=[
                "Read repository structure",
                "Identify relevant files based on requirements",
                "Extract keywords from issue",
                "Draft implementation plan",
                "Estimate scope of changes"
            ]
        ),
        AgentInfoResponse(
            name="Coder",
            description="Creates branches, implements code changes, and commits",
            responsibilities=[
                "Create feature branch",
                "Read relevant source files",
                "Generate code changes",
                "Write changes to files",
                "Commit changes to git"
            ]
        ),
        AgentInfoResponse(
            name="Reviewer",
            description="Reviews code changes for quality, security, and best practices",
            responsibilities=[
                "Read git diff of changes",
                "Check code style",
                "Identify security issues",
                "Verify documentation",
                "Check error handling",
                "Validate naming conventions"
            ]
        ),
        AgentInfoResponse(
            name="Tester",
            description="Creates and runs tests for new code",
            responsibilities=[
                "Analyze code changes",
                "Generate test files",
                "Write unit tests for classes and functions",
                "Commit test files",
                "Run tests and report results"
            ]
        ),
        AgentInfoResponse(
            name="PRManager",
            description="Creates and manages Pull Requests via GitHub API",
            responsibilities=[
                "Push branch to remote",
                "Create Pull Request",
                "Add description and labels",
                "Monitor review status",
                "Auto-merge after approval"
            ]
        )
    ]
    return agents_info


@app.get("/agents/{agent_type}", response_model=AgentInfoResponse, tags=["Agents"])
async def get_agent_info(agent_type: AgentType):
    """
    Get detailed information about a specific agent.
    """
    agents = await list_agents()
    agent_name_map = {
        AgentType.ORCHESTRATOR: "Orchestrator",
        AgentType.ANALYST: "Analyst",
        AgentType.CODER: "Coder",
        AgentType.REVIEWER: "Reviewer",
        AgentType.TESTER: "Tester",
        AgentType.PR_MANAGER: "PRManager",
    }
    
    target_name = agent_name_map.get(agent_type)
    for agent in agents:
        if agent.name == target_name:
            return agent
    
    raise HTTPException(status_code=404, detail=f"Agent {agent_type} not found")


@app.post("/agents/{agent_type}/execute", tags=["Agents"])
async def execute_agent(agent_type: AgentType, request: AgentExecuteRequest):
    """
    Execute a specific agent independently.
    
    This allows you to run individual agents without going through the full pipeline.
    Useful for testing or when you only need specific functionality.
    """
    try:
        agent = get_agent_by_type(agent_type)
        repo_path = request.repo_path or os.getcwd()
        
        # Create initial state
        if request.state:
            state = AgentState(**request.state)
            state.issue = request.issue
            state.repo_path = repo_path
        else:
            state = create_initial_state(request.issue, repo_path)
        
        # Execute the agent
        result_state = await agent.execute(state)
        
        return {
            "agent": agent_type.value,
            "status": result_state.status,
            "current_agent": result_state.current_agent,
            "messages": result_state.messages,
            "implementation_plan": result_state.implementation_plan,
            "files_to_modify": result_state.files_to_modify,
            "code_changes": result_state.code_changes,
            "review_findings": result_state.review_findings,
            "test_files": result_state.test_files,
            "errors": result_state.errors
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Pipeline Endpoints ====================

@app.post("/pipeline/run", response_model=PipelineRunResponse, tags=["Pipeline"])
async def run_pipeline_async(request: IssueRequest, background_tasks: BackgroundTasks):
    """
    Start a new pipeline run asynchronously.
    
    The pipeline executes in the background. Use the returned run_id
    to check status via GET /pipeline/{run_id}.
    
    Pipeline stages:
    1. Orchestrator parses requirements
    2. Analyst creates implementation plan
    3. Coder implements changes
    4. Reviewer reviews code
    5. Tester creates tests
    6. PRManager creates Pull Request
    """
    run_id = str(uuid.uuid4())[:8]
    repo_path = request.repo_path or os.getcwd()
    
    # Initialize pipeline
    pipeline = AgentPipeline(repo_path=repo_path)
    
    # Store initial status
    pipeline_runs[run_id] = {
        "status": PipelineStatus.RUNNING.value,
        "current_agent": "Orchestrator",
        "messages": [],
        "pr_url": None,
        "errors": []
    }
    
    # Define background task
    async def run_pipeline_task():
        try:
            result = await pipeline.run(request.issue)
            pipeline_runs[run_id] = {
                "status": result.get("status", PipelineStatus.COMPLETED.value),
                "current_agent": result.get("current_agent", ""),
                "messages": result.get("messages", []),
                "pr_url": result.get("pr_url"),
                "errors": result.get("errors", [])
            }
        except Exception as e:
            pipeline_runs[run_id] = {
                "status": PipelineStatus.ERROR.value,
                "current_agent": "",
                "messages": [],
                "pr_url": None,
                "errors": [str(e)]
            }
    
    background_tasks.add_task(run_pipeline_task)
    
    return PipelineRunResponse(
        run_id=run_id,
        status=PipelineStatus.RUNNING.value,
        current_agent="Orchestrator",
        messages=[],
        pr_url=None,
        errors=[]
    )


@app.get("/pipeline/{run_id}", response_model=PipelineRunResponse, tags=["Pipeline"])
async def get_pipeline_status(run_id: str):
    """
    Get the status of a pipeline run by its ID.
    """
    if run_id not in pipeline_runs:
        raise HTTPException(status_code=404, detail=f"Pipeline run '{run_id}' not found")
    
    run_data = pipeline_runs[run_id]
    return PipelineRunResponse(run_id=run_id, **run_data)


@app.get("/pipeline", tags=["Pipeline"])
async def list_pipeline_runs(
    status: Optional[PipelineStatus] = Query(None, description="Filter by status"),
    limit: int = Query(10, ge=1, le=100, description="Maximum number of results")
):
    """
    List all pipeline runs, optionally filtered by status.
    """
    runs = []
    for run_id, run_data in list(pipeline_runs.items())[-limit:]:
        if status is None or run_data["status"] == status.value:
            runs.append({
                "run_id": run_id,
                **run_data
            })
    return {"runs": runs, "total": len(runs)}


@app.post("/pipeline/sync", response_model=PipelineResultResponse, tags=["Pipeline"])
async def run_pipeline_sync(request: IssueRequest):
    """
    Run the full pipeline synchronously and wait for results.
    
    This is useful for testing or when you need immediate results.
    Note: This may take a while for complex issues.
    """
    repo_path = request.repo_path or os.getcwd()
    pipeline = AgentPipeline(repo_path=repo_path)
    
    try:
        result = await pipeline.run(request.issue)
        return PipelineResultResponse(
            status=result.get("status", "completed"),
            implementation_plan=result.get("implementation_plan", {}),
            files_modified=list(result.get("code_changes", {}).keys()),
            review_findings=result.get("review_findings", []),
            test_files=list(result.get("test_files", {}).keys()),
            pr_url=result.get("pr_url"),
            messages=result.get("messages", []),
            errors=result.get("errors", [])
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/pipeline/{run_id}", tags=["Pipeline"])
async def delete_pipeline_run(run_id: str):
    """
    Delete a pipeline run record.
    """
    if run_id not in pipeline_runs:
        raise HTTPException(status_code=404, detail=f"Pipeline run '{run_id}' not found")
    
    del pipeline_runs[run_id]
    return {"message": f"Pipeline run '{run_id}' deleted successfully"}


# ==================== Workflow Endpoints ====================

@app.get("/workflow", tags=["Workflow"])
async def get_workflow():
    """
    Get the workflow visualization and stage descriptions.
    """
    pipeline = AgentPipeline()
    
    return {
        "visualization": pipeline.get_workflow_visualization() if hasattr(pipeline, 'get_workflow_visualization') else None,
        "stages": [
            {
                "stage": 1,
                "name": "Orchestration",
                "agent": "Orchestrator",
                "input": "Issue/Requirements",
                "output": "Parsed requirements with type and complexity",
                "description": "The orchestrator parses the incoming issue, detects its type (feature, bugfix, refactor), and estimates complexity."
            },
            {
                "stage": 2,
                "name": "Analysis",
                "agent": "Analyst",
                "input": "Parsed requirements",
                "output": "Implementation plan with files to modify",
                "description": "The analyst reads the repository structure, identifies relevant files, and creates a detailed implementation plan."
            },
            {
                "stage": 3,
                "name": "Implementation",
                "agent": "Coder",
                "input": "Implementation plan",
                "output": "Code changes committed to feature branch",
                "description": "The coder creates a feature branch, reads relevant files, generates code changes, and commits them."
            },
            {
                "stage": 4,
                "name": "Review",
                "agent": "Reviewer",
                "input": "Code changes (git diff)",
                "output": "Review findings and suggestions",
                "description": "The reviewer analyzes the git diff, checks code style, security, documentation, and error handling."
            },
            {
                "stage": 5,
                "name": "Testing",
                "agent": "Tester",
                "input": "New code changes",
                "output": "Test files committed",
                "description": "The tester analyzes the new code, generates appropriate test files, and commits them to the branch."
            },
            {
                "stage": 6,
                "name": "PR Creation",
                "agent": "PRManager",
                "input": "All committed changes",
                "output": "Pull Request URL",
                "description": "The PR manager pushes the branch to remote, creates a Pull Request, and optionally auto-merges after approval."
            }
        ],
        "flow": "Orchestrator → Analyst → Coder → Reviewer → Tester → PRManager"
    }


@app.get("/workflow/diagram", tags=["Workflow"])
async def get_workflow_diagram():
    """
    Get an ASCII diagram of the workflow.
    """
    diagram = """
    ┌─────────────────────────────────────────────────────────────────────────┐
    │                    Multi-Agent Development Pipeline                      │
    └─────────────────────────────────────────────────────────────────────────┘
    
    ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
    │              │     │              │     │              │
    │ Orchestrator │────▶│   Analyst    │────▶│    Coder     │
    │              │     │              │     │              │
    └──────────────┘     └──────────────┘     └──────────────┘
           │                                         │
           │ Parse Issue                             │ Create Branch
           │ Detect Type                             │ Write Code
           │ Estimate Complexity                     │ Commit Changes
           │                                         │
           │                                         ▼
           │             ┌──────────────┐     ┌──────────────┐
           │             │              │     │              │
           │             │  PRManager   │◀────│   Reviewer   │
           │             │              │     │              │
           │             └──────────────┘     └──────────────┘
           │                    │                    │
           │                    │ Push Branch        │ Check Style
           │                    │ Create PR          │ Check Security
           │                    │ Auto-merge         │ Review Code
           │                    │                    │
           │                    ▼                    │
           │             ┌──────────────┐            │
           │             │              │            │
           └────────────▶│    Tester    │◀───────────┘
                         │              │
                         └──────────────┘
                                │
                                │ Generate Tests
                                │ Run Tests
                                │ Commit Tests
                                ▼
                         ┌──────────────┐
                         │   Complete   │
                         └──────────────┘
    """
    return {"diagram": diagram}


# ==================== Logging Endpoints ====================

@app.get("/logs", tags=["Logs"])
async def get_logs(
    agent: Optional[str] = Query(None, description="Filter by agent name (Orchestrator, Analyst, Coder, Reviewer, Tester, PRManager)"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of log entries to return")
):
    """
    Retrieve logs from the agent pipeline.
    
    Logs include:
    - Agent start/end events
    - Actions performed by each agent
    - Errors and exceptions
    - Pipeline start/end events
    """
    logs = agent_logger.get_logs(agent_name=agent, limit=limit)
    return {
        "logs": logs,
        "count": len(logs),
        "filter": {"agent": agent, "limit": limit}
    }


@app.get("/logs/recent", tags=["Logs"])
async def get_recent_logs(minutes: int = Query(5, ge=1, le=60, description="Get logs from last N minutes")):
    """
    Get logs from the last N minutes.
    """
    from datetime import datetime, timedelta
    
    all_logs = agent_logger.get_logs(limit=1000)
    cutoff = datetime.now() - timedelta(minutes=minutes)
    
    recent_logs = []
    for log in all_logs:
        try:
            log_time = datetime.fromisoformat(log.get("timestamp", ""))
            if log_time >= cutoff:
                recent_logs.append(log)
        except (ValueError, TypeError):
            continue
    
    return {
        "logs": recent_logs,
        "count": len(recent_logs),
        "filter": {"minutes": minutes}
    }


@app.get("/logs/agent/{agent_name}", tags=["Logs"])
async def get_agent_logs(
    agent_name: str,
    limit: int = Query(50, ge=1, le=500)
):
    """
    Get logs for a specific agent.
    """
    # Map agent type to agent name
    agent_name_map = {
        "orchestrator": "Orchestrator",
        "analyst": "Analyst",
        "coder": "Coder",
        "reviewer": "Reviewer",
        "tester": "Tester",
        "pr_manager": "PRManager",
        "prmanager": "PRManager"
    }
    
    mapped_name = agent_name_map.get(agent_name.lower(), agent_name)
    logs = agent_logger.get_logs(agent_name=mapped_name, limit=limit)
    
    return {
        "agent": mapped_name,
        "logs": logs,
        "count": len(logs)
    }


@app.delete("/logs", tags=["Logs"])
async def clear_logs():
    """
    Clear all log files.
    """
    agent_logger.clear_logs()
    return {"message": "All logs cleared successfully"}


@app.get("/logs/summary", tags=["Logs"])
async def get_logs_summary():
    """
    Get a summary of logged events.
    """
    all_logs = agent_logger.get_logs(limit=10000)
    
    summary = {
        "total_entries": len(all_logs),
        "by_agent": {},
        "by_event": {},
        "errors": []
    }
    
    for log in all_logs:
        # Count by agent
        agent = log.get("agent", "unknown")
        summary["by_agent"][agent] = summary["by_agent"].get(agent, 0) + 1
        
        # Count by event type
        event = log.get("event", "unknown")
        summary["by_event"][event] = summary["by_event"].get(event, 0) + 1
        
        # Collect errors
        if event == "error":
            summary["errors"].append({
                "agent": agent,
                "error": log.get("error"),
                "timestamp": log.get("timestamp")
            })
    
    return summary


# ==================== Error Handlers ====================

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "message": exc.detail,
            "status_code": exc.status_code
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={
            "error": True,
            "message": str(exc),
            "status_code": 500
        }
    )


# ==================== Main Entry Point ====================

if __name__ == "__main__":
    import uvicorn
    
    # Get configuration from environment
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8000"))
    reload = os.getenv("API_RELOAD", "false").lower() == "true"
    
    print(f"""
    ╔═══════════════════════════════════════════════════════════╗
    ║     Multi-Agent Development Pipeline API                  ║
    ╠═══════════════════════════════════════════════════════════╣
    ║  Endpoints:                                               ║
    ║    - API Docs:    http://{host}:{port}/docs                    ║
    ║    - ReDoc:       http://{host}:{port}/redoc                   ║
    ║    - Health:      http://{host}:{port}/health                  ║
    ╚═══════════════════════════════════════════════════════════╝
    """)
    
    uvicorn.run("api:app", host=host, port=port, reload=reload)
