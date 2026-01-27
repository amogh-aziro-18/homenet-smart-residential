from fastapi import Depends
from sqlalchemy.orm import Session

from db.session import get_db
from services.db_task_service import DBTaskService

from fastapi import Request
from services.notification_service import NotificationService

def get_task_service(db: Session = Depends(get_db)) -> DBTaskService:
    """
    Single source of truth for task service.
    """
    return DBTaskService(db)

def get_notification_service(request: Request) -> NotificationService:
    """
    Single source of truth for notification service.
    """
    return request.app.state.notification_service