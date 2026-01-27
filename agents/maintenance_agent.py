"""
Maintenance Agent - LLM-powered analysis with LangGraph (safe message updates)
"""
import sys
import os

parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

models_path = os.path.join(parent_dir, "models", "predictive_maintenance")
sys.path.insert(0, models_path)

from predict import predict_failure_risk
from agents.state import AgentState
from agents.llm_config import get_llm
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage


def _merge_state(state: AgentState, updates: dict) -> AgentState:
    """Merge updates into a copy of state, but keep messages as 'new messages only'."""
    new_state = dict(state)
    for k, v in updates.items():
        if k != "messages":
            new_state[k] = v
    if "messages" in updates:
        new_state["messages"] = updates["messages"]
    return new_state


def maintenance_agent_node(state: AgentState) -> AgentState:
    pump_id = state.get("pump_id")

    updates = {
        "current_agent": "maintenance",
        "next_agent": "supervisor",
        "messages": [AIMessage(content=f"🔧 AI Maintenance Agent analyzing pump: {pump_id}")],
    }

    try:
        prediction = predict_failure_risk(pump_id, horizon_hours=48)

        updates.update({
            "risk_score": prediction["risk_score"],
            "risk_level": prediction["risk_level"],
            "failure_signals": prediction["signals"],
            "current_metrics": prediction["current_metrics"],
        })

        llm = get_llm()

        prompt = f"""You are an AI maintenance agent analyzing pump failure risk.

PUMP: {pump_id}
RISK SCORE: {prediction['risk_score']:.1%}
RISK LEVEL: {prediction['risk_level']}

CURRENT METRICS:
- Vibration: {prediction['current_metrics']['vibration']:.2f} mm/s
- Temperature: {prediction['current_metrics']['temperature']:.1f}°C
- Pressure: {prediction['current_metrics']['pressure']:.1f} bar

FAILURE SIGNALS:
{chr(10).join(f"- {signal}" for signal in prediction['signals'])}

Decide:
ACTION_REQUIRED: true/false
ACTION_TYPE: urgent_inspection | scheduled_maintenance | enhanced_monitoring | none
PRIORITY: CRITICAL | HIGH | MEDIUM | LOW
SLA_HOURS: 4 | 24 | 72 | null
REASONING: max 2 sentences

Return EXACTLY:
ACTION_REQUIRED: ...
ACTION_TYPE: ...
PRIORITY: ...
SLA_HOURS: ...
REASONING: ...
"""

        resp = llm.invoke([
            SystemMessage(content="You are an expert maintenance engineer AI assistant."),
            HumanMessage(content=prompt),
        ])

        llm_decision = {}
        for line in resp.content.strip().split("\n"):
            if ":" in line:
                k, v = line.split(":", 1)
                llm_decision[k.strip()] = v.strip()

        action_required = llm_decision.get("ACTION_REQUIRED", "false").lower() == "true"
        action_type = llm_decision.get("ACTION_TYPE", "none")
        priority = llm_decision.get("PRIORITY", "LOW")
        reasoning = llm_decision.get("REASONING", "No reasoning provided")

        sla_raw = llm_decision.get("SLA_HOURS", "null")
        try:
            sla_hours = int(sla_raw) if sla_raw != "null" else None
        except Exception:
            sla_hours = None

        updates.update({
            "action_required": action_required,
            "action_type": action_type,
            "priority": priority,
            "sla_hours": sla_hours,
            "reasoning": reasoning,
        })

        # If task needed, add exactly once
        if action_required:
            task_id = f"TASK_{pump_id}"
            existing = any(t.get("task_id") == task_id for t in state.get("tasks", []))
            if not existing:
                task = {
                    "task_id": task_id,
                    "title": f"{priority}: Inspect {pump_id}",
                    "description": f"Risk: {prediction['risk_score']:.1%}. Signals: {', '.join(prediction['signals'][:2])}. {reasoning}",
                    "priority": priority,
                    "sla_hours": sla_hours,
                    "action_type": action_type,
                    "asset_id": pump_id,
                }
                updates["tasks"] = state.get("tasks", []) + [task]
                updates["task_title"] = task["title"]
                updates["task_description"] = task["description"]
                updates["messages"] = updates["messages"] + [AIMessage(content=f"⚠️ {priority}: {pump_id} requires {action_type}")]
            else:
                updates["messages"] = updates["messages"] + [AIMessage(content=f"ℹ️ Task already exists for {pump_id}")]
        else:
            updates["task_title"] = None
            updates["task_description"] = None
            updates["messages"] = updates["messages"] + [AIMessage(content=f"✅ {pump_id} operating normally")]

    except Exception as e:
        updates.update({
            "action_required": False,
            "next_agent": "supervisor",
            "messages": updates["messages"] + [AIMessage(content=f"❌ Error in maintenance agent: {str(e)}")],
        })

    return _merge_state(state, updates)


if __name__ == "__main__":
    from agents.state import build_agent_state

    print("=" * 70)
    print("🤖 AI MAINTENANCE AGENT TEST (with LLM)")
    print("=" * 70)

    s = build_agent_state(site_id="SITE_001", pump_id="PUMP_BLD_001_01")
    out = maintenance_agent_node(s)

    print(f"\nPump: {out['pump_id']}")
    print(f"Risk: {out['risk_score']:.1%} ({out['risk_level']})")
    print(f"Action: {out['action_type']}")
    print(f"Priority: {out['priority']}")
    print(f"SLA: {out['sla_hours']}h")
    print(f"\n🤖 LLM Reasoning: {out['reasoning']}")
