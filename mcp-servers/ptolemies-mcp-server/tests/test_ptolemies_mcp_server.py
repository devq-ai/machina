import pytest
from fastapi.testclient import TestClient
from src.server import app
import os

client = TestClient(app)

@pytest.fixture
def neo4j_credentials():
    """Mocked Neo4j Credentials for testing."""
    os.environ["NEO4J_URI"] = "bolt://localhost:7687"
    os.environ["NEO4J_USERNAME"] = "neo4j"
    os.environ["NEO4J_PASSWORD"] = "ptolemies"

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

def test_create_node(neo4j_credentials):
    """Test the create_node tool."""
    response = client.post("/tools/call", json={
        "name": "create_node",
        "arguments": {
            "label": "Person",
            "properties": {
                "name": "Alice"
            }
        }
    })
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "result" in data

def test_create_relationship(neo4j_credentials):
    """Test the create_relationship tool."""
    # First, create two nodes
    client.post("/tools/call", json={
        "name": "create_node",
        "arguments": {
            "label": "Person",
            "properties": {
                "name": "Alice"
            }
        }
    })
    client.post("/tools/call", json={
        "name": "create_node",
        "arguments": {
            "label": "Person",
            "properties": {
                "name": "Bob"
            }
        }
    })

    # Now, create a relationship between them
    response = client.post("/tools/call", json={
        "name": "create_relationship",
        "arguments": {
            "start_node_label": "Person",
            "start_node_properties": {
                "name": "Alice"
            },
            "end_node_label": "Person",
            "end_node_properties": {
                "name": "Bob"
            },
            "relationship_type": "KNOWS",
            "relationship_properties": {
                "since": 2021
            }
        }
    })
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "result" in data

def test_query_graph(neo4j_credentials):
    """Test the query_graph tool."""
    response = client.post("/tools/call", json={
        "name": "query_graph",
        "arguments": {
            "query": "MATCH (n) RETURN n"
        }
    })
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "result" in data
