from pydantic import BaseModel

class ScreenerRunRequest(BaseModel):
    """Request to run the screener."""

    screening_criteria: str


@app.post("/api/screener/run", response_model=dict)
async def run_screener(request: ScreenerRunRequest):
    """Run the screener with the given criteria."""
    results = screener.run(request.screening_criteria)
    return {"results": results}

# New endpoint for running the screener
class RunScreenerRequest(BaseModel):
    criteria: str


@app.post("/api/screener/run")
async def run_screener_endpoint(request: RunScreenerRequest):
    candidate_setups = await screener.run_screener(request.criteria)
    return candidate_setups