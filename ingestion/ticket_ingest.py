def ingest_ticket(ticket: dict) -> dict:
    """
    Ingest complaint/service ticket into DB (POC placeholder).
    """
    return {"status": "ok", "data": ticket}


def generate_synthetic_tickets(site_id: str, n: int = 20) -> list[dict]:
    """
    Generate synthetic complaint tickets for POC placeholder.
    """
    return []
