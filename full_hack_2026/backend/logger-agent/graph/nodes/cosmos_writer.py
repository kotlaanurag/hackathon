"""Node: Write classified errors to Cosmos DB — one document per error."""

from __future__ import annotations
import uuid
from datetime import datetime, timezone

from graph.state import LoggerAgentState
from utils.cosmos_client import write_to_cosmos


def cosmos_writer_node(state: LoggerAgentState) -> dict:
    """Write each classified error as a separate Cosmos DB document for downstream agents."""
    classified_errors = state.get("classified_errors", [])
    correlation_id = state.get("correlation_id", str(uuid.uuid4()))

    if not classified_errors:
        return {
            "cosmos_document_ids": [],
            "stage": "cosmos_writer",
            "status": "nothing_to_write",
        }

    doc_ids = []
    now = datetime.now(timezone.utc).isoformat()

    for idx, error in enumerate(classified_errors):
        document = {
            "id": str(uuid.uuid4()),
            "correlation_id": correlation_id,
            "sequence": idx + 1,
            "total_in_batch": len(classified_errors),
            "timestamp": now,
            "agent": "logger-agent",
            "stage": "error_analysis_complete",
            "status": "pending_error_handler",
            "error_type": error.get("error_type"),
            "error_description": error.get("error_description"),
            "field_name": error.get("field_name"),
            "suggested_next_step": error.get("suggested_next_step"),
            "severity": error.get("severity", "medium"),
            "occurrence_count": error.get("occurrence_count", 1),
            "raw_error_sample": error.get("raw_error_sample", ""),
        }
        doc_id = write_to_cosmos(document)
        if doc_id:
            doc_ids.append(doc_id)

    return {
        "cosmos_document_ids": doc_ids,
        "stage": "cosmos_writer",
        "status": "completed",
    }
