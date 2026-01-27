from __future__ import annotations

import os
import pandas as pd
from typing import Any, Dict, List, Optional


class AssetService:
    def __init__(self, tanks_csv_path: str = "data/samples/water_tanks.csv"):
        self.tanks_csv_path = tanks_csv_path

    def load_tanks(self) -> pd.DataFrame:
        if not os.path.exists(self.tanks_csv_path):
            raise FileNotFoundError(f"Tank CSV not found at: {self.tanks_csv_path}")

        df = pd.read_csv(self.tanks_csv_path)

        # normalize timestamp
        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"])
        else:
            raise ValueError("water_tanks.csv must have 'timestamp' column")

        return df

    def list_tanks(self) -> List[Dict[str, Any]]:
        df = self.load_tanks()
        df = df.copy()
        df["timestamp"] = df["timestamp"].astype(str)
        return df.to_dict(orient="records")

    def _derive_level_state(self, level_pct: float) -> str:
        """
        Water tank level state thresholds (POC rules).
        """
        if level_pct <= 20:
            return "CRITICAL"
        if level_pct <= 30:
            return "LOW"
        return "NORMAL"

    def _format_tank_status(self, building_id: str, row: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert selected tank row into API-safe tank status dict.
        """
        level_pct = float(row.get("level_percentage", 0.0))
        level_state = self._derive_level_state(level_pct)

        return {
            "status": "ok",
            "building_id": building_id,
            "tank_id": row.get("tank_id"),
            "timestamp": str(row.get("timestamp")),
            "capacity_liters": row.get("capacity_liters"),
            "current_level_liters": row.get("current_level_liters"),
            "level_percentage": level_pct,
            "level_state": level_state,
        }

    def get_latest_tank_status_by_building(self, building_id: str) -> Dict[str, Any]:
        """
        ✅ Backward compatible function.
        Always returns the latest row for building.
        """
        return self.get_tank_status_by_building(building_id=building_id, mode="latest")

    def get_tank_status_by_building(
        self,
        building_id: str,
        mode: str = "latest",  # latest | worst | at_time
        at_time: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Flexible tank status getter for supervisor.

        mode:
        - latest  : most recent timestamp row
        - worst   : lowest level_percentage row (good for demo task creation)
        - at_time : get row at a specific timestamp (closest match)

        at_time: required if mode="at_time"
        """
        df = self.load_tanks()

        if "building_id" not in df.columns:
            raise ValueError("water_tanks.csv must have 'building_id' column")

        sub = df[df["building_id"] == building_id].copy()

        if sub.empty:
            return {"status": "not_found", "building_id": building_id}

        if mode == "latest":
            sub = sub.sort_values("timestamp")
            chosen = sub.iloc[-1].to_dict()
            return self._format_tank_status(building_id, chosen)

        if mode == "worst":
            # lowest tank percentage row (best for showing LOW alerts/tasks)
            sub = sub.sort_values("level_percentage")
            chosen = sub.iloc[0].to_dict()
            return self._format_tank_status(building_id, chosen)

        if mode == "at_time":
            if not at_time:
                return {
                    "status": "error",
                    "message": "mode='at_time' requires at_time param (ISO datetime string)",
                }

            t = pd.to_datetime(at_time)

            # choose nearest timestamp
            sub["time_diff"] = (sub["timestamp"] - t).abs()
            sub = sub.sort_values("time_diff")
            chosen = sub.iloc[0].to_dict()

            # remove helper column if exists
            chosen.pop("time_diff", None)

            return self._format_tank_status(building_id, chosen)

        return {
            "status": "error",
            "message": f"Invalid mode: {mode}. Use latest | worst | at_time",
        }
