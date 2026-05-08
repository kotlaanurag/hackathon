"""FastAPI entrypoint — triggers graph execution."""

from fastapi import FastAPI, HTTPException

from config.settings import get_settings
from graph.builder import prompt_generator_graph
from models.schemas import GeneratePromptRequest, GeneratePromptResponse, HealthResponse

app = FastAPI(
    title="Requirements Agent",
    description="LangGraph-based agent that gathers multi-source context and generates structured MD specifications",
    version="2.0.0",
)


@app.post("/api/v1/generate", response_model=GeneratePromptResponse)
async def generate_prompt(request: GeneratePromptRequest):
    """Generate a structured Markdown specification from gathered context."""
    try:
        initial_state = {
            "request_type": request.request_type,
            "raw_input": request.raw_input,
            "github_repo_url": request.github_repo_url,
            "jira_project_key": request.jira_project_key,
            "excel_mapping_path": request.excel_mapping_path or get_settings().excel_mapping_path,
        }
        result = await prompt_generator_graph.ainvoke(initial_state)
        return GeneratePromptResponse(
            md_output=result.get("md_output", ""),
            jira_output=result.get("jira_output", []),
            sources_used=result.get("sources_needed", []),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(status="healthy", service="requirements-agent", version="2.0.0")
