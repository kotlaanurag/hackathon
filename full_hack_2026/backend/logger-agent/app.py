"""FastAPI entrypoint for the Logger Agent service."""

import uuid

from fastapi import FastAPI, HTTPException

from config.settings import get_settings
from graph.builder import logger_agent_graph
from models.schemas import AnalyzeRequest, AnalyzeResponse, ClassifiedError, HealthResponse

app = FastAPI(
    title="Logger Agent",
    description="Polls Azure App Insights, classifies PCS errors into mapping vs code errors, writes to Cosmos DB",
    version="1.0.0",
)


@app.post("/api/v1/analyze", response_model=AnalyzeResponse)
async def analyze_errors(request: AnalyzeRequest):
    """Analyze current day errors from App Insights, consolidate, classify, and write to Cosmos."""
    try:
        correlation_id = str(uuid.uuid4())

        initial_state = {
            "correlation_id": correlation_id,
            "lookback_hours": request.lookback_hours,
            "excel_mapping_path": request.excel_mapping_path or get_settings().excel_mapping_path,
        }
        result = await logger_agent_graph.ainvoke(initial_state)

        classified = [
            ClassifiedError(**e) for e in result.get("classified_errors", [])
        ]

        return AnalyzeResponse(
            correlation_id=correlation_id,
            status=result.get("status", "completed"),
            total_raw_errors=result.get("total_raw_errors", 0),
            total_distinct_patterns=len(classified),
            classified_errors=classified,
            cosmos_document_ids=result.get("cosmos_document_ids", []),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(status="healthy", service="logger-agent", version="1.0.0")
