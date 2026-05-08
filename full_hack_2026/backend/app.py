import os
from datetime import datetime, timezone

from flask import Flask, jsonify
from flask_cors import CORS


def create_app() -> Flask:
    app = Flask(__name__)

    cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
    CORS(app, resources={r"/api/*": {"origins": [origin.strip() for origin in cors_origins.split(",") if origin.strip()]}})

    @app.get("/api/health")
    def health_check():
        return jsonify(
            {
                "status": "ok",
                "service": "everassist-backend",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

    @app.get("/api")
    def api_index():
        return jsonify(
            {
                "message": "EverAssist Flask API is running",
                "routes": ["GET /api", "GET /api/health"],
            }
        )

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=os.getenv("FLASK_DEBUG", "false").lower() == "true")
