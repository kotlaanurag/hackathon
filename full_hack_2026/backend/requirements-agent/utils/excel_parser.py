"""openpyxl-based Excel parser for field mappings."""

from __future__ import annotations
import os
from typing import Any

import pandas as pd


def parse_field_mapping(path: str) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    """Parse Excel field mapping file and return (mapping_rows, validation_rules).
    
    Returns:
        tuple: (field_mapping list, validation_rules list)
    """
    if not path or not os.path.exists(path):
        return [], []

    try:
        df = pd.read_excel(path)
    except Exception:
        return [], []

    # Convert to list of dicts
    mapping = df.fillna("").to_dict(orient="records")

    # Extract validation rules column if present
    rules = []
    if "Validation Rules" in df.columns:
        for _, row in df.iterrows():
            field = row.get("PCS Payload", "")
            rule = row.get("Validation Rules", "")
            if field and rule:
                rules.append({"field": str(field), "rule": str(rule)})

    return mapping, rules
