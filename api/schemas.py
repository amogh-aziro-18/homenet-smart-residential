from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime


# -----------------------------
# Forecast Schemas
# -----------------------------
class ForecastPoint(BaseModel):
    timestamp: str
    value: float
    lower: float
    upper: float


class WaterDemandForecastResponse(BaseModel):
    status: str
    asset_id: str
    horizon_hours: int
    prediction_time: str
    forecast_start: Optional[str] = None
    forecast_end: Optional[str] = None
    forecast_total: float
    demand_level: str
    recommendation: str
    peak_hour: Optional[Dict[str, Any]] = None
    top_3_hours: List[Dict[str, Any]] = []
    forecast_series: List[ForecastPoint]
    model_name: str


# -----------------------------
# Task Schemas
# -----------------------------
TaskStatus = Literal["OPEN", "IN_PROGRESS", "DONE", "CANCELLED"]
TaskPriority = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]


class TaskCreateRequest(BaseModel):
    title: str
    description: Optional[str] = None
    asset_type: Optional[str] = Field(default="water", description="water/pump/tank")
    asset_id: Optional[str] = None
    building_id: Optional[str] = None
    priority: TaskPriority = "MEDIUM"
    sla_hours: int = 24


class TaskUpdateRequest(BaseModel):
    status: Optional[TaskStatus] = None
    notes: Optional[str] = None


class TaskResponse(BaseModel):
    task_id: str
    title: str
    description: Optional[str] = None
    asset_type: Optional[str] = "water"
    asset_id: Optional[str] = None
    building_id: Optional[str] = None
    priority: TaskPriority
    sla_hours: int
    status: TaskStatus
    created_at: str
    updated_at: str
    notes: Optional[str] = None
