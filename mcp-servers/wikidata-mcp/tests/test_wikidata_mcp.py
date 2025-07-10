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

def test_search_entity():
    """Test the search_entity tool."""
    response = client.post("/tools/call", json={
        "name": "search_entity",
        "arguments": {
            "query": "Douglas Adams"
        }
    })
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "results" in data

def test_search_property():
    """Test the search_property tool."""
    response = client.post("/tools/call", json={
        "name": "search_property",
        "arguments": {
            "query": "director"
        }
    })
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "results" in data

def test_get_properties():
    """Test the get_properties tool."""
    response = client.post("/tools/call", json={
        "name": "get_properties",
        "arguments": {
            "entity_id": "Q42"
        }
    })
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "results" in data

def test_execute_sparql():
    """Test the execute_sparql tool."""
    response = client.post("/tools/call", json={
        "name": "execute_sparql",
        "arguments": {
            "sparql_query": "SELECT ?item ?itemLabel WHERE { ?item wdt:P31 wd:Q146. SERVICE wikibase:label { bd:serviceParam wikibase:language \"[AUTO_LANGUAGE],en\". } } LIMIT 1"
        }
    })
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "results" in data

def test_get_metadata():
    """Test the get_metadata tool."""
    response = client.post("/tools/call", json={
        "name": "get_metadata",
        "arguments": {
            "entity_id": "Q42"
        }
    })
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "results" in data
