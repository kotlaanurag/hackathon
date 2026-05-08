# Requirements Agent

A LangGraph-based AI agent that analyzes error logs and generates structured Markdown specifications with JIRA story breakdowns.

## Architecture

```
┌─────────┐    ┌─────────────┐    ┌──────────────┐    ┌───────────────────┐    ┌──────────────┐
│  Intake │───▶│ Data Router │───▶│ Source Nodes 
 Context Assembler │───▶│ MD Generator │
└─────────┘    └─────────────┘    └──────────────┘    └───────────────────┘    └──────────────┘
                     │                    │
                     │              ┌─────┴──────┐
                     │              │ repo_parser │
                     │              │ log_analyzer│
                     │              │ jira_fetcher│
                     │              │ excel_mapper│
                     │              └────────────┘
                     ▼
               LLM decides which
               sources to consult
```

## Two Main Flows

### Flow 1: Payload Violation Errors
Errors caused by API requests that violate field mapping / validation rules defined in the Excel file.

**Examples:**
- `insuredName` exceeds 30 character max length
- `irisHost` value not in allowed enum `[Ireland, Syndicate, Asia]`
- `inceptionDate` in invalid date format
- `writtenLine` percentage value exceeds 100
- Missing required field `irisHost`
- `underWriterEmail` not matching email format

**Data sources consulted:** `["logs", "excel"]`

**Output:** MD specification describing the validation issue, affected fields, fix recommendations, and JIRA stories.

---

### Flow 2: Code/Feature Errors
Errors caused by missing logic, unhandled scenarios, or bugs in the codebase that don't currently have a fix.

**Examples:**
- IRIS returns "Reference doesn't exist" during renewal — no pre-validation
- UW email not registered in IRIS — no graceful fallback
- IRIS job timeout with no circuit-breaker handling
- `NullReferenceException` when both DUNS and IRIS code are empty
- Unsupported `multinationType` value — missing switch case

**Data sources consulted:** `["logs", "repo"]` (optionally `"jira"`)

**Output:** MD specification with root cause analysis, affected components, proposed solution, and JIRA stories.

---

## Project Structure

```
backend/requirements-agent/
├── app.py                          # FastAPI entrypoint
├── config/
│   ├── settings.py                 # Pydantic BaseSettings (env vars)
│   ├── constants.py                # Node names, edge conditions, LLM model IDs
│   ├── graph_config.yaml           # Configurable thresholds, retry policies
│   └── FieldMappings.xlsx          # API field mapping with validation rules
├── graph/
│   ├── state.py                    # TypedDict defining shared AgentState
│   ├── builder.py                  # StateGraph construction, compile graph
│   └── nodes/
│       ├── intake.py               # Parse initial request, normalize inputs
│       ├── data_router.py          # LLM-powered decision: which sources needed
│       ├── repo_parser.py          # Clone repo, AST parse, build dependency map
│       ├── log_analyzer.py         # Fetch & cluster errors, extract root causes
│       ├── jira_fetcher.py         # Pull story + acceptance criteria
│       ├── excel_mapper.py         # Parse field mapping & validation rules
│       ├── context_assembler.py    # Merge all gathered context into unified model
│       └── md_generator.py         # Render final structured MD + JIRA stories
├── parsers/
│   ├── python_parser.py            # AST-based code extraction
│   ├── dependency_graph.py         # Module dependency tree
│   └── schema_extractor.py         # ORM model extraction
├── prompts/
│   ├── templates/
│   │   ├── data_decision.j2        # Prompt for data_router LLM call
│   │   ├── error_analysis.j2       # Prompt for log clustering
│   │   └── final_output.md.j2      # Jinja2 template for final MD
│   ├── examples/
│   │   └── markdown files/         # Few-shot example MDs for style guidance
│   └── output_schema.py            # Pydantic model defining MD structure
├── utils/
│   ├── github_client.py            # GitHub clone/fetch
│   ├── azure_logs.py               # Azure Monitor query client
│   ├── jira_client.py              # Jira REST API wrapper
│   ├── excel_parser.py             # openpyxl-based parser
│   └── llm.py                      # Azure OpenAI Responses API wrapper
├── models/
│   ├── schemas.py                  # Request/response Pydantic models
│   └── codebase_models.py          # Parsed code structure models
├── tests/
│   └── mock_errors/                # Mock error log files for testing
├── requirements.txt
├── .env.example
└── README.md
```

## Quick Start

```bash
cd backend/requirements-agent
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy ..\..\..\.env .env
uvicorn app:app --reload --port 8000
```

## API

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| GET | `/docs` | Swagger UI |
| POST | `/api/v1/generate` | Run the agent |

### Example Request — Payload Violation

```json
{
  "raw_input": "Validation failed: 'insuredName' value 'International Consolidated Holdings Group Ltd' exceeds maximum length of 30 characters (actual: 46).",
  "request_type": "error_analysis",
  "excel_mapping_path": "config/FieldMappings.xlsx"
}
```

### Example Request — Code Error

```json
{
  "raw_input": "\"GetRenewPolicy\" completed with domain errors: \"IMEX Internal RunMap Failure; '' - The Reference (450388/03/2026) doesn't exist\"",
  "request_type": "error_analysis",
  "github_repo_url": "https://github.com/EvGr-Hackathon-2026/InfoSys_Hackathon_2026"
}
```

### Response Schema

```json
{
  "md_output": "# Markdown specification...",
  "jira_output": [
    {
      "title": "Story title",
      "description": "Detailed description",
      "acceptance_criteria": ["Given...", "When...", "Then..."],
      "story_points": 5,
      "labels": ["api", "validation"]
    }
  ],
  "sources_used": ["logs", "excel"]
}
```

## Configuration

### Environment Variables

| Variable | Description |
|----------|-------------|
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI Responses API endpoint |
| `AZURE_OPENAI_API_KEY` | API key |
| `AZURE_OPENAI_DEPLOYMENT` | Model deployment name |
| `AZURE_OPENAI_API_VERSION` | API version |
| `GITHUB_TOKEN` | GitHub PAT for private repos |
| `JIRA_BASE_URL` | Jira instance URL |
| `JIRA_API_TOKEN` | Jira API token |
| `JIRA_PROJECT_KEY` | Default Jira project key |

### LLM

Uses **Azure OpenAI Responses API** (`gpt-5.2-codex`) with a custom LangChain wrapper (`utils/llm.py`).

### Few-Shot Learning

Example markdown files in `prompts/examples/markdown files/` are automatically loaded and injected into the MD generator prompt to guide output style and structure.

## Test Data

Mock error logs are in `tests/mock_errors/`:

| File | Flow | Scenario |
|------|------|----------|
| `payload_violation_invalid_iris_host.log` | 1 | Invalid enum value |
| `payload_violation_invalid_date.log` | 1 | Bad date format |
| `payload_violation_percentage_scale.log` | 1 | Value > 100% |
| `payload_violation_missing_required_field.log` | 1 | Missing irisHost |
| `payload_violation_format_errors.log` | 1 | Email + length errors |
| `payload_violation_insured_name_too_long.log` | 1 | insuredName > 30 chars |
| `code_error_renew_reference_not_found.log` | 2 | IRIS reference missing |
| `code_error_uw_code_not_in_iris.log` | 2 | UW email not registered |
| `code_error_iris_timeout.log` | 2 | IRIS job timeout |
| `code_error_null_reference_assured_resolution.log` | 2 | NullRef in resolution |
| `code_error_unsupported_multination_type.log` | 2 | Unhandled switch case |
