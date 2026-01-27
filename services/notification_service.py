from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import List, Dict, Optional
import uuid


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _make_id() -> str:
    return f"NOTIF_{uuid.uuid4().hex[:8].upper()}"


@dataclass
class Notification:
    notification_id: str
    type: str               # SYSTEM / ALERT / INFO
    title: str
    message: str
    severity: str           # LOW / MEDIUM / HIGH / CRITICAL
    building_id: str
    related_task_id: Optional[str]
    created_at: str
    read: bool = False


class NotificationService:
    """
    In-memory notification store (POC).
    """
    def __init__(self):
        self._notifications: List[Notification] = []

    def create_notification(
        self,
        *,
        type: str,
        title: str,
        message: str,
        severity: str,
        building_id: str,
        related_task_id: Optional[str] = None,
    ) -> Dict:
        notif = Notification(
            notification_id=_make_id(),
            type=type,
            title=title,
            message=message,
            severity=severity,
            building_id=building_id,
            related_task_id=related_task_id,
            created_at=_utc_now(),
            read=False,
        )
        self._notifications.append(notif)
        return asdict(notif)

    def list_notifications(
        self,
        building_id: Optional[str] = None,
        unread_only: bool = False,
        limit: Optional[int] = None,
    ) -> List[Dict]:
        notifs = self._notifications

        if building_id:
            notifs = [n for n in notifs if n.building_id == building_id]

        if unread_only:
            notifs = [n for n in notifs if not n.read]

        notifs = sorted(notifs, key=lambda n: n.created_at, reverse=True)

        if limit:
            notifs = notifs[:limit]

        return [asdict(n) for n in notifs]

    def mark_as_read(self, notification_id: str) -> None:
        for n in self._notifications:
            if n.notification_id == notification_id:
                n.read = True
                break
