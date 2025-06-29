import pytest
from fastapi.testclient import TestClient
from src.server import app
import os

client = TestClient(app)

@pytest.fixture
def agentql_credentials():
    """Mocked AgentQL Credentials for testing."""
    os.environ["AGENTQL_API_KEY"] = os.environ.get("AGENTQL_API_KEY")

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

@pytest.mark.asyncio
async def test_agentql_query(agentql_credentials):
    """Test the agentql_query tool."""
    query = """
    {
        posts[] {
            title
            author
        }
    }
    """
    response = client.post("/tools/call", json={
        "name": "agentql_query",
        "arguments": {
            "url": "https://dev.to",
            "query": query
        }
    })
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "result" in data
    assert "posts" in data["result"]
    assert len(data["result"]["posts"]) > 0
    assert "title" in data["result"]["posts"][0]
    assert "author" in data["result"]["posts"][0]
