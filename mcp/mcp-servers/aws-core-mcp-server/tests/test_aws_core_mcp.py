import pytest
from fastapi.testclient import TestClient
import sys
import os

# Add the project root to the PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.server import app
from moto import mock_aws
import boto3

client = TestClient(app)

@pytest.fixture
def aws_credentials():
    """Mocked AWS Credentials for moto."""
    import os
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"

@pytest.fixture
def s3_client(aws_credentials):
    with mock_aws():
        yield boto3.client("s3", region_name="us-east-1")

@pytest.fixture
def ec2_client(aws_credentials):
    with mock_aws():
        yield boto3.client("ec2", region_name="us-east-1")

@pytest.fixture
def iam_client(aws_credentials):
    with mock_aws():
        yield boto3.client("iam", region_name="us-east-1")


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

def test_s3_list_buckets(s3_client):
    """Test the s3_list_buckets tool."""
    s3_client.create_bucket(Bucket="test-bucket-1")
    s3_client.create_bucket(Bucket="test-bucket-2")

    response = client.post("/tools/call", json={
        "name": "s3_list_buckets",
        "arguments": {}
    })
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "buckets" in data
    assert "test-bucket-1" in data["buckets"]
    assert "test-bucket-2" in data["buckets"]

def test_ec2_list_instances(ec2_client):
    """Test the ec2_list_instances tool."""
    ec2_client.run_instances(ImageId="ami-12345678", MinCount=1, MaxCount=1)

    response = client.post("/tools/call", json={
        "name": "ec2_list_instances",
        "arguments": {}
    })
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "instances" in data
    assert len(data["instances"]) == 1

def test_iam_list_users(iam_client):
    """Test the iam_list_users tool."""
    iam_client.create_user(UserName="test-user-1")
    iam_client.create_user(UserName="test-user-2")

    response = client.post("/tools/call", json={
        "name": "iam_list_users",
        "arguments": {}
    })
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "users" in data
    assert "test-user-1" in data["users"]
    assert "test-user-2" in data["users"]
