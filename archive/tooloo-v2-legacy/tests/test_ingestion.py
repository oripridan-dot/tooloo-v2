import pytest
from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)

def test_ingest_support_request_success():
    """Test successful ingestion of a support request."""
    sample_request = {
        "request_id": "req-12345",
        "instrument": {
            "instrument_id": "inst-abc",
            "name": "Fender Stratocaster",
            "type": "Guitar",
            "price": 1200.50
        },
        "issue_description": "Buzzing sound from low E string.",
        "customer_id": "cust-67890"
    }
    response = client.post("/ingest/support_request/", json=sample_request)
    assert response.status_code == 200
    assert response.json() == {"message": "Support request received and queued for processing.", "request_id": "req-12345"}

def test_ingest_support_request_missing_field():
    """Test ingestion with a missing required field."""
    sample_request = {
        "request_id": "req-12346",
        "instrument": {
            "instrument_id": "inst-abd",
            "name": "Gibson Les Paul",
            "type": "Guitar",
            "price": 1500.00
        },
        # Missing "issue_description"
        "customer_id": "cust-67891"
    }
    response = client.post("/ingest/support_request/", json=sample_request)
    assert response.status_code == 422 # Unprocessable Entity due to Pydantic validation

def test_health_check():
    """Test the health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}
