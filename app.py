import os
from datetime import datetime, timezone

from flask import Flask, jsonify

app = Flask(__name__)

# Configuration is loaded from the environment so secrets are never hardcoded.
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "change-me-in-dotenv")
APP_ENV = os.environ.get("APP_ENV", "development")
APP_VERSION = os.environ.get("APP_VERSION", "1.0.0")
PORT = int(os.environ.get("PORT", "5000"))

# Capture process start time so /health can report uptime.
_START_TIME = datetime.now(timezone.utc)


@app.route("/")
def index():
    return jsonify(
        message="Hello from the Flask Health API",
        environment=APP_ENV,
        version=APP_VERSION,
    )


@app.route("/health")
def health():
    uptime_seconds = (datetime.now(timezone.utc) - _START_TIME).total_seconds()
    return (
        jsonify(
            status="healthy",
            version=APP_VERSION,
            uptime_seconds=round(uptime_seconds, 2),
            timestamp=datetime.now(timezone.utc).isoformat(),
        ),
        200,
    )


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=PORT)
