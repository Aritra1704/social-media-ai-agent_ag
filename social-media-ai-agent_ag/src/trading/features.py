class FeatureExtractor:
    def __init__(self, data_source: str = "nifty50"):
        self.data_source = data_source

    def extract_features(self, symbol: str) -> dict:
        return {
            'price_1d_change': 0.23,
            'volume_20d_avg': 15000000.0,
            'rsi_14': 78.5,
            'macd': -0.12
        }