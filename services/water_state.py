from dataclasses import dataclass
from typing import Optional

@dataclass
class WaterState:
    building_id: Optional[str]
    level_percentage: float
    level_state: str
    last_mode: Optional[str]
    ai_summary: Optional[str]

WATER_STATE = WaterState(
    building_id=None,
    level_percentage=0.0,
    level_state="UNKNOWN",
    last_mode=None,
    ai_summary=None,
)
