import app as flask_app


def _client():
    flask_app.app.config["TESTING"] = True
    return flask_app.app.test_client()


def test_index_returns_ok():
    resp = _client().get("/")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["message"] == "Hello from the Flask Health API"
    assert "version" in data


def test_health_returns_healthy():
    resp = _client().get("/health")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "healthy"
    assert "timestamp" in data
    assert data["uptime_seconds"] >= 0
