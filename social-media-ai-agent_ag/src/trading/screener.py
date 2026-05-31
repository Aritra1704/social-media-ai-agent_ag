from social_media_ai_agent_ag.src.trading.universe import UniverseManager
from social_media_ai_agent_ag.src.trading.features import FeatureExtractor

class AIScreener:
    def __init__(self):
        self.universe_manager = UniverseManager()
        self.feature_extractor = FeatureExtractor()

    def run(self, screening_criteria):
        # Placeholder for Ollama interaction
        candidate_instruments = self._ollama_interaction(screening_criteria)
        
        # Placeholder for Gemini ranking
        ranked_instruments = self._gemini_ranking(candidate_instruments)
        
        return ranked_instruments

    def _ollama_interaction(self, criteria):
        # Placeholder method to simulate Ollama interaction
        print(f"Ollama is screening with criteria: {criteria}")
        candidate_instruments = self.universe_manager.get_instruments(criteria)
        return candidate_instruments

    def _gemini_ranking(self, instruments):
        # Placeholder method to simulate Gemini ranking
        print("Gemini is ranking the instruments...")
        ranked_instruments = sorted(instruments, key=lambda x: x['score'], reverse=True)
        return ranked_instruments