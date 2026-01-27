from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _make_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8].upper()}"


@dataclass
class Task:
    task_id: str
    title: str
    description: str
    asset_type: str
    asset_id: str
    building_id: str
    priority: str
    sla_hours: int
    status: str
    created_at: str
    updated_at: str
    notes: Optional[str] = None


class TaskService:
    """
    In-memory task store with minimal history support.
    """

    def __init__(self):
        self._tasks: List[Task] = []

    def list_tasks(
        self,
        building_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        List tasks with optional filters (history support).
        """
        tasks = self._tasks

        if building_id:
            tasks = [t for t in tasks if t.building_id == building_id]

        if status:
            tasks = [t for t in tasks if t.status == status]

        tasks = sorted(tasks, key=lambda t: t.created_at, reverse=True)

        if limit:
            tasks = tasks[:limit]

        return [asdict(t) for t in tasks]

    def _find_open_duplicate(
        self, title: str, asset_id: str, building_id: str
    ) -> Optional[Task]:
        for t in self._tasks:
            if (
                t.status == "OPEN"
                and t.title.lower() == title.lower()
                and t.asset_id == asset_id
                and t.building_id == building_id
            ):
                return t
        return None

    def create_task(
        self,
        title: str,
        description: str,
        asset_type: str,
        asset_id: str,
        building_id: str,
        priority: str = "MEDIUM",
        sla_hours: int = 24,
    ) -> Dict[str, Any]:

        dup = self._find_open_duplicate(title, asset_id, building_id)
        if dup:
            return asdict(dup)

        now = _utc_now().isoformat()

        task = Task(
            task_id=_make_id("TASK"),
            title=title,
            description=description,
            asset_type=asset_type,
            asset_id=asset_id,
            building_id=building_id,
            priority=priority,
            sla_hours=sla_hours,
            status="OPEN",
            created_at=now,
            updated_at=now,
            notes=None,
        )

        self._tasks.append(task)
        return asdict(task)
