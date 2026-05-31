import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from src.trading.screener import AIScreener
from src.web.api import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as client:
        yield client


@pytest.fixture
def mock_universe_manager():
    return MagicMock()


@pytest.fixture
def mock_ollama_client():
    return MagicMock()


@pytest.fixture
def mock_gemini_model():
    return MagicMock()


def test_screener_endpoint(client, mock_universe_manager, mock_ollama_client, mock_gemini_model):
    with patch('src.trading.screener.AIScreener._ollama_interaction', return_value=['AAPL', 'GOOGL']):
        with patch('src.trading.screener.AIScreener._gemini_ranking', return_value={'AAPL': 0.9, 'GOOGL': 0.8}):
            response = client.post("/api/screener/run", json={"criteria": {"growth": ["high"]}})
            assert response.status_code == 200
            assert response.json() == {'AAPL': 0.9, 'GOOGL': 0.8}


def test_screener_endpoint_with_different_criteria(client, mock_universe_manager, mock_ollama_client, mock_gemini_model):
    with patch('src.trading.screener.AIScreener._ollama_interaction', return_value=['MSFT', 'AMZN']):
        with patch('src.trading.screener.AIScreener._gemini_ranking', return_value={'MSFT': 0.85, 'AMZN': 0.95}):
            response = client.post("/api/screener/run", json={"criteria": {"volatility": ["low"]}})
            assert response.status_code == 200
            assert response.json() == {'MSFT': 0.85, 'AMZN': 0.95}