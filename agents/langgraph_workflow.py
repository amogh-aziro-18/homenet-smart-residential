"""
LangGraph Multi-Agent Workflow - Clean message handling
"""
import sys
import os
from typing import Literal

parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

from langgraph.graph import StateGraph, END
from langchain_core.messages import AIMessage
from agents.state import AgentState, build_agent_state
from agents.maintenance_agent import maintenance_agent_node
from agents.routing_agent import routing_agent_node


def supervisor_node(state: AgentState) -> dict:
    has_pump = state.get("pump_id") is not None
    has_analysis = state.get("risk_score") is not None
    has_tasks = len(state.get("tasks", [])) > 0
    has_assignments = len(state.get("assignments", [])) > 0

    if has_pump and not has_analysis:
        next_agent = "maintenance"
    elif has_tasks and not has_assignments:
        next_agent = "routing"
    else:
        next_agent = "end"

    return {
        "current_agent": "supervisor",
        "next_agent": next_agent,
        "messages": [AIMessage(content="👔 Supervisor Agent orchestrating")],
    }


def route_agent(state: AgentState) -> Literal["maintenance", "routing", "end"]:
    nxt = state.get("next_agent", "end")
    if nxt == "maintenance":
        return "maintenance"
    if nxt == "routing":
        return "routing"
    return "end"


def build_workflow():
    workflow = StateGraph(AgentState)
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("maintenance", maintenance_agent_node)
    workflow.add_node("routing", routing_agent_node)

    workflow.set_entry_point("supervisor")

    workflow.add_conditional_edges(
        "supervisor",
        route_agent,
        {"maintenance": "maintenance", "routing": "routing", "end": END},
    )

    workflow.add_edge("maintenance", "supervisor")
    workflow.add_edge("routing", END)

    return workflow.compile()


def run_langgraph_workflow(pump_id: str):
    app = build_workflow()
    initial_state = build_agent_state(site_id="SITE_001", pump_id=pump_id)
    return app.invoke(initial_state)


if __name__ == "__main__":
    print("=" * 70)
    print("🤖 LANGGRAPH MULTI-AGENT WORKFLOW")
    print("=" * 70)

    result = run_langgraph_workflow("PUMP_BLD_001_01")

    print("\n" + "=" * 70)
    print("WORKFLOW TRACE:")
    print("=" * 70)
    for m in result["messages"]:
        print(f"  {getattr(m, 'content', str(m))}")

    print("\n" + "=" * 70)
    print("FINAL RESULTS:")
    print("=" * 70)
    print(f"Risk: {result['risk_score']:.1%} ({result['risk_level']})")
    print(f"Action: {result['action_type']}")
    print(f"Priority: {result['priority']}")
    print(f"SLA: {result['sla_hours']}h")
    print(f"\n🤖 AI Reasoning: {result['reasoning']}")

    if result.get("assignments"):
        print("\n📋 Task Assignments:")
        for a in result["assignments"]:
            print(f"  → {a['technician_name']} (Status: {a['status']})")

    print("\n" + "=" * 70)