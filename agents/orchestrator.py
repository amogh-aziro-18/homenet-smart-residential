"""
Main Orchestrator - Site-wide monitoring using LangGraph workflow
"""
import sys
import os
from datetime import datetime
from typing import Any, Optional
from services.water_state import WATER_STATE

parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

from agents.langgraph_workflow import run_langgraph_workflow
from typing import List, Dict
from agents.forecast_agent import run_forecast_agent
from services.technician_service import get_available_pump_technicians

CONFIG = {
    "tank_low": 30,
    "tank_critical": 20,
    "vibration_high": 10,
    "temperature_high": 70,
    "pressure_low": 30,
}

# Site configuration
SITES = {
    "SITE_001": {
        "name": "Chennai Residential Complex",
        "pumps": [
            "PUMP_BLD_001_01",
            "PUMP_BLD_001_02",
            "PUMP_BLD_002_01",
            "PUMP_BLD_002_02"
        ]
    }
}


def _get_langgraph_analysis(pump_id: str, tank_pct: float) -> Dict[str, Any]:
    """Safely run LangGraph and return normalized analysis payload."""
    try:
        result = run_langgraph_workflow(pump_id=pump_id, tank_pct=tank_pct)

        risk_score = result.get("risk_score", 0.0)
        risk_level = result.get("risk_level", "UNKNOWN")
        reasoning = result.get("reasoning", "Tank analysis performed")

        return {
            "status": "real",
            "supervisor_analysis": reasoning,
            "maintenance_risk_score": float(risk_score) if risk_score else 0.0,
            "maintenance_risk_level": risk_level,
            "maintenance_current_metrics": result.get("current_metrics", {}),
            "maintenance_failure_signals": result.get("failure_signals", []),
            "routing_assignments": result.get("assignments", []),
            "messages": [
                msg.content if hasattr(msg, "content") else str(msg)
                for msg in result.get("messages", [])
            ],
        }
    except Exception as e:
        print(f"⚠️  LangGraph workflow failed: {e}")
        # Keep failure deterministic and data-driven. Downstream maintenance
        # inference will be derived from real telemetry in _build_maintenance_output.
        return {
            "status": "error",
            "supervisor_analysis": "",
            "maintenance_risk_score": 0.0,
            "maintenance_risk_level": "UNKNOWN",
            "maintenance_current_metrics": {},
            "maintenance_failure_signals": [],
            "routing_assignments": [],
            "error": str(e),
        }


def _build_maintenance_output(
    pump_status: Dict[str, Any],
    langgraph_result: Dict[str, Any],
) -> Dict[str, Any]:
    """Create structured maintenance output with real telemetry values."""
    telemetry = pump_status.get("telemetry", {}) if isinstance(pump_status, dict) else {}
    telemetry_signals = pump_status.get("signals", {}) if isinstance(pump_status, dict) else {}

    normalized_signals = {
        "vibration": float(telemetry.get("vibration_mm_s", 0.0)),
        "temperature": float(telemetry.get("temperature_celsius", 0.0)),
        "pressure": float(telemetry.get("pressure_psi", 0.0)),
        "current": float(telemetry.get("current_amps", 0.0)),
        "flow": float(telemetry.get("flow_rate_lpm", 0.0)),
        "high_vibration": bool(telemetry_signals.get("high_vibration", False)),
        "high_temperature": bool(telemetry_signals.get("high_temperature", False)),
        "low_pressure": bool(telemetry_signals.get("low_pressure", False)),
        "low_flow": bool(telemetry_signals.get("low_flow", False)),
    }

    # Deterministic telemetry risk fallback so core decisions never depend on LLM availability.
    signal_score = 0
    if normalized_signals["high_vibration"]:
        signal_score += 2
    if normalized_signals["high_temperature"]:
        signal_score += 2
    if normalized_signals["low_pressure"]:
        signal_score += 1
    if normalized_signals["low_flow"]:
        signal_score += 1

    deterministic_risk = min(1.0, signal_score / 6.0)
    if signal_score >= 5:
        deterministic_level = "CRITICAL"
    elif signal_score >= 3:
        deterministic_level = "HIGH"
    elif signal_score >= 1:
        deterministic_level = "MEDIUM"
    else:
        deterministic_level = "LOW"

    langgraph_risk = float(langgraph_result.get("maintenance_risk_score", 0.0))
    langgraph_level = str(langgraph_result.get("maintenance_risk_level", "UNKNOWN")).upper()

    if langgraph_level in {"LOW", "MEDIUM", "HIGH", "CRITICAL"} and langgraph_risk > 0.0:
        risk_score = max(langgraph_risk, deterministic_risk)
        # Preserve severity if deterministic inference indicates higher urgency.
        level_order = {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}
        risk_level = (
            deterministic_level
            if level_order[deterministic_level] > level_order.get(langgraph_level, 0)
            else langgraph_level
        )
    else:
        risk_score = deterministic_risk
        risk_level = deterministic_level

    reasoning = langgraph_result.get("supervisor_analysis")
    if not reasoning:
        reasoning = (
            "Telemetry-driven assessment: "
            f"vibration={normalized_signals['vibration']:.2f} mm/s, "
            f"temperature={normalized_signals['temperature']:.1f} C, "
            f"pressure={normalized_signals['pressure']:.1f} psi, "
            f"flow={normalized_signals['flow']:.1f} LPM."
        )

    return {
        "risk_score": risk_score,
        "risk_level": risk_level,
        "signals": normalized_signals,
        "reasoning": reasoning,
    }


def _supervisor_agent_plan(system_state: Dict[str, Any], mode: str) -> Dict[str, Any]:
    """
    Supervisor decides which domain agents to trigger.
    """
    tank = system_state.get("tank_status", {})
    pump = system_state.get("pump_status", {})
    tank_pct = float(tank.get("level_percentage", 0.0))
    pump_signals = pump.get("signals", {}) if isinstance(pump, dict) else {}
    abnormal_pump = any(
        [
            bool(pump_signals.get("high_vibration")),
            bool(pump_signals.get("high_temperature")),
            bool(pump_signals.get("low_pressure")),
            bool(pump_signals.get("low_flow")),
        ]
    )

    return {
        # Forecast stays enabled for predictive behavior and UI continuity.
        "run_forecast_agent": True,
        # Maintenance runs only from data-driven abnormal telemetry.
        "run_maintenance_agent": abnormal_pump,
        "abnormal_pump_detected": abnormal_pump,
        "tank_low_or_worse": tank_pct < CONFIG["tank_low"],
    }


def _pick_technician_name(langgraph_result: Dict[str, Any]) -> str:
    assignments = langgraph_result.get("routing_assignments", []) or []
    if assignments and isinstance(assignments[0], dict):
        return assignments[0].get("technician_name") or "Technician A"
    # Deterministic fallback assignment from technician data source.
    candidates = get_available_pump_technicians()
    if candidates:
        return str(candidates[0].get("name", "Technician A"))
    return "Technician A"


def _run_forecast_via_agent(building_id: str, tank_pct: float) -> Dict[str, Any]:
    """
    Run forecast through Forecast Agent (agent -> model), then normalize output
    to /water/run response schema expected by frontend.
    """
    try:
        agent_out = run_forecast_agent(building_id=building_id)
        raw = agent_out.get("ml_forecast_raw") or {}
        forecast_total = float(raw.get("forecast_total", agent_out.get("forecast_total", 0.0)) or 0.0)
        demand_level = str(raw.get("demand_level", agent_out.get("demand_level", "LOW")) or "LOW").upper()
        # Preserve existing predictive urgency behavior tied to current tank level.
        if tank_pct < CONFIG["tank_critical"]:
            demand_level = "CRITICAL"
        elif tank_pct < CONFIG["tank_low"] and demand_level == "LOW":
            demand_level = "MEDIUM"
        recommendation = (
            agent_out.get("ml_recommendation")
            or agent_out.get("reasoning")
            or "Forecast agent completed."
        )
        if tank_pct < CONFIG["tank_critical"]:
            recommendation = "Tank critically low. Refill recommended ASAP despite demand forecast."
        elif tank_pct < CONFIG["tank_low"] and "refill" not in str(recommendation).lower():
            recommendation = "Tank level is low. Turn ON the motor and schedule refill soon."
        return {
            "status": str(raw.get("status", "ok")),
            "asset_id": building_id,
            "horizon_hours": int(raw.get("horizon_hours", 24)),
            "forecast_total": forecast_total,
            "demand_level": demand_level,
            "recommendation": recommendation,
            "forecast_start": raw.get("forecast_start"),
            "forecast_end": raw.get("forecast_end"),
            "peak_hour": raw.get("peak_hour"),
            "top_3_hours": raw.get("top_3_hours", []),
            "forecast_series": raw.get("forecast_series", []),
            "model_name": raw.get("model_name", "prophet_v1"),
            "agent_reasoning": agent_out.get("reasoning"),
        }
    except Exception as e:
        print(f"⚠️ Forecast agent execution failed: {e}")
        return {
            "status": "error",
            "asset_id": building_id,
            "horizon_hours": 24,
            "forecast_total": 0.0,
            "demand_level": "LOW",
            "recommendation": "Forecast temporarily unavailable. Continue close monitoring.",
            "confidence_level": "Low",
            "peak_hour": None,
            "top_3_hours": [],
            "forecast_series": [],
            "model_name": "unavailable",
            "error": str(e),
        }


def supervisor_decision(
    *,
    system_state: Dict[str, Any],
    forecast: Dict[str, Any],
    maintenance: Dict[str, Any],
    langgraph_result: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Central decision policy:
    detect -> predict -> decide (alerts + task intents + operator summary)
    """
    tank = system_state.get("tank_status", {})
    pump = system_state.get("pump_status", {})
    telemetry = pump.get("telemetry", {}) if isinstance(pump, dict) else {}
    signals = maintenance.get("signals", {}) if isinstance(maintenance, dict) else {}

    tank_pct = float(tank.get("level_percentage", 0.0))
    risk_level = str(maintenance.get("risk_level", "LOW")).upper()
    demand_level = str(forecast.get("demand_level", "LOW")).upper()
    technician_name = _pick_technician_name(langgraph_result)

    alerts: List[Dict[str, Any]] = []
    task_intents: List[Dict[str, Any]] = []
    notification_intents: List[Dict[str, Any]] = []
    technician_assignment: Dict[str, Any] | None = None

    # 1) LOW / CRITICAL WATER
    tank_failed = tank_pct < CONFIG["tank_low"]
    if tank_failed:
        tank_alert = {
            "type": "CRITICAL" if tank_pct <= CONFIG["tank_critical"] else "WARNING",
            "asset": "TANK",
            "message": (
                f"Tank level dropped to {tank_pct:.1f}%. "
                "Please turn ON the motor to stabilize supply."
            ),
            "details": {
                "level_percentage": tank_pct,
                "scenario": "tank_low_level",
            },
            "action": "Turn on motor",
        }
        alerts.append(tank_alert)
        notification_intents.append(
            {
                "type": "ALERT",
                "asset": "TANK",
                "category": "WATER_LEVEL",
                "alert_type": tank_alert["type"],
                "message": tank_alert["message"],
                "details": tank_alert["details"],
                "action": tank_alert["action"],
            }
        )
        task_intents.append(
            {
                "title": "Emergency tanker refill" if tank_pct <= CONFIG["tank_critical"] else "Schedule tanker refill",
                "description": f"Tank low at {tank_pct:.1f}%. Refill required.",
                "asset_type": "water",
                "asset_id": tank.get("tank_id"),
                "priority": "CRITICAL" if tank_pct <= CONFIG["tank_critical"] else "HIGH",
                "sla_hours": 2 if tank_pct <= CONFIG["tank_critical"] else 6,
            }
        )

    # 2) PROACTIVE REFILL
    if demand_level in {"HIGH", "CRITICAL"} and tank_pct < 60:
        proactive_alert = {
            "type": "WARNING",
            "asset": "TANK",
            "message": "Water level is expected to drop to critical levels. Refill has been scheduled proactively.",
            "details": {"forecast_demand_level": demand_level, "level_percentage": tank_pct},
            "action": "Task created / Proactive refill scheduled",
        }
        alerts.append(proactive_alert)
        notification_intents.append(
            {
                "type": "ALERT",
                "asset": "TANK",
                "category": "WATER_LEVEL",
                "alert_type": proactive_alert["type"],
                "message": proactive_alert["message"],
                "details": proactive_alert["details"],
                "action": proactive_alert["action"],
            }
        )
        task_intents.append(
            {
                "title": "Proactive tanker refill",
                "description": f"Forecast={demand_level} with tank at {tank_pct:.1f}%.",
                "asset_type": "water",
                "asset_id": tank.get("tank_id"),
                "priority": "HIGH",
                "sla_hours": 6,
            }
        )

    # 3) PUMP FAILURE
    high_vibration = bool(signals.get("high_vibration", False))
    high_temperature = bool(signals.get("high_temperature", False))
    low_pressure = bool(signals.get("low_pressure", False))
    low_flow = bool(signals.get("low_flow", False))
    pump_failed = high_vibration or high_temperature or risk_level in {"HIGH", "CRITICAL"}
    if pump_failed:
        technician_assignment = {
            "technician_name": technician_name,
            "task_type": "Inspect Pump",
            "asset_id": pump.get("pump_id"),
            "status": "assigned",
        }
        pump_alert = {
            "type": "CRITICAL" if risk_level == "CRITICAL" else "WARNING",
            "asset": "PUMP",
            "message": (
                f"Pump failure risk detected. Technician {technician_name} has been assigned.\n"
                f"Vibration: {float(telemetry.get('vibration_mm_s', 0.0)):.2f} mm/s, "
                f"Temperature: {float(telemetry.get('temperature_celsius', 0.0)):.1f} degC, "
                f"Pressure: {float(telemetry.get('pressure_psi', 0.0)):.1f} psi. "
                "Please store water for the next few hours."
            ),
            "details": {
                "vibration": float(telemetry.get("vibration_mm_s", 0.0)),
                "temperature": float(telemetry.get("temperature_celsius", 0.0)),
                "pressure": float(telemetry.get("pressure_psi", 0.0)),
                "current": float(telemetry.get("current_amps", 0.0)),
                "flow": float(telemetry.get("flow_rate_lpm", 0.0)),
                "technician_name": technician_name,
                "scenario": "pump_failure_risk",
            },
            "action": f"Technician assigned ({technician_name})",
        }
        alerts.append(pump_alert)
        notification_intents.append(
            {
                "type": "ALERT",
                "asset": "PUMP",
                "category": "PUMP_FAILURE",
                "alert_type": pump_alert["type"],
                "message": pump_alert["message"],
                "details": pump_alert["details"],
                "action": pump_alert["action"],
            }
        )
        task_intents.append(
            {
                "title": "Inspect Pump",
                "description": (
                    f"Risk={risk_level}. Vib={float(telemetry.get('vibration_mm_s', 0.0)):.2f}, "
                    f"Temp={float(telemetry.get('temperature_celsius', 0.0)):.1f}, "
                    f"Pressure={float(telemetry.get('pressure_psi', 0.0)):.1f}"
                ),
                "asset_type": "pump",
                "asset_id": pump.get("pump_id"),
                "priority": "CRITICAL" if risk_level == "CRITICAL" else "HIGH",
                "sla_hours": 2 if risk_level == "CRITICAL" else 4,
            }
        )

    # 4) PUMP INEFFICIENCY
    operating = str(pump.get("operating_state", "")).lower()
    if operating == "running" and low_flow and not (high_vibration or high_temperature):
        ineff_alert = {
            "type": "WARNING",
            "asset": "PUMP",
            "message": "Pump is operational but not delivering expected flow. Inspection has been scheduled.",
            "details": {
                "flow": float(telemetry.get("flow_rate_lpm", 0.0)),
                "pressure": float(telemetry.get("pressure_psi", 0.0)),
            },
            "action": "Task created / Pump inspection",
        }
        alerts.append(ineff_alert)
        notification_intents.append(
            {
                "type": "ALERT",
                "asset": "PUMP",
                "category": "PUMP_FAILURE",
                "alert_type": ineff_alert["type"],
                "message": ineff_alert["message"],
                "details": ineff_alert["details"],
                "action": ineff_alert["action"],
            }
        )

    # 5) COMBINED WORST SCENARIO: tank low + pump failure risk
    if tank_failed and pump_failed:
        system_alert = {
            "type": "CRITICAL",
            "asset": "SYSTEM",
            "message": (
                "Combined risk: tank is low and pump is under failure-risk inspection. "
                "Please turn ON motor backup and store water while pump repair is in progress."
            ),
            "details": {
                "tank_level_percentage": tank_pct,
                "pump_risk_level": risk_level,
                "scenario": "combined_tank_and_pump_failure",
            },
            "action": "Motor backup + maintenance workflow activated",
        }
        alerts.append(system_alert)
        notification_intents.append(
            {
                "type": "ALERT",
                "asset": "SYSTEM",
                "category": "SYSTEM",
                "alert_type": system_alert["type"],
                "message": system_alert["message"],
                "details": system_alert["details"],
                "action": system_alert["action"],
            }
        )

    if tank_pct < CONFIG["tank_low"]:
        ai_summary = "⚠️ Water level is critically low. Immediate tanker refill recommended to avoid outage."
        ai_reasoning = "Tank has dropped below 30% capacity. Pump failures and service outages are imminent at this critical threshold."
        ai_priority = "CRITICAL"
        ai_action = "emergency_refill"
    elif risk_level in {"HIGH", "CRITICAL"}:
        ai_summary = "⚠️ Pump health risk elevated. Maintenance inspection has been prioritized."
        ai_reasoning = "Telemetry signals indicate elevated pump stress and possible failure conditions."
        ai_priority = "HIGH"
        ai_action = "inspect_pump"
    elif tank_pct < 70:
        ai_summary = "⚠️ Water level is moderate. Monitor consumption closely over next 24 hours."
        ai_reasoning = "Moderate consumption trend detected. Refill should be scheduled within next 6-12 hours to prevent crisis."
        ai_priority = "HIGH"
        ai_action = "scheduled_refill"
    else:
        ai_summary = "✅ Water level is healthy. No immediate action required."
        ai_reasoning = "Reservoir is in good operational condition. Normal consumption patterns observed."
        ai_priority = "LOW"
        ai_action = "monitor"

    return {
        "alerts": alerts,
        "task_intents": task_intents,
        "notification_intents": notification_intents,
        "technician_assignment": technician_assignment,
        "ai_summary": ai_summary,
        "ai_reasoning": ai_reasoning,
        "ai_priority": ai_priority,
        "ai_action": ai_action,
    }


def supervisor_run(
    *,
    system_state: Dict[str, Any],
    building_id: str,
    mode: str,
) -> Dict[str, Any]:
    """
    Supervisor execution (domain logic + agent triggers + model/tool calls).
    Returns ONLY data (no side-effects like tasks/notifications).
    """
    tank_status = system_state.get("tank_status", {})
    pump_status = system_state.get("pump_status", {})

    assets = system_state.get("assets", {})
    if isinstance(assets, dict):
        water_assets = assets.get("water", {})
        if isinstance(water_assets, dict):
            tank_status = water_assets.get("tank", tank_status)
            pump_status = water_assets.get("pump", pump_status)

    tank_pct = float(tank_status.get("level_percentage", 0.0))

    agent_plan = _supervisor_agent_plan(
        {"tank_status": tank_status, "pump_status": pump_status},
        mode,
    )

    if agent_plan["run_forecast_agent"]:
        forecast_result = _run_forecast_via_agent(building_id=building_id, tank_pct=tank_pct)
    else:
        forecast_result = {
            "status": "skipped",
            "asset_id": building_id,
            "horizon_hours": 24,
            "forecast_total": 0.0,
            "demand_level": "LOW",
            "recommendation": "Forecast agent not triggered by supervisor.",
        }

    pump_id = pump_status.get("pump_id") or f"PUMP_{building_id}_01"
    if agent_plan["run_maintenance_agent"]:
        langgraph_result = _get_langgraph_analysis(pump_id=pump_id, tank_pct=tank_pct)
    else:
        langgraph_result = {
            "status": "skipped",
            "supervisor_analysis": "Maintenance agent not triggered by supervisor.",
            "maintenance_risk_score": 0.0,
            "maintenance_risk_level": "LOW",
            "maintenance_current_metrics": {},
            "maintenance_failure_signals": [],
            "routing_assignments": [],
            "messages": [],
        }

    maintenance_result = _build_maintenance_output(pump_status, langgraph_result)

    decision = supervisor_decision(
        system_state=system_state,
        forecast=forecast_result,
        maintenance=maintenance_result,
        langgraph_result=langgraph_result,
    )

    return {
        "tank_pct": tank_pct,
        "tank_status": tank_status,
        "pump_status": pump_status,
        "forecast_result": forecast_result,
        "maintenance_result": maintenance_result,
        "langgraph_result": langgraph_result,
        "alerts": decision["alerts"],
        "task_intents": decision["task_intents"],
        "notification_intents": decision["notification_intents"],
        "technician_assignment": decision["technician_assignment"],
        "ai_summary": decision["ai_summary"],
        "ai_reasoning": decision["ai_reasoning"],
        "ai_priority": decision["ai_priority"],
        "ai_action": decision["ai_action"],
    }


def execution_layer(
    *,
    building_id: str,
    notification_intents: List[Dict[str, Any]],
    task_intents: List[Dict[str, Any]],
    task_service: Any,
    notification_service: Any,
) -> Dict[str, Any]:
    """
    Execution layer: side-effects only (persist tasks + emit notifications).
    Returns created artifacts for UI.
    """
    created_tasks: List[Dict[str, Any]] = []
    for intent in task_intents:
        asset_id = intent.get("asset_id")
        if not asset_id:
            continue
        created_tasks.append(
            task_service.create_task(
                title=intent["title"],
                description=intent["description"],
                asset_type=intent["asset_type"],
                asset_id=asset_id,
                building_id=building_id,
                priority=intent["priority"],
                sla_hours=intent["sla_hours"],
            )
        )

    created_notifications: List[Dict[str, Any]] = []
    for idx, intent in enumerate(notification_intents):
        related_task_id: Optional[str] = None
        if idx < len(created_tasks):
            related_task_id = created_tasks[idx].get("task_id")
        asset = intent.get("asset")
        category = intent.get("category", "SYSTEM")
        alert_type = str(intent.get("alert_type", "WARNING")).upper()
        if alert_type == "CRITICAL":
            severity = "CRITICAL"
        elif alert_type == "WARNING":
            severity = "HIGH"
        else:
            severity = "MEDIUM"
        created_notifications.append(
            notification_service.create_notification(
                type=intent.get("type", "ALERT"),
                category=category,
                asset=asset,
                title=f"{asset} {alert_type}",
                message=intent["message"],
                severity=severity,
                details=intent.get("details"),
                action=intent.get("action"),
                building_id=building_id,
                related_task_id=related_task_id,
            )
        )

    return {
        "created_tasks": created_tasks,
        "created_notifications": created_notifications,
    }


def run_water_orchestration(
    *,
    building_id: str,
    mode: str,
    at_time: str | None,
    system_state: Dict[str, Any],
    task_service: Any,
    notification_service: Any,
) -> Dict[str, Any]:
    """
    Central orchestration for /water/run.
    Route should only call this function with prepared inputs.
    """
    # 1) Supervisor returns ONLY data + intents (no side-effects).
    supervisor_out = supervisor_run(
        system_state=system_state,
        building_id=building_id,
        mode=mode,
    )

    # 2) Execution layer performs side-effects (persist tasks + emit notifications).
    exec_out = execution_layer(
        building_id=building_id,
        notification_intents=supervisor_out["notification_intents"],
        task_intents=supervisor_out["task_intents"],
        task_service=task_service,
        notification_service=notification_service,
    )

    tank_status = supervisor_out.get("tank_status", {})
    pump_status = supervisor_out.get("pump_status", {})
    tank_pct = supervisor_out.get("tank_pct", 0.0)

    forecast_result = supervisor_out["forecast_result"]
    maintenance_result = supervisor_out["maintenance_result"]
    langgraph_result = supervisor_out["langgraph_result"]

    alerts = supervisor_out["alerts"]
    created_tasks = exec_out["created_tasks"]
    created_notifications = exec_out["created_notifications"]

    ai_summary = supervisor_out["ai_summary"]
    ai_reasoning = supervisor_out["ai_reasoning"]
    ai_priority = supervisor_out["ai_priority"]
    ai_action = supervisor_out["ai_action"]
    technician_assignment = supervisor_out.get("technician_assignment")

    WATER_STATE.building_id = building_id
    WATER_STATE.level_percentage = tank_pct
    WATER_STATE.level_state = tank_status.get("level_state", "NORMAL")
    WATER_STATE.last_mode = mode
    WATER_STATE.ai_summary = ai_summary

    return {
        "status": "ok",
        "building_id": building_id,
        "mode": mode,
        "at_time": at_time,
        "system_state": system_state,
        "tank_status": tank_status,
        "pump_status": pump_status,
        "forecast": forecast_result,
        "maintenance": maintenance_result,
        "alerts": alerts or [],
        "tasks": created_tasks or [],
        "created_tasks": created_tasks or [],
        "notifications": created_notifications,
        "message": "Supervisor run complete",
        "ai_summary": WATER_STATE.ai_summary,
        "ai_reasoning": ai_reasoning,
        "ai_priority": ai_priority,
        "ai_action": ai_action,
        "langgraph": langgraph_result,
        "technician_assignment": technician_assignment,
    }


def monitor_site(site_id: str) -> Dict:
    """
    Monitor all assets at a site using LangGraph AI agents
    """
    print(f"\n{'='*70}")
    print(f"🏢 MONITORING SITE: {site_id} (LangGraph AI)")
    print(f"{'='*70}\n")
    
    site_config = SITES.get(site_id)
    if not site_config:
        return {"error": f"Site {site_id} not found"}
    
    results = {
        "site_id": site_id,
        "site_name": site_config["name"],
        "timestamp": datetime.now().isoformat(),
        "pumps_analyzed": 0,
        "tasks_created": [],
        "critical_count": 0,
        "high_count": 0,
        "medium_count": 0,
        "low_count": 0,
        "assignments": [],
        "details": []
    }
    
    # Analyze each pump using LangGraph workflow
    for pump_id in site_config["pumps"]:
        print(f"🔍 Analyzing {pump_id} with AI agents...")
        
        try:
            # Run full LangGraph workflow (ML + LLM + Routing)
            workflow_result = run_langgraph_workflow(pump_id)
            
            results["pumps_analyzed"] += 1
            
            # Extract results
            priority = workflow_result.get("priority", "LOW")
            risk_score = workflow_result.get("risk_score", 0)
            action_type = workflow_result.get("action_type", "none")
            reasoning = workflow_result.get("reasoning", "N/A")
            
            # Count by priority
            if priority == "CRITICAL":
                results["critical_count"] += 1
            elif priority == "HIGH":
                results["high_count"] += 1
            elif priority == "MEDIUM":
                results["medium_count"] += 1
            else:
                results["low_count"] += 1
            
            # Add tasks
            if workflow_result.get("tasks"):
                results["tasks_created"].extend(workflow_result["tasks"])
            
            # Add assignments
            if workflow_result.get("assignments"):
                results["assignments"].extend(workflow_result["assignments"])
            
            # Store details
            results["details"].append({
                "pump_id": pump_id,
                "risk_score": risk_score,
                "priority": priority,
                "action_type": action_type,
                "reasoning": reasoning,
                "tasks": workflow_result.get("tasks", []),
                "assignments": workflow_result.get("assignments", [])
            })
            
            print(f"   ✅ {pump_id}: {priority} priority (Risk: {risk_score:.1%})\n")
            
        except Exception as e:
            print(f"   ❌ Error analyzing {pump_id}: {str(e)}\n")
            results["low_count"] += 1
    
    return results


def print_summary(results: Dict):
    """
    Print formatted summary of monitoring results
    """
    print("\n" + "="*70)
    print("📊 SITE MONITORING SUMMARY (LangGraph AI)")
    print("="*70)
    
    print(f"\n🏢 Site: {results['site_name']} ({results['site_id']})")
    print(f"⏰ Timestamp: {results['timestamp']}")
    
    print(f"\n📈 ANALYSIS RESULTS:")
    print(f"   Pumps Analyzed: {results['pumps_analyzed']}")
    print(f"   Tasks Created: {len(results['tasks_created'])}")
    print(f"   Technicians Assigned: {len(results['assignments'])}")
    
    print(f"\n🚨 PRIORITY BREAKDOWN:")
    print(f"   🔴 CRITICAL: {results['critical_count']}")
    print(f"   🟠 HIGH:     {results['high_count']}")
    print(f"   🟡 MEDIUM:   {results['medium_count']}")
    print(f"   🟢 LOW:      {results['low_count']}")
    
    if results['tasks_created']:
        print(f"\n📋 TASKS CREATED:")
        for idx, task in enumerate(results['tasks_created'], 1):
            print(f"\n   Task {idx}:")
            print(f"   {task['priority']}: {task['title']}")
            print(f"   SLA: {task['sla_hours']} hours")
            print(f"   Asset: {task['asset_id']}")
            print(f"   Action: {task['action_type']}")
    
    if results['assignments']:
        print(f"\n👷 TECHNICIAN ASSIGNMENTS:")
        for idx, assignment in enumerate(results['assignments'], 1):
            print(f"\n   Assignment {idx}:")
            print(f"   Task: {assignment['task_id']}")
            print(f"   Technician: {assignment['technician_name']}")
            print(f"   Priority: {assignment['priority']}")
            print(f"   Status: {assignment['status']}")
    
    if not results['tasks_created']:
        print(f"\n✅ No urgent tasks required - all assets operating normally")
    
    print("\n" + "="*70)
    
    if WATER_STATE:
        WATER_STATE.ai_summary = results

def monitor_all_sites() -> List[Dict]:
    """
    Monitor all configured sites
    """
    all_results = []
    
    for site_id in SITES.keys():
        results = monitor_site(site_id)
        all_results.append(results)
        print_summary(results)
    
    return all_results


if __name__ == "__main__":
    """Run site monitoring with LangGraph AI agents"""
    print("="*70)
    print("🚀 HOMENET AI AGENT SYSTEM - SITE MONITORING")
    print("🤖 Powered by LangGraph + LLM")
    print("="*70)
    
    # Monitor all sites
    results = monitor_all_sites()
    
    print("\n" + "="*70)
    print("✅ MONITORING COMPLETE")
    print("="*70)