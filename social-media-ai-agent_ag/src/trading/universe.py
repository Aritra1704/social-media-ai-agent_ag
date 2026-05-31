class UniverseManager:
    def __init__(self, data_source: str = "nifty50"):
        self.data_source = data_source
        self.instruments = []

    def refresh_universe(self):
        # Hardcoded list of Nifty50-like symbols for demonstration purposes
        nifty50_symbols = [
            {"id": "RELIANCE", "name": "Reliance Industries"},
            {"id": "TCS", "name": "Tata Consultancy Services"},
            {"id": "HDFC_BANK", "name": "HDFC Bank"},
            {"id": "INFY", "name": "Infosys"},
            {"id": "ICICI_BANK", "name": "ICICI Bank"},
            {"id": "KOTAKBANK", "name": "Kotak Mahindra Bank"},
            {"id": "HUL", "name": "Hindustan Unilever"},
            {"id": "ITC", "name": "Indian Tobacco Company"},
            {"id": "L&T", "name": " Larsen & Toubro"},
            {"id": "BHARTIARTL", "name": "Bharti Enterprises"}
        ]
        self.instruments = nifty50_symbols
        return self.instruments

    def get_all_instruments(self):
        return self.instruments

    def get_instrument(self, instrument_id: str) -> dict:
        for instrument in self.instruments:
            if instrument['id'] == instrument_id:
                return instrument
        return None