from src.trading.universe import UniverseManager
from src.trading.features import FeatureExtractor
import ollama

class AIScreener:
    def __init__(self):
        self.universe_manager = UniverseManager()
        self.feature_extractor = FeatureExtractor()
        self.ollama_client = ollama.Client()
        self.ollama_model = 'llama2'

    def run(self, screening_criteria):
        candidate_instruments = self._ollama_interaction(screening_criteria)
        ranked_instruments = self._gemini_ranking(candidate_instruments)
        return ranked_instruments

    def _ollama_interaction(self, criteria):
        instruments = self.universe_manager.get_all_instruments()
        instrument_ids = ','.join([instrument['id'] for instrument in instruments])
        prompt = f"Screen the following instruments: {instrument_ids} based on the following criteria: {criteria}"
        
        try:
            response = self.ollama_client.generate(prompt, model=self.ollama_model)
            candidate_ids = [id.strip() for id in response.split(',')]
        except Exception as e:
            print(f"Error calling Ollama: {e}")
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
        ranked_instruments = sorted(instruments, key=lambda x: x['score'], reverse=True)
        return ranked_instruments