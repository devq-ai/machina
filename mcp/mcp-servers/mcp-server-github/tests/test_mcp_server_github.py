import pytest
from fastapi.testclient import TestClient
from src.server import app
import os
from unittest.mock import patch

client = TestClient(app)

@pytest.fixture
def github_credentials():
    """Mocked GitHub Credentials for testing."""
    os.environ["GITHUB_TOKEN"] = os.environ.get("GITHUB_PAT")

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

@patch("github.AuthenticatedUser.AuthenticatedUser.create_repo")
def test_create_repository(mock_create_repo, github_credentials):
    """Test the create_repository tool."""
    mock_create_repo.return_value.full_name = "test-owner/test-repo"
    response = client.post("/tools/call", json={
        "name": "create_repository",
        "arguments": {
            "name": "test-repo"
        }
    })
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "repo" in data
    assert data["repo"] == "test-owner/test-repo"

def test_list_issues(github_credentials):
    """Test the list_issues tool."""
    response = client.post("/tools/call", json={
        "name": "list_issues",
        "arguments": {
            "owner": "PyGithub",
            "repo": "PyGithub"
        }
    })
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "issues" in data
