from fastapi import APIRouter, Depends
from typing import Any, Dict, List
from services.asset_service import AssetService

router = APIRouter()


def get_asset_service() -> AssetService:
    if not hasattr(get_asset_service, "_instance"):
        get_asset_service._instance = AssetService()
    return get_asset_service._instance


@router.get("/water/tanks", response_model=None)
def list_water_tanks(
    asset_service: AssetService = Depends(get_asset_service),
) -> List[Dict[str, Any]]:
    return asset_service.list_tanks()
