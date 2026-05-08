"""Node: Classify errors into mapping errors vs code errors using LLM."""

from __future__ import annotations
import json

from langchain_core.messages import HumanMessage, SystemMessage

from config.constants import ERROR_TYPE_CODE, ERROR_TYPE_MAPPING
from graph.state import LoggerAgentState
from utils.llm import get_llm


CLASSIFICATION_PROMPT = """You are an expert error analyst for a Policy Connector Service (PCS) which is a skeleton/wrapper service that maps fields between Evervue and the IRIS platform via APIs.

PCS errors fall into exactly two categories:

1. **missing_or_incorrect_mapping** — The error is caused by a field that is missing, incorrectly mapped, has a wrong data type, or has an invalid value according to the field mappings between PCS and IRIS.
   Examples: null reference on a field that should be mapped, validation failure on a mapped field, "field X not found", type mismatch between source and target.

2. **code_error** — The error is a bug in the PCS codebase itself (logic error, unhandled exception, timeout, configuration issue, infrastructure issue) that is NOT related to field mapping.
   Examples: null pointer in business logic, timeout calling downstream API, serialization bug, missing dependency injection.

You will be given:
- Error logs from Azure App Insights (may contain MANY duplicate/similar errors)
- The field mapping Excel data (PCS payload fields <-> IRIS fields)

IMPORTANT: The logs may contain hundreds of errors. You MUST:
1. Intelligently CONSOLIDATE duplicate/similar errors into distinct patterns
2. Group errors that have the same root cause together
3. Report the occurrence count for each consolidated pattern
4. Produce one entry per DISTINCT error pattern (not per log line)

For each distinct consolidated error pattern, provide:
- "error_type": "missing_or_incorrect_mapping" or "code_error"
- "error_description": detailed description of what went wrong
- "field_name": the specific field involved (null if code_error)
- "suggested_next_step": actionable next step to resolve
- "severity": "high", "medium", or "low"
- "occurrence_count": how many times this error pattern appeared in the logs
- "raw_error_sample": a representative sample of the raw error

Return a JSON array of classified errors. Output ONLY valid JSON array."""


def error_classifier_node(state: LoggerAgentState) -> dict:
    """Use LLM to classify errors into mapping vs code errors."""
    raw_logs = state.get("raw_logs", "")
    log_entries = state.get("log_entries", [])
    field_mappings = state.get("field_mappings", [])

    if not raw_logs and not log_entries:
        return {
            "classified_errors": [],
            "stage": "error_classifier",
            "status": "no_errors_to_classify",
        }

    # Build context for LLM
    logs_text = raw_logs if raw_logs else json.dumps(log_entries[:50], indent=2)
    mappings_text = json.dumps(field_mappings[:100], indent=2) if field_mappings else "No field mappings available."

    llm = get_llm()
    response = llm.invoke([
        SystemMessage(content=CLASSIFICATION_PROMPT),
        HumanMessage(content=f"""## Error Logs (from Azure App Insights):
{logs_text[:12000]}

## Field Mappings (PCS <-> IRIS):
{mappings_text[:6000]}

Classify each distinct error pattern."""),
    ])

    try:
        classified = json.loads(response.content)
        if not isinstance(classified, list):
            classified = [classified]
    except json.JSONDecodeError:
        # Fallback: wrap the response as a single unclassified entry
        classified = [{
            "error_type": ERROR_TYPE_CODE,
            "error_description": response.content,
            "field_name": None,
            "suggested_next_step": "Manual review required",
            "severity": "medium",
            "raw_error_sample": "",
        }]

    return {
        "classified_errors": classified,
        "stage": "error_classifier",
        "status": "completed",
    }
