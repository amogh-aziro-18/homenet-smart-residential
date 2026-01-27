"""
LangGraph State Management - Typed state for agent workflow
"""
from typing import TypedDict, Annotated, List, Dict, Optional

from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage


class AgentState(TypedDict):
    # Input
    site_id: str
    pump_id: Optional[str]
    building_id: Optional[str]

    # ML Predictions
    risk_score: Optional[float]
    risk_level: Optional[str]
    failure_signals: Optional[List[str]]
    current_metrics: Optional[Dict]

    # Forecasting
    current_demand: Optional[float]
    predicted_demand: Optional[float]
    peak_time: Optional[str]

    # Decision outputs
    action_required: bool
    action_type: Optional[str]
    priority: Optional[str]
    sla_hours: Optional[int]
    reasoning: Optional[str]

    # Tasks
    task_title: Optional[str]
    task_description: Optional[str]
    tasks: List[Dict]
    assignments: List[Dict]

    # Workflow control
    messages: Annotated[List[BaseMessage], add_messages]
    current_agent: Optional[str]
    next_agent: Optional[str]


def build_agent_state(site_id: str, pump_id: str = None, building_id: str = None) -> AgentState:
    return {
        "site_id": site_id,
        "pump_id": pump_id,
        "building_id": building_id,

        "risk_score": None,
        "risk_level": None,
        "failure_signals": None,
        "current_metrics": None,

        "current_demand": None,
        "predicted_demand": None,
        "peak_time": None,

        "action_required": False,
        "action_type": None,
        "priority": None,
        "sla_hours": None,
        "reasoning": None,

        "task_title": None,
        "task_description": None,
        "tasks": [],
        "assignments": [],

        "messages": [],
        "current_agent": None,
        "next_agent": None,
    }
