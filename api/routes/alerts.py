from fastapi import APIRouter, Depends, Query
from typing import List, Dict, Optional

from api.dependencies import get_notification_service
from services.notification_service import NotificationService

router = APIRouter()


@router.get("/notifications", response_model=None)
def list_notifications(
    building_id: Optional[str] = Query(None),
    unread_only: bool = Query(False),
    limit: Optional[int] = Query(10),
    notification_service: NotificationService = Depends(get_notification_service),
) -> List[Dict]:
    """
    List system notifications (for mobile app).
    """
    return notification_service.list_notifications(
        building_id=building_id,
        unread_only=unread_only,
        limit=limit,
    )
