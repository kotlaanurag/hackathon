"""Jira REST API wrapper."""

from __future__ import annotations
from typing import Any

import requests

from config.settings import get_settings


def fetch_stories(project_key: str, max_results: int = 50) -> list[dict[str, Any]]:
    """Fetch JIRA stories for a given project."""
    settings = get_settings()

    if not settings.jira_base_url or not settings.jira_api_token:
        return []

    url = f"{settings.jira_base_url}/rest/api/3/search"
    headers = {
        "Authorization": f"Basic {settings.jira_api_token}",
        "Content-Type": "application/json",
    }
    params = {
        "jql": f"project = {project_key} ORDER BY updated DESC",
        "maxResults": max_results,
        "fields": "summary,description,status,labels,customfield_10016",  # story points
    }

    try:
        resp = requests.get(url, headers=headers, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        return []

    stories = []
    for issue in data.get("issues", []):
        fields = issue.get("fields", {})
        stories.append({
            "key": issue.get("key"),
            "title": fields.get("summary", ""),
            "description": fields.get("description", ""),
            "status": fields.get("status", {}).get("name", ""),
            "labels": fields.get("labels", []),
        })

    return stories
