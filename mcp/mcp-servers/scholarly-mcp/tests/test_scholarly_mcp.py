import pytest
from fastapi.testclient import TestClient
from src.server import app

client = TestClient(app)

def test_health_check():
    """Test the health check endpoint."""
    response = client.post("/tools/call", json={
        "name": "health_check",
        "arguments": {}
    })
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "service" in data
    assert "timestamp" in data

def test_search_arxiv():
    """Test the search_arxiv tool."""
    response = client.post("/tools/call", json={
        "name": "search_arxiv",
        "arguments": {
            "keyword": "attention is all you need"
        }
    })
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "results" in data
