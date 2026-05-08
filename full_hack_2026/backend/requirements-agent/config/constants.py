"""Constants: node names, edge conditions, LLM model IDs."""

# ─── Node Names ──────────────────────────────────────────────────────────────
NODE_INTAKE = "intake"
NODE_DATA_ROUTER = "data_router"
NODE_REPO_PARSER = "repo_parser"
NODE_JIRA_FETCHER = "jira_fetcher"
NODE_EXCEL_MAPPER = "excel_mapper"
NODE_CONTEXT_ASSEMBLER = "context_assembler"
NODE_MD_GENERATOR = "md_generator"

# ─── Edge Conditions ─────────────────────────────────────────────────────────
ROUTE_NEEDS_REPO = "needs_repo"
ROUTE_NEEDS_LOGS = "needs_logs"
ROUTE_NEEDS_JIRA = "needs_jira"
ROUTE_NEEDS_EXCEL = "needs_excel"
ROUTE_ASSEMBLE = "assemble"

# ─── LLM Model IDs ──────────────────────────────────────────────────────────
LLM_GPT4O = "gpt-4o"
LLM_GPT4O_MINI = "gpt-4o-mini"

# ─── Defaults ────────────────────────────────────────────────────────────────
DEFAULT_TEMPERATURE = 0.2
MAX_RETRIES = 3
