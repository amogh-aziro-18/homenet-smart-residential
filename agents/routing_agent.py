"""
Routing Agent - Assigns tasks to technicians based on availability and skills
LangGraph-safe: returns message deltas (for add_messages reducer).
"""
import sys
import os
from datetime import datetime
from typing import List, Dict, Optional

parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

from agents.state import AgentState
from langchain_core.messages import AIMessage


# Technician database (mock)
TECHNICIANS = {
    "TECH_001": {
        "name": "Technician A",
        "skills": ["pumps", "electrical", "plumbing"],
        "available": True,
        "current_load": 2,
        "max_capacity": 5,
    },
    "TECH_002": {
        "name": "Technician B",
        "skills": ["pumps", "mechanical", "sensors"],
        "available": True,
        "current_load": 1,
        "max_capacity": 5,
    },
    "TECH_003": {
        "name": "Technician C",
        "skills": ["plumbing", "general"],
        "available": False,
        "current_load": 5,
        "max_capacity": 5,
    },
    "TECH_004": {
        "name": "Technician D",
        "skills": ["electrical", "sensors", "diagnostics"],
        "available": True,
        "current_load": 0,
        "max_capacity": 5,
    },
}


def get_required_skills(action_type: str) -> List[str]:
    """Determine required skills based on action type."""
    skill_map = {
        "urgent_inspection": ["pumps", "diagnostics"],
        "scheduled_maintenance": ["pumps", "mechanical"],
        "enhanced_monitoring": ["sensors"],
        "capacity_alert": ["pumps", "electrical"],
        "capacity_monitoring": ["sensors"],
    }
    return skill_map.get(action_type, ["general"])


def assign_technician(task: Dict, required_skills: List[str]) -> Optional[str]:
    """Find best available technician for a task."""
    candidates = []

    # Priority 1: available + skill match, lowest load wins
    for tech_id, tech in TECHNICIANS.items():
        if not tech["available"]:
            continue
        if any(skill in tech["skills"] for skill in required_skills):
            candidates.append((tech_id, tech["current_load"]))

    candidates.sort(key=lambda x: x[1])
    if candidates:
        return candidates[0][0]

    # Priority 2: any available tech
    for tech_id, tech in TECHNICIANS.items():
        if tech["available"]:
            return tech_id

    return None


def routing_agent_node(state: AgentState) -> Dict:
    """
    LangGraph node: return ONLY state updates (including messages as deltas).
    """
    new_messages = [AIMessage(content="🔀 Routing Agent assigning tasks")]

    tasks = state.get("tasks", [])
    existing_assignments = state.get("assignments", []) or []
    new_assignments = []

    for task in tasks:
        task_id = task.get("task_id")

        # Skip if already assigned
        if any(a.get("task_id") == task_id for a in existing_assignments):
            continue

        required_skills = get_required_skills(task.get("action_type", "general"))
        tech_id = assign_technician(task, required_skills)

        if tech_id:
            assignment = {
                "task_id": task_id,
                "task_title": task.get("title"),
                "technician_id": tech_id,
                "technician_name": TECHNICIANS[tech_id]["name"],
                "priority": task.get("priority"),
                "sla_hours": task.get("sla_hours"),
                "assigned_at": datetime.now().isoformat(),
                "status": "assigned",
            }
            new_assignments.append(assignment)

            # Update mock technician load
            TECHNICIANS[tech_id]["current_load"] += 1
            if TECHNICIANS[tech_id]["current_load"] >= TECHNICIANS[tech_id]["max_capacity"]:
                TECHNICIANS[tech_id]["available"] = False

            new_messages.append(
                AIMessage(content=f"✅ Assigned {task_id} to {TECHNICIANS[tech_id]['name']}")
            )
        else:
            assignment = {
                "task_id": task_id,
                "task_title": task.get("title"),
                "technician_id": None,
                "technician_name": "ESCALATED - No available technician",
                "priority": task.get("priority"),
                "sla_hours": task.get("sla_hours"),
                "assigned_at": datetime.now().isoformat(),
                "status": "escalated",
            }
            new_assignments.append(assignment)
            new_messages.append(
                AIMessage(content=f"⚠️ ESCALATED {task_id} - No technician available")
            )

    return {
        "current_agent": "routing",
        "next_agent": "end",
        "assignments": existing_assignments + new_assignments,
        "messages": new_messages,  # IMPORTANT: only new messages; add_messages will merge
    }


def run_routing_agent(tasks: List[Dict]) -> Dict:
    """
    Standalone runner (outside LangGraph).
    """
    from agents.state import build_agent_state

    state = build_agent_state(site_id="SITE_001")
    state["tasks"] = tasks

    updates = routing_agent_node(state)

    # Manual merge for standalone readability
    merged_messages = (state.get("messages", []) or []) + updates.get("messages", [])
    merged_assignments = updates.get("assignments", [])

    return {
        "tasks_assigned": len(merged_assignments),
        "assignments": merged_assignments,
        "messages": [m.content for m in merged_messages],
    }


if __name__ == "__main__":
    print("=" * 70)
    print("ROUTING AGENT TEST (LangGraph-safe)")
    print("=" * 70)

    mock_tasks = [
        {
            "task_id": "TASK_PUMP_BLD_001_01",
            "title": "CRITICAL: Inspect PUMP_BLD_001_01",
            "action_type": "urgent_inspection",
            "priority": "CRITICAL",
            "sla_hours": 4,
        },
        {
            "task_id": "TASK_PUMP_BLD_002_01",
            "title": "CRITICAL: Inspect PUMP_BLD_002_01",
            "action_type": "urgent_inspection",
            "priority": "CRITICAL",
            "sla_hours": 4,
        },
        {
            "task_id": "TASK_BLD_001_CAPACITY",
            "title": "HIGH: Capacity Alert BLD_001",
            "action_type": "capacity_alert",
            "priority": "HIGH",
            "sla_hours": 6,
        },
    ]

    result = run_routing_agent(mock_tasks)

    print("\nMessages:")
    for msg in result["messages"]:
        print(f"  {msg}")

    print("\nAssignments:")
    for a in result["assignments"]:
        print(f"  {a['task_id']} -> {a['technician_name']} ({a['status']})")

    print("\n" + "=" * 70)
