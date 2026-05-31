from pydantic import BaseModel

class ScreenerRunRequest(BaseModel):
    """Request to run the screener."""

    screening_criteria: str


@app.post("/api/screener/run", response_model=dict)
async def run_screener(request: ScreenerRunRequest):
    """Run the screener with the given criteria."""
    results = screener.run(request.screening_criteria)
    return {"results": results}