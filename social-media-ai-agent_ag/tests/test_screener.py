import pytest
from httpx import AsyncClient
from unittest.mock import patch, MagicMock

from social_media_ai_agent_ag.src.trading.screener import AIScreener
from social_media_ai_agent_ag.src.web.api import app

@pytest.fixture(scope="module")
async def client():
    async with AsyncClient(app=app, base_url="http://test") as client:
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

@pytest.mark.asyncio
async def test_screener_endpoint(client, mock_universe_manager, mock_ollama_client, mock_gemini_model):
    with patch('social_media_ai_agent_ag.src.trading.screener.AIScreener._ollama_interaction', return_value=['AAPL', 'GOOGL']):
        with patch('social_media_ai_agent_ag.src.trading.screener.AIScreener._gemini_ranking', return_value={'AAPL': 0.9, 'GOOGL': 0.8}):
            response = await client.post("/api/screener/run", json={"criteria": "high_growth"})
            assert response.status_code == 200
            assert response.json() == {'AAPL': 0.9, 'GOOGL': 0.8}

@pytest.mark.asyncio
async def test_screener_endpoint_with_different_criteria(client, mock_universe_manager, mock_ollama_client, mock_gemini_model):
    with patch('social_media_ai_agent_ag.src.trading.screener.AIScreener._ollama_interaction', return_value=['MSFT', 'AMZN']):
        with patch('social_media_ai_agent_ag.src.trading.screener.AIScreener._gemini_ranking', return_value={'MSFT': 0.85, 'AMZN': 0.95}):
            response = await client.post("/api/screener/run", json={"criteria": "low_volatility"})
            assert response.status_code == 200
            assert response.json() == {'MSFT': 0.85, 'AMZN': 0.95}