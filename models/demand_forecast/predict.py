import os
import json
from datetime import datetime, timezone
import joblib


ARTIFACT_DIR = "models/demand_forecast/artifacts"


def _load_metadata() -> dict:
    meta_path = os.path.join(ARTIFACT_DIR, "metadata.json")
    if not os.path.exists(meta_path):
        raise FileNotFoundError(
            "metadata.json not found. Train model first:\n"
            "python models/demand_forecast/train.py"
        )
    with open(meta_path, "r") as f:
        return json.load(f)


def _load_model_for_asset(asset_id: str):
    """
    Loads the correct Prophet model using metadata.json.

    Supports:
    - group_col present: multiple models (one per building_id)
    - group_col absent: single global model
    """
    meta = _load_metadata()
    group_col = meta.get("group_col")

    if group_col:
        for m in meta.get("models", []):
            if str(m.get("group_value")) == str(asset_id):
                return joblib.load(m["model_path"]), meta

        # fallback: first model
        return joblib.load(meta["models"][0]["model_path"]), meta

    # global model case
    return joblib.load(meta["models"][0]["model_path"]), meta


def _demand_level(total_forecast: float, tank_pct: float = None) -> str:
    """
    Determine demand urgency based on forecast AND current tank level.
    
    If tank is critically low, upgrade demand level to reflect urgency.
    """
    # Start with forecast-based level
    if total_forecast >= 8000:
        base_level = "HIGH"
    elif total_forecast >= 4000:
        base_level = "MEDIUM"
    else:
        base_level = "LOW"
    
    # Upgrade if tank is critically low (overrides forecast)
    if tank_pct is not None:
        if tank_pct < 20:
            return "CRITICAL"  # Emergency level
        elif tank_pct < 30:
            # Force HIGH urgency if tank is low, even if demand forecast is low
            if base_level == "LOW":
                return "MEDIUM"
            else:
                return "HIGH"
    
    return base_level


def _recommendation_text(level: str, tank_pct: float = None) -> str:
    if level == "CRITICAL":
        return "EMERGENCY: Tank below 20%. Immediate tanker dispatch required. Switch to emergency protocols NOW."
    if level == "HIGH":
        if tank_pct is not None and tank_pct < 30:
            return "URGENT REFILL: Low tank level + high demand forecast. Dispatch tanker within 30 minutes to prevent service outage."
        return "Schedule tanker refill / increase pumping cycle within next 6–12 hours."
    if level == "MEDIUM":
        if tank_pct is not None and tank_pct < 30:
            return "Tank critically low. Refill recommended ASAP despite moderate demand forecast."
        return "Monitor demand; consider pump runtime adjustment during peak hours."
    return "Normal consumption pattern; no immediate action required."


def forecast_water_demand(asset_id: str, horizon_hours: int, tank_pct: float = None) -> dict:
    """
    Forecast water demand for next N hours.
    Optionally accepts tank_pct to adjust urgency based on current tank level.
    Output format is agent-friendly and consistent.
    """
    model, meta = _load_model_for_asset(asset_id)

    freq = meta.get("freq", "h")

    future = model.make_future_dataframe(periods=horizon_hours, freq=freq)
    fcst = model.predict(future)

    fcst_tail = fcst.tail(horizon_hours).copy()

    series = []
    total = 0.0

    for _, row in fcst_tail.iterrows():
        val = max(0.0, float(row["yhat"]))  # no negative consumption
        total += val

        series.append(
            {
                "timestamp": row["ds"].isoformat(),
                "value": round(val, 2),
                "lower": round(max(0.0, float(row.get("yhat_lower", val))), 2),
                "upper": round(max(0.0, float(row.get("yhat_upper", val))), 2),
            }
        )

    # Adjust demand level based on tank percentage if provided
    level = _demand_level(total, tank_pct=tank_pct)
    recommendation = _recommendation_text(level, tank_pct=tank_pct)

    forecast_start = series[0]["timestamp"] if series else None
    forecast_end = series[-1]["timestamp"] if series else None

    # Find peak hour and top 3 hours
    sorted_series = sorted(series, key=lambda x: x["value"], reverse=True)
    peak = sorted_series[0] if sorted_series else None
    top3 = sorted_series[:3] if len(sorted_series) >= 3 else sorted_series

    return {
        "status": "ok",
        "asset_id": str(asset_id),
        "horizon_hours": int(horizon_hours),
        "prediction_time": datetime.now(timezone.utc).isoformat(),
        "forecast_start": forecast_start,
        "forecast_end": forecast_end,
        "forecast_total": round(total, 2),
        "demand_level": level,
        "recommendation": recommendation,
        "peak_hour": peak,
        "top_3_hours": top3,
        "forecast_series": series,
        "model_name": "prophet_v1",
    }


def pretty_print_forecast(result: dict) -> None:
    print("=" * 70)
    print("WATER DEMAND FORECAST - PREDICTIONS")
    print("=" * 70)

    print(f"\n🏢 Building/Asset: {result['asset_id']}")
    print(f"📅 Prediction Time: {result['prediction_time']}")
    print(f"⏳ Horizon: {result['horizon_hours']} hours")
    print(f"🕒 Forecast Window: {result['forecast_start']} → {result['forecast_end']}")
    print(f"💧 Total Expected Demand: {result['forecast_total']} liters")
    print(f"🚦 Demand Level: {result['demand_level']}")

    peak = result.get("peak_hour")
    if peak:
        print("\n🔥 Peak Demand Hour:")
        print(
            f"   {peak['timestamp']} → {peak['value']} L "
            f"(range: {peak['lower']} - {peak['upper']})"
        )

    print("\n🏆 Top 3 Demand Hours:")
    for row in result.get("top_3_hours", []):
        print(f"   {row['timestamp']} → {row['value']} L")

    print("\n📈 Next Few Forecast Points:")
    for row in result.get("forecast_series", [])[:6]:
        print(
            f"   {row['timestamp']} → {row['value']} L "
            f"(range: {row['lower']} - {row['upper']})"
        )

    print("\n✅ Recommended Action:")
    print(f"   {result['recommendation']}")

    print("\n✅ FORECAST COMPLETE!")
    print("=" * 70)


# ---------------------------------------------------------------------
# ✅ BACKWARD + API COMPATIBILITY WRAPPER
# --------------------------------------------------------------------- 
def predict_demand(building_id: str, horizon_hours: int = 24, tank_pct: float = None) -> dict:
    """
    Wrapper so that FastAPI routes can call a consistent name:
        predict_demand(building_id="BLD_001", horizon_hours=24, tank_pct=26)

    Internally uses your working:
        forecast_water_demand(asset_id=..., horizon_hours=..., tank_pct=...)
    
    tank_pct: Optional. Current tank level percentage. If provided, adjusts demand urgency.
    """
    return forecast_water_demand(asset_id=building_id, horizon_hours=horizon_hours, tank_pct=tank_pct)
if __name__ == "__main__":
    # Change asset_id based on your trained groups (BLD_001 / BLD_002)
    out = forecast_water_demand(asset_id="BLD_001", horizon_hours=24)
    pretty_print_forecast(out)
    