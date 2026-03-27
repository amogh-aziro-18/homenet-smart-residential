from fastapi import APIRouter
from services.water_state import WATER_STATE

router = APIRouter()

@router.get("/water/status")
def get_water_status():
    if not WATER_STATE:
        return {"status": "empty"}
    return WATER_STATE
