"""Node: Fetch error logs from Azure App Insights (or mock files for testing)."""

from __future__ import annotations
import os
import glob

from graph.state import LoggerAgentState
from utils.azure_logs import fetch_error_logs

MOCK_ERRORS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "tests", "mock_errors")


def _load_mock_logs() -> tuple[str, list[dict]]:
    """Load all .log files from tests/mock_errors as fallback."""
    mock_dir = os.path.normpath(MOCK_ERRORS_DIR)
    if not os.path.isdir(mock_dir):
        return "", []

    all_lines = []
    log_entries = []

    for filepath in sorted(glob.glob(os.path.join(mock_dir, "*.log"))):
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        all_lines.append(f"--- {os.path.basename(filepath)} ---")
        all_lines.append(content)

        # Parse each non-header line as a log entry
        for line in content.strip().splitlines():
            if line.startswith("timestamp") or not line.strip():
                continue
            parts = line.split("\t", 2)
            if len(parts) >= 3:
                log_entries.append({
                    "timestamp": parts[0].strip(),
                    "severity": parts[1].strip(),
                    "message": parts[2].strip(),
                    "source_file": os.path.basename(filepath),
                })

    return "\n".join(all_lines), log_entries


def log_fetcher_node(state: LoggerAgentState) -> dict:
    """Fetch current day error logs from Azure App Insights, fall back to mock files."""
    lookback_hours = state.get("lookback_hours", 24)

    raw_logs, log_entries = fetch_error_logs(lookback_hours)

    # Fall back to mock files if App Insights returned nothing
    if not raw_logs and not log_entries:
        raw_logs, log_entries = _load_mock_logs()

    if not raw_logs and not log_entries:
        return {
            "raw_logs": "",
            "log_entries": [],
            "total_raw_errors": 0,
            "stage": "log_fetcher",
            "status": "no_logs_found",
        }

    return {
        "raw_logs": raw_logs,
        "log_entries": log_entries,
        "total_raw_errors": len(log_entries),
        "stage": "log_fetcher",
        "status": "completed",
    }
