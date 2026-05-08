# Logger Agent

Polls Azure App Insights for PCS (Policy Connector Service) errors, classifies them using an LLM, and writes results to Cosmos DB for downstream processing.

## Error Classification

Errors are bucketed into two categories:

1. **missing_or_incorrect_mapping** — Field mapping issues between PCS and IRIS (missing field, wrong type, invalid value)
2. **code_error** — Bugs in the PCS codebase (logic errors, unhandled exceptions, timeouts)

## Architecture

```
App Insights → [Log Fetcher] → [Excel Loader] → [Error Classifier (LLM)] → [Cosmos Writer] → Cosmos DB
```

Each step maintains state/stage/status in the graph for observability.

## API

- `POST /api/v1/analyze` — Trigger error analysis
- `GET /health` — Health check

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env  # Fill in Azure credentials
uvicorn app:app --port 8001
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI endpoint |
| `AZURE_OPENAI_API_KEY` | Azure OpenAI key |
| `AZURE_OPENAI_DEPLOYMENT` | Model deployment name |
| `AZURE_LOG_ANALYTICS_WORKSPACE_ID` | App Insights workspace |
| `AZURE_TENANT_ID` | Azure AD tenant |
| `AZURE_CLIENT_ID` | Service principal client ID |
| `AZURE_CLIENT_SECRET` | Service principal secret |
| `COSMOS_ENDPOINT` | Cosmos DB endpoint |
| `COSMOS_KEY` | Cosmos DB key |
| `EXCEL_MAPPING_PATH` | Path to field mappings Excel |
