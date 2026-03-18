import pytest
from fastapi.testclient import TestClient

def test_missing_token_returns_401(client):
    response = client.get("/api/sessions")
    assert response.status_code == 401

def test_invalid_token_returns_401(client):
    response = client.get("/api/sessions",
        headers={"Authorization": "Bearer invalid.token.here"})
    assert response.status_code == 401

def test_valid_token_passes(client, valid_jwt):
    response = client.get("/api/sessions",
        headers={"Authorization": f"Bearer {valid_jwt}"})
    assert response.status_code != 401

def test_expired_token_returns_401(client, expired_jwt):
    response = client.get("/api/sessions",
        headers={"Authorization": f"Bearer {expired_jwt}"})
    assert response.status_code == 401

def test_cohort_token_valid(client):
    response = client.post("/api/join",
        json={"cohort_token": "valid-test-token", "email": "rep@bsci.com", "name": "Test Rep"})
    assert response.status_code in (200, 201)

def test_cohort_token_invalid_returns_400(client):
    response = client.post("/api/join",
        json={"cohort_token": "nonexistent", "email": "rep@bsci.com", "name": "Test Rep"})
    assert response.status_code == 400
