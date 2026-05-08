# Stub UI API

A small FastAPI app that serves dummy endpoints for the EverAssist frontend
while the real backend is being built.

## Run

```bash
cd backend/stub-ui
pip install -r requirements.txt
uvicorn main:app --reload --port 8001
```

## Endpoints

- `GET  /api/health` — service health
- `POST /api/requirements/generate-md` — returns a Markdown summary built from intake form data
- `POST /api/requirements/submit` — accepts a requirement and returns a confirmation

The frontend reads the base URL from `VITE_STUB_API_URL` and falls back to
`http://localhost:8001`. If the API is unreachable the UI generates the
Markdown locally so the flow stays demo-able.
