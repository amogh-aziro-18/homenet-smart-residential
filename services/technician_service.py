from __future__ import annotations

import csv
import os
from typing import Any, Dict, List

TECHNICIANS_CSV_PATH = "data/samples/technicians.csv"


def _to_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def _to_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _parse_skills(raw: Any) -> List[str]:
    if raw is None:
        return []
    return [s.strip().lower() for s in str(raw).split(",") if s.strip()]


def _fallback_technicians() -> Dict[str, Dict[str, Any]]:
    # Fallback protects runtime if CSV is missing/corrupt.
    return {
        "TECH_001": {
            "name": "Technician A",
            "skills": ["pumps", "electrical", "plumbing"],
            "available": True,
            "current_load": 2,
            "max_capacity": 5,
        },
        "TECH_002": {
            "name": "Technician B",
            "skills": ["pumps", "mechanical", "sensors"],
            "available": True,
            "current_load": 1,
            "max_capacity": 5,
        },
        "TECH_003": {
            "name": "Technician C",
            "skills": ["plumbing", "general"],
            "available": False,
            "current_load": 5,
            "max_capacity": 5,
        },
    }


def load_technicians(path: str = TECHNICIANS_CSV_PATH) -> Dict[str, Dict[str, Any]]:
    if not os.path.exists(path):
        return _fallback_technicians()

    technicians: Dict[str, Dict[str, Any]] = {}
    try:
        with open(path, "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                tech_id = str(row.get("technician_id", "")).strip()
                if not tech_id:
                    continue
                max_capacity = max(1, _to_int(row.get("max_capacity"), 5))
                current_load = max(0, _to_int(row.get("current_load"), 0))
                technicians[tech_id] = {
                    "name": str(row.get("name", tech_id)).strip() or tech_id,
                    "skills": _parse_skills(row.get("skills")),
                    "available": _to_bool(row.get("available"), True),
                    "current_load": current_load,
                    "max_capacity": max_capacity,
                }
    except Exception:
        return _fallback_technicians()

    return technicians or _fallback_technicians()


def get_available_pump_technicians(path: str = TECHNICIANS_CSV_PATH) -> List[Dict[str, Any]]:
    technicians = load_technicians(path=path)
    out: List[Dict[str, Any]] = []
    for tech_id, tech in technicians.items():
        if not tech.get("available"):
            continue
        if "pumps" not in (tech.get("skills") or []):
            continue
        out.append({"technician_id": tech_id, **tech})
    out.sort(key=lambda t: int(t.get("current_load", 999)))
    return out
