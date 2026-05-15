import json
import pytest
import logging
import io
from app import app, logger

@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c

def test_structured_logging_json(client):
    # Create a buffer to capture logs
    log_buffer = io.StringIO()
    handler = logging.StreamHandler(log_buffer)
    # We use the same formatter as the app to verify it
    from app import JsonFormatter
    handler.setFormatter(JsonFormatter())
    
    logger.addHandler(handler)
    try:
        r = client.get("/health")
        assert r.status_code == 200
        
        # Get the logs from the buffer
        log_output = log_buffer.getvalue()
        assert log_output != ""
        
        # Parse the JSON log
        lines = log_output.strip().split("\n")
        found = False
        for line in lines:
            data = json.loads(line)
            if data.get("event") == "request_completed":
                assert "timestamp" in data
                assert "request_id" in data
                assert data["method"] == "GET"
                assert data["path"] == "/health"
                assert data["status"] == 200
                assert "duration_ms" in data
                assert "ip" in data
                found = True
                break
        assert found, "Request completed log not found in structured logs"
    finally:
        logger.removeHandler(handler)

def test_app_startup_log():
    # Verify we can log a simple string message too
    log_buffer = io.StringIO()
    handler = logging.StreamHandler(log_buffer)
    from app import JsonFormatter
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)
    try:
        logger.info("Test startup message")
        data = json.loads(log_buffer.getvalue().strip())
        assert data["event"] == "Test startup message"
        assert data["level"] == "INFO"
    finally:
        logger.removeHandler(handler)
