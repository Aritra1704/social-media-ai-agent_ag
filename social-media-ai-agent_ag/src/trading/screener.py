from .universe import UniverseManager
from .features import FeatureExtractor
import ollama
import google.generativeai as genai
import json

class AIScreener:
    def __init__(self):
        self.universe_manager = UniverseManager()
        self.feature_extractor = FeatureExtractor()
        self.ollama_client = ollama.Client()
        self.ollama_model = 'llama2'
        self.gemini_client = genai.GenerativeModel('gemini-pro')
        genai.configure(api_key="YOUR_GEMINI_API_KEY")
        self.universe_manager.refresh_universe()

    def run(self, screening_criteria):
        candidate_instruments = self._ollama_interaction(screening_criteria)
        ranked_instruments = self._gemini_ranking(candidate_instruments)
        return ranked_instruments

    def _ollama_interaction(self, criteria):
        instruments = self.universe_manager.get_all_instruments()
        instrument_ids = ','.join([instrument['id'] for instrument in instruments])
        prompt = f"Screen the following instruments: {instrument_ids} based on the following criteria: {criteria}. Please return a comma-separated list of instrument IDs only, with no additional text."
        
        try:
            ollama_response = self.ollama_client.generate(prompt, model=self.ollama_model)
            print(f"Raw Ollama response: {ollama_response}")
            llm_text_response = ollama_response['response'].strip()
            candidate_ids = [id.strip() for id in llm_text_response.split(',') if id.strip()]
        except Exception as e:
            print(f"Error calling Ollama or parsing response: {e}")
            candidate_ids = []

        candidate_instruments = []
        for instrument_id in candidate_ids:
            instrument = self.universe_manager.get_instrument(instrument_id)
            if instrument:
                candidate_instruments.append({
                    'id': instrument['id'],
                    'name': instrument['name'],
                    'score': 0.9  # Placeholder score
                })

        return candidate_instruments

    def _gemini_ranking(self, instruments):
        print("Gemini is ranking the instruments...")
        instrument_list_str = ", ".join([f"ID: {inst['id']}, Name: {inst['name']}, Score: {inst['score']}" for inst in instruments])
        prompt = f"Rank these instruments based on their potential as trading setups: {instrument_list_str}. Return a JSON array of instrument IDs only, e.g., [\"ID1\", \"ID2\", \"ID3\"]"

        try:
            gemini_response = self.gemini_client.generate_content(prompt)
            print(f"Raw Gemini response: {gemini_response.text}")
            ranked_ids = json.loads(gemini_response.text)
            
            ranked_instruments = []
            for instrument_id in ranked_ids:
                instrument = next((inst for inst in instruments if inst['id'] == instrument_id), None)
                if instrument:
                    ranked_instruments.append(instrument)
        except json.JSONDecodeError as e:
            print(f"Error parsing Gemini response JSON: {e}")
            ranked_instruments = [] # Return empty list on parsing error
        except Exception as e:
            print(f"Error calling Gemini API: {e}")
            ranked_instruments = []

        return ranked_instruments