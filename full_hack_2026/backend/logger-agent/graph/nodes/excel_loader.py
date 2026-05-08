"""Node: Load field mappings from Excel file."""

from __future__ import annotations
import os
from typing import Any

import pandas as pd

from config.settings import get_settings
from graph.state import LoggerAgentState


def excel_loader_node(state: LoggerAgentState) -> dict:
    """Load PCS <-> IRIS field mappings from Excel."""
    path = state.get("excel_mapping_path") or get_settings().excel_mapping_path

    if not path or not os.path.exists(path):
        return {
            "field_mappings": [],
            "stage": "excel_loader",
            "status": "no_excel_found",
        }

    try:
        df = pd.read_excel(path)
        mappings = df.fillna("").to_dict(orient="records")
    except Exception:
        mappings = []

    return {
        "field_mappings": mappings,
        "stage": "excel_loader",
        "status": "completed",
    }
