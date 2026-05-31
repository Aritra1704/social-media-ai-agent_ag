import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
print("Added path:", sys.path[0])

from trading.screener import AIScreener
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from src.web.api import app

def test_run_screener_success():
    client = TestClient(app)

    with patch('ollama.Client.generate') as mock_ollama, \
         patch('google.generativeai.GenerativeModel.generate_content') as mock_gemini, \
         patch('trading.universe.UniverseManager') as MockUniverseManager:
        
        mock_universe_manager = MockUniverseManager.return_value
        mock_universe_manager.get_all_instruments.return_value = [{'id': 'ID1', 'name': 'Instrument 1'}, {'id': 'ID2', 'name': 'Instrument 2'}]
        mock_universe_manager.get_instrument.side_effect = lambda instrument_id: {'id': instrument_id, 'name': f'Instrument {instrument_id}'}
        mock_universe_manager.refresh_universe.return_value = None

        mock_ollama.return_value = {'response': 'ID1,ID2'}
        mock_gemini.return_value.text = '[\"ID1\", \"ID2\"]'

        screening_criteria = "stocks with high market capitalization and good growth prospects"
        response = client.post("/api/screener/run", json={"screening_criteria": screening_criteria})

        assert response.status_code == 200
        assert 'results' in response.json()
        assert len(response.json()['results']) == 2

def test_run_screener_empty_criteria():
    client = TestClient(app)

    with patch('ollama.Client.generate') as mock_ollama, \
         patch('google.generativeai.GenerativeModel.generate_content') as mock_gemini, \
         patch('trading.universe.UniverseManager') as MockUniverseManager:
        
        mock_universe_manager = MockUniverseManager.return_value
        mock_universe_manager.get_all_instruments.return_value = [{'id': 'ID1', 'name': 'Instrument 1'}, {'id': 'ID2', 'name': 'Instrument 2'}]
        mock_universe_manager.get_instrument.side_effect = lambda instrument_id: {'id': instrument_id, 'name': f'Instrument {instrument_id}'}
        mock_universe_manager.refresh_universe.return_value = None

        mock_ollama.return_value = {'response': ''}
        mock_gemini.return_value.text = '[]'

        screening_criteria = ""
        response = client.post("/api/screener/run", json={"screening_criteria": screening_criteria})

        assert response.status_code == 200
        assert 'results' in response.json()
        assert len(response.json()['results']) == 0

def test_run_screener_no_ollama_candidates():
    client = TestClient(app)

    with patch('ollama.Client.generate') as mock_ollama, \
         patch('google.generativeai.GenerativeModel.generate_content') as mock_gemini, \
         patch('trading.universe.UniverseManager') as MockUniverseManager:
        
        mock_universe_manager = MockUniverseManager.return_value
        mock_universe_manager.get_all_instruments.return_value = [{'id': 'ID1', 'name': 'Instrument 1'}, {'id': 'ID2', 'name': 'Instrument 2'}]
        mock_universe_manager.get_instrument.side_effect = lambda instrument_id: {'id': instrument_id, 'name': f'Instrument {instrument_id}'}
        mock_universe_manager.refresh_universe.return_value = None

        mock_ollama.return_value = {'response': ''}
        mock_gemini.return_value.text = '[]'

        screening_criteria = "stocks with high market capitalization and good growth prospects"
        response = client.post("/api/screener/run", json={"screening_criteria": screening_criteria})

        assert response.status_code == 200
        assert 'results' in response.json()
        assert len(response.json()['results']) == 0

def test_run_screener_ollama_filters_gemini_reorders():
    client = TestClient(app)

    with patch('ollama.Client.generate') as mock_ollama, \
         patch('google.generativeai.GenerativeModel.generate_content') as mock_gemini, \
         patch('trading.universe.UniverseManager') as MockUniverseManager:
        
        mock_universe_manager = MockUniverseManager.return_value
        mock_universe_manager.get_all_instruments.return_value = [{'id': 'ID1', 'name': 'Instrument 1'}, {'id': 'ID2', 'name': 'Instrument 2'}]
        mock_universe_manager.get_instrument.side_effect = lambda instrument_id: {'id': instrument_id, 'name': f'Instrument {instrument_id}'}
        mock_universe_manager.refresh_universe.return_value = None

        mock_ollama.return_value = {'response': 'ID1,ID2'}
        mock_gemini.return_value.text = '[\"ID2\", \"ID1\"]'

        screening_criteria = "stocks with high market capitalization and good growth prospects"
        response = client.post("/api/screener/run", json={"screening_criteria": screening_criteria})

        assert response.status_code == 200
        assert 'results' in response.json()
        assert len(response.json()['results']) == 2

def test_run_screener_ollama_error():
    client = TestClient(app)

    with patch('ollama.Client.generate') as mock_ollama, \
         patch('google.generativeai.GenerativeModel.generate_content') as mock_gemini, \
         patch('trading.universe.UniverseManager') as MockUniverseManager:
        
        mock_universe_manager = MockUniverseManager.return_value
        mock_universe_manager.get_all_instruments.return_value = [{'id': 'ID1', 'name': 'Instrument 1'}, {'id': 'ID2', 'name': 'Instrument 2'}]
        mock_universe_manager.get_instrument.side_effect = lambda instrument_id: {'id': instrument_id, 'name': f'Instrument {instrument_id}'}
        mock_universe_manager.refresh_universe.return_value = None

        mock_ollama.side_effect = Exception("Ollama error")
        mock_gemini.return_value.text = '["ID1", "ID2"]'

        screening_criteria = "stocks with high market capitalization and good growth prospects"
        response = client.post("/api/screener/run", json={"screening_criteria": screening_criteria})

        assert response.status_code == 500
        assert 'error' in response.json()

def test_run_screener_gemini_error():
    client = TestClient(app)

    with patch('ollama.Client.generate') as mock_ollama, \
         patch('google.generativeai.GenerativeModel.generate_content') as mock_gemini, \
         patch('trading.universe.UniverseManager') as MockUniverseManager:
        
        mock_universe_manager = MockUniverseManager.return_value
        mock_universe_manager.get_all_instruments.return_value = [{'id': 'ID1', 'name': 'Instrument 1'}, {'id': 'ID2', 'name': 'Instrument 2'}]
        mock_universe_manager.get_instrument.side_effect = lambda instrument_id: {'id': instrument_id, 'name': f'Instrument {instrument_id}'}
        mock_universe_manager.refresh_universe.return_value = None

        mock_ollama.return_value = {'response': 'ID1,ID2'}
        mock_gemini.side_effect = Exception("Gemini error")

        screening_criteria = "stocks with high market capitalization and good growth prospects"
        response = client.post("/api/screener/run", json={"screening_criteria": screening_criteria})

        assert response.status_code == 500
        assert 'error' in response.json()

if __name__ == "__main__":
    test_run_screener_success()
    test_run_screener_empty_criteria()
    test_run_screener_no_ollama_candidates()
    test_run_screener_ollama_filters_gemini_reorders()
    test_run_screener_ollama_error()
    test_run_screener_gemini_error()