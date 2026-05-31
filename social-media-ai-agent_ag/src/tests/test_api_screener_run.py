import pytest
from httpx import AsyncClient
from src.web.api import app, run_screener_endpoint

@pytest.fixture
async def client():
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

async def test_successful_request(client):
    criteria = {
        "age": {"min": 18, "max": 30},
        "location": "New York"
    }
    response = await client.post("/api/screener/run", json={"criteria": criteria})
    assert response.status_code == 200
    data = response.json()
    assert "candidate_setups" in data
    assert len(data["candidate_setups"]) > 0

async def test_invalid_request_missing_criteria(client):
    response = await client.post("/api/screener/run", json={})
    assert response.status_code == 422

async def test_screener_run_called_correctly(mocker, client):
    mock_run_screener = mocker.patch("src.web.api.screener.run_screener")
    criteria = {
        "age": {"min": 18, "max": 30},
        "location": "New York"
    }
    await client.post("/api/screener/run", json={"criteria": criteria})
    mock_run_screener.assert_called_once_with(criteria)