def build_agent_state(site_id: str) -> dict:
    """
    Create initial LangGraph state object (POC placeholder).
    """
    return {"site_id": site_id, "alerts": [], "tasks": []}
