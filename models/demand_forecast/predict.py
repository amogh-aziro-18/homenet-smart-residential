def forecast_water_demand(asset_id: str, horizon_hours: int) -> dict:
    """
    Return forecasted water demand for the given horizon.
    """
    return {
        "asset_id": asset_id,
        "horizon_hours": horizon_hours,
        "forecast": [],
        "confidence": 0.0
    }
