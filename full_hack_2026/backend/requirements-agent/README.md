# Requirements Agent

A LangGraph-based agent that gathers multi-source context (GitHub repos, Azure error logs, JIRA stories, Excel field mappings) and generates structured Markdown specifications with JIRA story breakdowns.

## Architecture

```
┌─────────┐    ┌─────────────┐    ┌──────────────┐    ┌───────────────────┐    ┌──────────────┐
│  Intake │───▶│ Data Router │───▶│ Source Nodes │───▶│ Context Assembler │───▶│ MD Generator │
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

## Project Structure

```
requirements-agent/
├── app.py                          # FastAPI entrypoint
├── config/
│   ├── settings.py                 # Pydantic BaseSettings
│   ├── constants.py                # Node names, edge conditions, LLM model IDs
│   └── graph_config.yaml           # Configurable thresholds, retry policies
├── graph/
│   ├── state.py                    # TypedDict defining shared AgentState
│   ├── builder.py                  # StateGraph construction, compile graph
│   └── nodes/
│       ├── intake.py               # Parse initial request, normalize inputs
│       ├── data_router.py          # LLM-powered decision: which sources needed
│       ├── repo_parser.py          # Clone repo, AST parse, build dependency map
│       ├── log_analyzer.py         # Fetch & cluster Azure errors
│       ├── jira_fetcher.py         # Pull story + acceptance criteria
│       ├── excel_mapper.py         # Parse field mapping & validation rules
│       ├── context_assembler.py    # Merge all gathered context
│       └── md_generator.py         # Render final structured MD prompt
├── parsers/
│   ├── python_parser.py            # AST-based code extraction
│   ├── dependency_graph.py         # Module dependency tree
│   └── schema_extractor.py        # ORM model extraction
├── prompts/
│   ├── templates/
│   │   ├── data_decision.j2        # Prompt for data_router LLM call
│   │   ├── error_analysis.j2       # Prompt for log clustering
│   │   └── final_output.md.j2      # Jinja2 template for final MD
│   └── output_schema.py            # Pydantic model defining MD structure
├── utils/
│   ├── github_client.py            # GitHub clone/fetch
│   ├── azure_logs.py               # Azure Monitor query client
│   ├── jira_client.py              # Jira REST API wrapper
│   ├── excel_parser.py             # openpyxl-based parser
│   └── llm.py                      # LangChain LLM wrapper
├── models/
│   ├── schemas.py                  # Request/response models
│   └── codebase_models.py          # Parsed code structure models
├── requirements.txt
├── .env.example
└── README.md
```

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env
# Edit .env with your credentials

# 3. Run the service
uvicorn app:app --reload --port 8000
```

## API Usage

### Generate Specification
```bash
POST /api/v1/generate
Content-Type: application/json

{
  "raw_input": "Error: 400 Bad Request on POST /api/v1.0/policies - irisHost field validation failed",
  "request_type": "error_analysis",
  "github_repo_url": "https://github.com/org/policy-connector-service",
  "jira_project_key": "PCS",
  "excel_mapping_path": "config/FieldMappings.xlsx"
}
```

### Health Check
```bash
GET /health
```

## Configuration

Edit `config/graph_config.yaml` to tune:
- Retry policies and backoff
- Token limits and thresholds
- Source-specific settings (clone depth, log lookback, etc.)
