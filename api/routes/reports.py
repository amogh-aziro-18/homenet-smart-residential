from __future__ import annotations

from fastapi import APIRouter, Depends
from typing import Any, Dict

from api.dependencies import get_task_service, get_notification_service
from services.asset_service import AssetService
from services.task_service import TaskService
from services.notification_service import NotificationService
from agents.orchestrator import run_water_orchestration
from agents.forecast_agent import run_forecast_agent
from services.water_state import WATER_STATE

router = APIRouter()

def get_asset_service() -> AssetService:
    if not hasattr(get_asset_service, "_instance"):
        get_asset_service._instance = AssetService()
    return get_asset_service._instance


def print_supervisor_summary(result: dict) -> None:
    print("\n" + "=" * 70)
    print("🏠 HOMENET WATER SUPERVISOR RUN SUMMARY")
    print("=" * 70)

    print(f"🏢 Building: {result.get('building_id')}")

    tank = result.get("tank_status", {})
    print("\n🛢️ Tank:")
    print(
        f"   {tank.get('tank_id')} | "
        f"{tank.get('level_percentage')}% | "
        f"{tank.get('level_state')}"
    )

    forecast = result.get("forecast", {})
    print("\n📈 Forecast:")
    print(
        f"   Level: {forecast.get('demand_level')} | "
        f"Total: {forecast.get('forecast_total')} L"
    )

    tasks = result.get("created_tasks", [])
    print("\n📝 Tasks:")
    if not tasks:
        print("   None")
    else:
        for t in tasks:
            print(f"   {t['task_id']} | {t['priority']} | {t['title']}")

    print("=" * 70 + "\n")

@router.get("/water/status")
def get_water_status():
    if WATER_STATE is None:
        return {"status": "empty"}
    return WATER_STATE.__dict__

@router.get("/forecast/{building_id}", response_model=None)
def forecast(building_id: str, tank_pct: float = None) -> Dict[str, Any]:
    """
    Get water demand forecast.
    Optional tank_pct parameter: if provided, adjusts urgency based on current tank level.
    """
    agent_out = run_forecast_agent(building_id=building_id)
    raw = agent_out.get("ml_forecast_raw") or {}
    demand_level = str(raw.get("demand_level", agent_out.get("demand_level", "LOW"))).upper()
    recommendation = raw.get("recommendation") or agent_out.get("ml_recommendation") or agent_out.get("reasoning")
    if tank_pct is not None:
        if float(tank_pct) < 20:
            demand_level = "CRITICAL"
        elif float(tank_pct) < 30 and demand_level == "LOW":
            demand_level = "MEDIUM"
    return {
        "status": raw.get("status", "ok"),
        "asset_id": building_id,
        "horizon_hours": raw.get("horizon_hours", 24),
        "forecast_total": raw.get("forecast_total", agent_out.get("forecast_total", 0.0)),
        "demand_level": demand_level,
        "recommendation": recommendation,
        "forecast_start": raw.get("forecast_start"),
        "forecast_end": raw.get("forecast_end"),
        "peak_hour": raw.get("peak_hour"),
        "top_3_hours": raw.get("top_3_hours", []),
        "forecast_series": raw.get("forecast_series", []),
        "model_name": raw.get("model_name", "prophet_v1"),
    }


@router.post("/water/run", response_model=None)
def run_water_supervisor(
    building_id: str,
    mode: str = "latest",
    tank_mode: str | None = None,
    pump_mode: str | None = None,
    at_time: str | None = None,
    task_service: TaskService = Depends(get_task_service),
    asset_service: AssetService = Depends(get_asset_service),
    notification_service: NotificationService = Depends(get_notification_service),
) -> Dict[str, Any]:

    # Thin API route: prepare unified state and delegate orchestration
    system_state = asset_service.get_system_state(
        building_id=building_id,
        mode=mode,
        tank_mode=tank_mode,
        pump_mode=pump_mode,
        at_time=at_time,
    )
    result = run_water_orchestration(
        building_id=building_id,
        mode=mode,
        at_time=at_time,
        system_state=system_state,
        task_service=task_service,
        notification_service=notification_service,
    )

    print_supervisor_summary(result)
    return result
