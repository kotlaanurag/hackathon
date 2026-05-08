"""Constants for the logger agent."""

# ─── Node Names ──────────────────────────────────────────────────────────────
NODE_LOG_FETCHER = "log_fetcher"
NODE_EXCEL_LOADER = "excel_loader"
NODE_ERROR_CLASSIFIER = "error_classifier"
NODE_COSMOS_WRITER = "cosmos_writer"

# ─── Error Types ─────────────────────────────────────────────────────────────
ERROR_TYPE_MAPPING = "missing_or_incorrect_mapping"
ERROR_TYPE_CODE = "code_error"

# ─── LLM ─────────────────────────────────────────────────────────────────────
DEFAULT_TEMPERATURE = 0.1
