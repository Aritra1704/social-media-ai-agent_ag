class UniverseManager:
    def __init__(self, data_source: str = "nifty50"):
        self.data_source = data_source
        self.instruments = []

    def refresh_universe(self):
        # Hardcoded list of Nifty50-like symbols for demonstration purposes
        nifty50_symbols = [
            "RELIANCE", "TCS", "HDFC_BANK", "INFY", "ICICI_BANK",
            "KOTAKBANK", "HUL", "ITC", "L&T", "BHARTIARTL"
        ]
        self.instruments = nifty50_symbols
        return self.instruments

    def get_all_instruments(self):
        return self.instruments