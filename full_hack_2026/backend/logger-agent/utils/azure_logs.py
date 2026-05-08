"""Azure App Insights REST API client for fetching error logs."""

from __future__ import annotations
from typing import Any

import requests

from config.settings import get_settings

APP_INSIGHTS_API_BASE = "https://api.applicationinsights.io/v1/apps"


def fetch_error_logs(lookback_hours: int = 24) -> tuple[str, list[dict[str, Any]]]:
    """Fetch error logs from Azure App Insights REST API.

    Returns:
        tuple: (raw_logs_text, list_of_parsed_log_entries)
    """
    settings = get_settings()

    if not settings.azure_appinsights_app_id or not settings.azure_appinsights_api_key:
        return "", []

    query = f"""
    exceptions
    | where timestamp > ago({lookback_hours}h)
    | project timestamp, problemId, outerMessage, innermostMessage, operation_Name, cloud_RoleName, type, method, assembly
    | order by timestamp desc
    | take 500
    """

    url = f"{APP_INSIGHTS_API_BASE}/{settings.azure_appinsights_app_id}/query"
    headers = {
        "x-api-key": settings.azure_appinsights_api_key,
        "Content-Type": "application/json",
    }

    try:
        resp = requests.post(url, headers=headers, json={"query": query}, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        log_entries = []
        raw_lines = []

        for table in data.get("tables", []):
            columns = [col["name"] for col in table.get("columns", [])]
            for row in table.get("rows", []):
                entry = dict(zip(columns, row))
                log_entries.append(entry)
                raw_lines.append(
                    f"[{entry.get('timestamp')}] {entry.get('operation_Name', '')} | "
                    f"{entry.get('outerMessage', '')} | {entry.get('innermostMessage', '')}"
                )

        return "\n".join(raw_lines), log_entries

    except Exception as e:
        return f"Error fetching logs: {str(e)}", []
