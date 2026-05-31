from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

class RunScreenerRequest(BaseModel):
    criteria: dict

@router.post("/api/screener/run")
async def run_screener_endpoint(request: RunScreenerRequest):
    try:
        result = screener.run_screener(request.criteria)
        return {"result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))