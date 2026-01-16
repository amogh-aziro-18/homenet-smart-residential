def create_work_order(alert: dict, assignee_id: str | None = None) -> dict:
    """
    Create a task/work order from an alert.
    """
    return {"status": "ok", "work_order": {}}


def update_task_status(task_id: str, status: str) -> dict:
    """
    Update work order status (OPEN, IN_PROGRESS, CLOSED).
    """
    return {"status": "ok", "task_id": task_id, "new_status": status}
