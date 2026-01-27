from __future__ import annotations

from fastapi import APIRouter, Depends
from typing import Any, Dict

from api.dependencies import get_task_service, get_notification_service
from services.asset_service import AssetService
from services.task_service import TaskService
from services.notification_service import NotificationService
from models.demand_forecast.predict import predict_demand

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


@router.get("/forecast/{building_id}", response_model=None)
def forecast(building_id: str) -> Dict[str, Any]:
    return predict_demand(building_id=building_id, horizon_hours=24)


@router.post("/water/run", response_model=None)
def run_water_supervisor(
    building_id: str,
    mode: str = "latest",
    at_time: str | None = None,
    task_service: TaskService = Depends(get_task_service),
    asset_service: AssetService = Depends(get_asset_service),
    notification_service: NotificationService = Depends(get_notification_service),
) -> Dict[str, Any]:

    forecast_result = predict_demand(building_id=building_id, horizon_hours=24)

    tank_status = asset_service.get_tank_status_by_building(
        building_id=building_id,
        mode=mode,
        at_time=at_time,
    )

    created_tasks = []

    level_state = tank_status.get("level_state", "NORMAL")
    tank_pct = float(tank_status.get("level_percentage", 0.0))
    tank_id = tank_status.get("tank_id")

    if level_state == "CRITICAL":
        created_tasks.append(
            task_service.create_task(
                title="Emergency tanker refill",
                description=f"Tank CRITICAL ({tank_pct}%)",
                asset_type="water",
                asset_id=tank_id,
                building_id=building_id,
                priority="CRITICAL",
                sla_hours=2,
            )
        )

    elif level_state == "LOW":
        created_tasks.append(
            task_service.create_task(
                title="Schedule tanker refill",
                description=f"Tank LOW ({tank_pct}%)",
                asset_type="water",
                asset_id=tank_id,
                building_id=building_id,
                priority="HIGH",
                sla_hours=6,
            )
        )

    # 🔔 Create notification ONLY if a task was created
    if created_tasks:
        notification_service.create_notification(
            type="ALERT",
            title="Water tank level low",
            message=f"Tank {tank_id} is LOW at {tank_pct}%. Refill scheduled.",
            severity="HIGH",
            building_id=building_id,
            related_task_id=created_tasks[0]["task_id"],
        )

    result = {
        "status": "ok",
        "building_id": building_id,
        "mode": mode,
        "at_time": at_time,
        "tank_status": tank_status,
        "forecast": forecast_result,
        "created_tasks": created_tasks,
        "message": "Supervisor run complete",
    }

    print_supervisor_summary(result)
    return result
