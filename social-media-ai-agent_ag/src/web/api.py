from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, validator

router = APIRouter()

class RunScreenerRequest(BaseModel):
    criteria: dict

    @validator('criteria')
    def check_criteria(cls, v):
        if not isinstance(v, dict) or not all(isinstance(k, str) and isinstance(v[k], list) for k in v):
            raise ValueError("Criteria must be a dictionary where keys are strings and values are lists")
        return v

@router.post("/api/screener/run")
async def run_screener_endpoint(request: RunScreenerRequest):
    try:
        result = screener.run_screener(request.criteria)
        return {"result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))