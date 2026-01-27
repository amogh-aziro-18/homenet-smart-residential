from __future__ import annotations

from typing import Any, Dict, List, Optional
from datetime import datetime
import uuid

from sqlalchemy.orm import Session
from sqlalchemy import select

from db.models import TaskDB


def _make_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8].upper()}"


class DBTaskService:
    """
    DB-backed task service.
    MUST match TaskService interface exactly.
    """

    def __init__(self, db: Session):
        self.db = db

    # ✅ SAME SIGNATURE AS TaskService
    def list_tasks(
        self,
        building_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:

        stmt = select(TaskDB)

        if building_id:
            stmt = stmt.where(TaskDB.building_id == building_id)

        if status:
            stmt = stmt.where(TaskDB.status == status)

        stmt = stmt.order_by(TaskDB.created_at.desc())

        if limit:
            stmt = stmt.limit(limit)

        rows = self.db.execute(stmt).scalars().all()

        return [self._to_dict(t) for t in rows]

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

        # ✅ DUPLICATE PREVENTION (same logic as memory version)
        existing = (
            self.db.query(TaskDB)
            .filter(
                TaskDB.status == "OPEN",
                TaskDB.title.ilike(title),
                TaskDB.asset_id == asset_id,
                TaskDB.building_id == building_id,
            )
            .first()
        )

        if existing:
            return self._to_dict(existing)

        now = datetime.utcnow()

        task = TaskDB(
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

        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)

        return self._to_dict(task)

    # 🔁 INTERNAL
    def _to_dict(self, t: TaskDB) -> Dict[str, Any]:
        return {
            "task_id": t.task_id,
            "title": t.title,
            "description": t.description,
            "asset_type": t.asset_type,
            "asset_id": t.asset_id,
            "building_id": t.building_id,
            "priority": t.priority,
            "sla_hours": t.sla_hours,
            "status": t.status,
            "created_at": t.created_at.isoformat(),
            "updated_at": t.updated_at.isoformat(),
            "notes": t.notes,
        }
