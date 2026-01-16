def list_tasks(site_id: str) -> dict:
    return {"status": "ok", "tasks": []}


def complete_task(task_id: str) -> dict:
    return {"status": "ok", "task_id": task_id}
