from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any
import uuid


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _make_id() -> str:
    return f"NOTIF_{uuid.uuid4().hex[:8].upper()}"

push_sent: bool = False

@dataclass
class Notification:
    notification_id: str
    type: str               # SYSTEM / ALERT / INFO
    category: Optional[str] # WATER_LEVEL / PUMP_FAILURE / ...
    asset: Optional[str]    # TANK / PUMP / ...
    title: str
    message: str
    severity: str           # LOW / MEDIUM / HIGH / CRITICAL
    details: Optional[Dict[str, Any]]
    action: Optional[str]
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
        category: Optional[str] = None,
        asset: Optional[str] = None,
        title: str,
        message: str,
        severity: str,
        details: Optional[Dict[str, Any]] = None,
        action: Optional[str] = None,
        building_id: str,
        related_task_id: Optional[str] = None,
    ) -> Dict:
        # De-duplication to avoid flooding from frequent polling across tabs.
        # Look back through recent entries for the same logical notification.
        now_iso = _utc_now()
        try:
            now = datetime.fromisoformat(now_iso)
        except Exception:
            now = None

        for existing in reversed(self._notifications):
            if (
                existing.type == type
                and existing.severity == severity
                and existing.building_id == building_id
                and existing.message == message
            ):
                if now is None:
                    return asdict(existing)
                try:
                    prev = datetime.fromisoformat(existing.created_at)
                    if abs((now - prev).total_seconds()) < 120:
                        return asdict(existing)
                except Exception:
                    return asdict(existing)
                # Older match found outside dedupe window; stop searching.
                break

        notif = Notification(
            notification_id=_make_id(),
            type=type,
            category=category,
            asset=asset,
            title=title,
            message=message,
            severity=severity,
            details=details,
            action=action,
            building_id=building_id,
            related_task_id=related_task_id,
            created_at=now_iso,
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
