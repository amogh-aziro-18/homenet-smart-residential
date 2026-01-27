from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from typing import Any, Dict, List, Optional
from pydantic import BaseModel

from api.dependencies import get_task_service
from services.task_service import TaskService

router = APIRouter()


class TaskCreateRequest(BaseModel):
    title: str
    description: str
    asset_type: str
    asset_id: str
    building_id: str
    priority: str = "MEDIUM"
    sla_hours: int = 24


@router.get("/tasks", response_model=None)
def list_tasks(
    building_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: Optional[int] = Query(None),
    task_service: TaskService = Depends(get_task_service),
) -> List[Dict[str, Any]]:
    """
    List tasks with optional history filters.
    """
    return task_service.list_tasks(
        building_id=building_id,
        status=status,
        limit=limit,
    )


@router.post("/tasks", response_model=None)
def create_task(
    payload: TaskCreateRequest,
    task_service: TaskService = Depends(get_task_service),
) -> Dict[str, Any]:
    return task_service.create_task(
        title=payload.title,
        description=payload.description,
        asset_type=payload.asset_type,
        asset_id=payload.asset_id,
        building_id=payload.building_id,
        priority=payload.priority,
        sla_hours=payload.sla_hours,
    )
