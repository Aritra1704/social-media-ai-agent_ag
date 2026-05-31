from fastapi import FastAPI, HTTPException
from social_media_ai_agent_ag.src.trading.universe import UniverseManager
from social_media_ai_agent_ag.src.trading.features import FeatureExtractor

app = FastAPI()

# Initialize instances of UniverseManager and FeatureExtractor
universe_manager = UniverseManager()
feature_extractor = FeatureExtractor()

@app.get("/api/universe")
async def get_universe():
    instruments = universe_manager.get_all_instruments()
    if not instruments:
        raise HTTPException(status_code=404, detail="No instruments found")
    return {"instruments": instruments}

@app.post("/api/universe/refresh")
async def refresh_universe():
    refreshed_instruments = universe_manager.refresh_universe()
    if not refreshed_instruments:
        raise HTTPException(status_code=500, detail="Failed to refresh universe")
    return {"refreshed_instruments": refreshed_instruments}

@app.post("/api/features/extract")
async def extract_features(symbol: str):
    feature_vector = feature_extractor.extract_features(symbol)
    if feature_vector is None:
        raise HTTPException(status_code=400, detail="Invalid symbol or no features extracted")
    return {"symbol": symbol, "feature_vector": feature_vector}