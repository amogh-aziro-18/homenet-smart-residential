from typing import List, Optional
from sqlalchemy.orm import Session
from datetime import datetime, timezone
import uuid

from db.models import TaskDB


def _utc_now():
    return datetime.now(timezone.utc)


def _make_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8].upper()}"


def get_all_tasks(db: Session) -> List[TaskDB]:
    return db.query(TaskDB).order_by(TaskDB.created_at.desc()).all()


def find_open_duplicate(
    db: Session,
    title: str,
    asset_id: str,
    building_id: str,
) -> Optional[TaskDB]:
    return (
        db.query(TaskDB)
        .filter(
            TaskDB.status == "OPEN",
            TaskDB.title.ilike(title),
            TaskDB.asset_id == asset_id,
            TaskDB.building_id == building_id,
        )
        .first()
    )


def create_task(
    db: Session,
    *,
    title: str,
    description: str,
    asset_type: str,
    asset_id: str,
    building_id: str,
    priority: str,
    sla_hours: int,
) -> TaskDB:
    existing = find_open_duplicate(
        db=db,
        title=title,
        asset_id=asset_id,
        building_id=building_id,
    )
    if existing:
        return existing

    now = _utc_now()

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
    )

    db.add(task)
    db.commit()
    db.refresh(task)

    return task
