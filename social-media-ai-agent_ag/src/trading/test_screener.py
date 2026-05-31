import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
print("Added path:", sys.path[0])

from trading.screener import AIScreener
from fastapi.testclient import TestClient
from unittest.mock import patch
from src.trading.api import app

def test_run_screener_endpoint():
    client = TestClient(app)

    with patch('ollama.Client.generate') as mock_ollama, \
         patch('google.generativeai.GenerativeModel.generate_content') as mock_gemini:
        
        mock_ollama.return_value = {'response': 'ID1,ID2'}
        mock_gemini.return_value.text = '[\"ID1\", \"ID2\"]'

        screening_criteria = "stocks with high market capitalization and good growth prospects"
        response = client.post("/api/screener/run", json={"screening_criteria": screening_criteria})

        assert response.status_code == 200
        assert 'candidate_setups' in response.json()
        assert len(response.json()['candidate_setups']) == 2

if __name__ == "__main__":
    test_run_screener_endpoint()