# Backend

Flask backend API for EverAssist.

## Quick start

1. Create and activate a virtual environment.
2. Install dependencies:

	```bash
	pip install -r requirements.txt
	```

3. (Optional) Copy environment file:

	```bash
	copy .env.example .env
	```

4. Run the API:

	```bash
	python app.py
	```

API base URL: `http://localhost:5000/api`

## Endpoints

- `GET /api` - API info
- `GET /api/health` - health check
