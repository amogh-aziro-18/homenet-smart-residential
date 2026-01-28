def ingest_ticket(ticket: dict) -> dict:
    """
    Ingest complaint/service ticket into DB (POC placeholder).
    Processes ticket and categorizes it for agent routing.
    
    Args:
        ticket: Raw ticket data
        
    Returns:
        Processed ticket with status
    """
    import os
    import json
    from datetime import datetime
    
    # Category mapping
    category_map = {
        "no water": "water_supply",
        "low pressure": "water_pressure",
        "pump noise": "pump_failure",
        "pump not working": "pump_failure",
        "leakage": "water_leak",
        "overflow": "tank_overflow",
        "dirty water": "water_quality",
        "motor": "pump_failure",
        "vibration": "pump_vibration"
    }
    
    # Auto-categorize based on description
    description = ticket.get("description", "").lower()
    category = "general_maintenance"
    
    for keyword, cat in category_map.items():
        if keyword in description:
            category = cat
            break
    
    # Priority mapping
    priority_map = {"urgent": "CRITICAL", "high": "HIGH", "medium": "MEDIUM", "low": "LOW"}
    priority = priority_map.get(ticket.get("priority", "medium").lower(), "MEDIUM")
    
    # Build processed ticket
    processed = {
        "ticket_id": ticket.get("ticket_id", f"TKT_{int(datetime.now().timestamp())}"),
        "description": ticket.get("description", ""),
        "category": category,
        "priority": priority,
        "building_id": ticket.get("building", ""),
        "asset_id": ticket.get("asset_id", ""),
        "reported_at": ticket.get("reported_at", datetime.now().isoformat()),
        "processed_at": datetime.now().isoformat(),
        "status": "ingested"
    }
    
    # Save to file (POC - in production, save to DB)
    os.makedirs("data/tickets", exist_ok=True)
    output_file = f"data/tickets/ingested_{datetime.now().strftime('%Y%m%d')}.jsonl"
    
    with open(output_file, "a") as f:
        f.write(json.dumps(processed) + "\n")
    
    print(f"✅ Ticket {processed['ticket_id']} ingested - Category: {category}, Priority: {priority}")
    
    return {"status": "ok", "data": processed}


def generate_synthetic_tickets(site_id: str, n: int = 20) -> list[dict]:
    """
    Generate synthetic complaint tickets for POC placeholder.
    
    Args:
        site_id: Site identifier
        n: Number of tickets to generate
        
    Returns:
        List of synthetic ticket dictionaries
    """
    import random
    from datetime import datetime, timedelta
    
    ticket_templates = [
        {"description": "No water supply in my flat", "priority": "urgent", "building": "BLD_001"},
        {"description": "Very low water pressure", "priority": "high", "building": "BLD_001"},
        {"description": "Pump making loud noise", "priority": "high", "building": "BLD_002"},
        {"description": "Water leakage from overhead tank", "priority": "medium", "building": "BLD_002"},
        {"description": "Pump not working at all", "priority": "urgent", "building": "BLD_001"},
        {"description": "Dirty water coming from tap", "priority": "high", "building": "BLD_001"},
        {"description": "Tank overflow issue", "priority": "medium", "building": "BLD_002"},
        {"description": "Motor vibration is excessive", "priority": "high", "building": "BLD_002"},
        {"description": "Need routine maintenance check", "priority": "low", "building": "BLD_001"},
        {"description": "Water supply timing issue", "priority": "medium", "building": "BLD_002"},
    ]
    
    buildings = ["BLD_001", "BLD_002"]
    start_date = datetime.now() - timedelta(days=30)
    
    tickets = []
    for i in range(n):
        template = random.choice(ticket_templates)
        report_date = start_date + timedelta(hours=random.randint(0, 720))
        
        ticket = {
            "ticket_id": f"TKT_{site_id}_{i+1:04d}",
            "site_id": site_id,
            "building": random.choice(buildings),
            "description": template["description"],
            "priority": template["priority"],
            "reported_at": report_date.isoformat(),
            "flat_no": f"{random.randint(1,4)}{random.randint(0,9):02d}",
            "asset_id": f"PUMP_{random.choice(buildings)}_{random.randint(1,2):02d}" if "pump" in template["description"].lower() else ""
        }
        
        tickets.append(ticket)
    
    return tickets

if __name__ == "__main__":
    """Test ticket ingestion"""
    print("="*70)
    print("🎫 TICKET INGESTION TEST")
    print("="*70)
    from datetime import datetime   
    # Generate synthetic tickets
    print("\n📝 Generating 10 synthetic tickets...")
    tickets = generate_synthetic_tickets("SITE_001", n=10)
    print(f"✅ Generated {len(tickets)} tickets")
    
    # Ingest them
    print("\n🔄 Ingesting tickets...")
    for ticket in tickets:
        result = ingest_ticket(ticket)
    
    print("\n✅ Ingestion test complete!")
    print(f"📁 Check: data/tickets/ingested_{datetime.now().strftime('%Y%m%d')}.jsonl")
from datetime import datetime