from __future__ import annotations

import os
import time
from typing import Any, Dict, List, Optional

import pandas as pd

CONFIG = {
    "tank_low": 30,
    "tank_critical": 20,
    "vibration_high": 10,
    "temperature_high": 70,
    "pressure_low": 30,
}


class AssetService:
    def __init__(
        self,
        tanks_csv_path: str = "data/samples/water_tanks.csv",
        pumps_csv_path: str = "data/samples/water_pumps.csv",
    ):
        self.tanks_csv_path = tanks_csv_path
        self.pumps_csv_path = pumps_csv_path
        # Keep a stable snapshot within a short window, then advance to next CSV row.
        self._latest_sequence_index: Dict[str, int] = {}
        self._latest_sequence_bucket: Dict[str, int] = {}
        # Same behavior for worst-case mode: stable per window, rotating across windows.
        self._worst_sequence_index: Dict[str, int] = {}
        self._worst_sequence_bucket: Dict[str, int] = {}

    def load_tanks(self) -> pd.DataFrame:
        if not os.path.exists(self.tanks_csv_path):
            raise FileNotFoundError(f"Tank CSV not found at: {self.tanks_csv_path}")

        df = pd.read_csv(self.tanks_csv_path)

        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"])
        else:
            raise ValueError("water_tanks.csv must have 'timestamp' column")

        return df

    def load_pumps(self) -> pd.DataFrame:
        if not os.path.exists(self.pumps_csv_path):
            raise FileNotFoundError(f"Pump CSV not found at: {self.pumps_csv_path}")

        df = pd.read_csv(self.pumps_csv_path)

        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"])
        else:
            raise ValueError("water_pumps.csv must have 'timestamp' column")

        required_cols = {
            "pump_id",
            "building_id",
            "tank_id",
            "status",
            "current_amps",
            "vibration_mm_s",
            "temperature_celsius",
            "flow_rate_lpm",
            "pressure_psi",
        }
        missing = required_cols - set(df.columns)
        if missing:
            raise ValueError(f"water_pumps.csv missing columns: {sorted(missing)}")

        return df

    def list_tanks(self) -> List[Dict[str, Any]]:
        df = self.load_tanks().copy()
        df["timestamp"] = df["timestamp"].astype(str)
        return df.to_dict(orient="records")

    def _derive_level_state(self, level_pct: float) -> str:
        if level_pct <= CONFIG["tank_critical"]:
            return "CRITICAL"
        if level_pct <= CONFIG["tank_low"]:
            return "LOW"
        return "NORMAL"

    def _format_tank_status(self, building_id: str, row: Dict[str, Any]) -> Dict[str, Any]:
        level_pct = float(row.get("level_percentage", 0.0))
        level_state = self._derive_level_state(level_pct)

        capacity = float(row.get("capacity_liters", 5000))
        current_level = round((level_pct / 100.0) * capacity, 1)

        return {
            "status": "ok",
            "building_id": building_id,
            "tank_id": row.get("tank_id"),
            "timestamp": str(row.get("timestamp")),
            "capacity_liters": capacity,
            "current_level_liters": current_level,
            "level_percentage": level_pct,
            "level_state": level_state,
        }

    def _derive_pump_signals(self, row: Dict[str, Any]) -> Dict[str, bool]:
        vibration = float(row.get("vibration_mm_s", 0.0))
        temperature = float(row.get("temperature_celsius", 0.0))
        pressure = float(row.get("pressure_psi", 0.0))
        flow = float(row.get("flow_rate_lpm", 0.0))

        return {
            "high_vibration": vibration > CONFIG["vibration_high"],
            "high_temperature": temperature > CONFIG["temperature_high"],
            "low_pressure": pressure < CONFIG["pressure_low"],
            "low_flow": flow < 120.0,
        }

    def _pump_risk_proxy(self, row: Dict[str, Any]) -> int:
        signals = self._derive_pump_signals(row)
        score = 0
        if signals["high_vibration"]:
            score += 2
        if signals["high_temperature"]:
            score += 2
        if signals["low_pressure"]:
            score += 1
        if signals["low_flow"]:
            score += 1
        if str(row.get("status", "")).lower() != "running":
            score += 1
        return score

    def _derive_pump_condition(self, risk_score: int) -> str:
        if risk_score >= 5:
            return "CRITICAL"
        if risk_score >= 3:
            return "HIGH"
        if risk_score >= 1:
            return "MEDIUM"
        return "LOW"

    def _pick_rotating_row(
        self,
        *,
        sub: pd.DataFrame,
        bucket_seconds: int = 10,
    ) -> Dict[str, Any]:
        """
        Pick one row from an already-ranked dataframe by rotating every time bucket.
        This guarantees:
        - cross-tab consistency within a bucket
        - different CSV record across buckets (data-driven, not hardcoded)
        """
        if sub.empty:
            return {}

        # Stateless rotation: changes with time bucket even across service re-instantiation.
        bucket = int(time.time() // bucket_seconds)
        idx = bucket % len(sub)
        return sub.iloc[idx].to_dict()

    def _format_pump_status(self, building_id: str, row: Dict[str, Any]) -> Dict[str, Any]:
        signals = self._derive_pump_signals(row)
        proxy_score = self._pump_risk_proxy(row)

        return {
            "status": "ok",
            "building_id": building_id,
            "pump_id": row.get("pump_id"),
            "tank_id": row.get("tank_id"),
            "timestamp": str(row.get("timestamp")),
            "operating_state": row.get("status"),
            "telemetry": {
                "current_amps": float(row.get("current_amps", 0.0)),
                "vibration_mm_s": float(row.get("vibration_mm_s", 0.0)),
                "temperature_celsius": float(row.get("temperature_celsius", 0.0)),
                "flow_rate_lpm": float(row.get("flow_rate_lpm", 0.0)),
                "pressure_psi": float(row.get("pressure_psi", 0.0)),
            },
            "signals": signals,
            "condition": self._derive_pump_condition(proxy_score),
            "condition_score": proxy_score,
        }

    def get_latest_tank_status_by_building(self, building_id: str) -> Dict[str, Any]:
        return self.get_tank_status_by_building(building_id=building_id, mode="latest")

    def get_tank_status_by_building(
        self,
        building_id: str,
        mode: str = "latest",  # latest | worst | at_time
        at_time: Optional[str] = None,
    ) -> Dict[str, Any]:
        df = self.load_tanks()

        if "building_id" not in df.columns:
            raise ValueError("water_tanks.csv must have 'building_id' column")

        sub = df[df["building_id"] == building_id].copy()

        if sub.empty:
            return {"status": "not_found", "building_id": building_id}

        if mode == "latest":
            # Moving-but-consistent latest mode:
            # - within the same 20s bucket, all tabs see same row
            # - across buckets, we advance through real CSV history
            sub = sub.sort_values("timestamp", ascending=False).reset_index(drop=True)
            building_key = f"{building_id}_latest"
            bucket = int(time.time() // 20)
            prev_bucket = self._latest_sequence_bucket.get(building_key)

            idx = self._latest_sequence_index.get(building_key, 0)
            if prev_bucket is None:
                # Start from most recent sample.
                idx = 0
            elif bucket != prev_bucket:
                idx = (idx + 1) % len(sub)

            self._latest_sequence_index[building_key] = idx
            self._latest_sequence_bucket[building_key] = bucket
            chosen = sub.iloc[idx].to_dict()
            return self._format_tank_status(building_id, chosen)

        if mode == "worst":
            sub_worst = sub[sub["level_percentage"] < 30]
            if sub_worst.empty:
                # No critical rows -> rotate through lowest-level rows.
                ranked = sub.sort_values(["level_percentage", "timestamp"], ascending=[True, False]).reset_index(drop=True)
                pool = ranked.head(min(20, len(ranked))).reset_index(drop=True)
                chosen = self._pick_rotating_row(sub=pool)
            else:
                # Rotate through worst-case rows. If too few rows, broaden pool slightly (<35%)
                # so the UI keeps moving while still showing severe levels.
                ranked = sub_worst.sort_values(["level_percentage", "timestamp"], ascending=[True, False]).reset_index(drop=True)
                if len(ranked) < 5:
                    broadened = sub[sub["level_percentage"] < 35].copy()
                    if not broadened.empty:
                        ranked = broadened.sort_values(["level_percentage", "timestamp"], ascending=[True, False]).reset_index(drop=True)
                pool = ranked.head(min(30, len(ranked))).reset_index(drop=True)
                chosen = self._pick_rotating_row(sub=pool)
            return self._format_tank_status(building_id, chosen)

        if mode == "at_time":
            if not at_time:
                return {
                    "status": "error",
                    "message": "mode='at_time' requires at_time param (ISO datetime string)",
                }

            t = pd.to_datetime(at_time)
            sub["time_diff"] = (sub["timestamp"] - t).abs()
            sub = sub.sort_values("time_diff")
            chosen = sub.iloc[0].to_dict()
            chosen.pop("time_diff", None)

            return self._format_tank_status(building_id, chosen)

        return {
            "status": "error",
            "message": f"Invalid mode: {mode}. Use latest | worst | at_time",
        }

    def get_pump_status_by_building(
        self,
        building_id: str,
        mode: str = "latest",  # latest | worst | at_time
        at_time: Optional[str] = None,
    ) -> Dict[str, Any]:
        df = self.load_pumps()

        sub = df[df["building_id"] == building_id].copy()
        if sub.empty:
            return {"status": "not_found", "building_id": building_id, "asset": "pump"}

        if mode == "latest":
            sub = sub.sort_values("timestamp", ascending=False)
            chosen = sub.iloc[0].to_dict()
            return self._format_pump_status(building_id, chosen)

        if mode == "worst":
            sub = sub.copy()
            sub["risk_proxy"] = sub.apply(lambda r: self._pump_risk_proxy(r.to_dict()), axis=1)
            ranked_all = sub.sort_values(["risk_proxy", "timestamp"], ascending=[False, False]).reset_index(drop=True)
            # Use >=2 so worst-case mode consistently surfaces abnormal pump telemetry.
            severe = ranked_all[ranked_all["risk_proxy"] >= 2].copy()
            if len(severe) >= 3:
                pool = severe.head(min(25, len(severe))).reset_index(drop=True)
            else:
                # If severe rows are sparse, rotate top risky rows to keep telemetry changing.
                pool = ranked_all.head(min(25, len(ranked_all))).reset_index(drop=True)
            chosen = self._pick_rotating_row(sub=pool)
            return self._format_pump_status(building_id, chosen)

        if mode == "at_time":
            if not at_time:
                return {
                    "status": "error",
                    "message": "mode='at_time' requires at_time param (ISO datetime string)",
                }
            t = pd.to_datetime(at_time)
            sub["time_diff"] = (sub["timestamp"] - t).abs()
            sub = sub.sort_values("time_diff")
            chosen = sub.iloc[0].to_dict()
            return self._format_pump_status(building_id, chosen)

        return {
            "status": "error",
            "message": f"Invalid mode: {mode}. Use latest | worst | at_time",
        }

    def get_system_state(
        self,
        building_id: str,
        mode: str = "latest",
        tank_mode: Optional[str] = None,
        pump_mode: Optional[str] = None,
        at_time: Optional[str] = None,
    ) -> Dict[str, Any]:
        resolved_tank_mode = tank_mode or mode
        resolved_pump_mode = pump_mode or mode

        tank_status = self.get_tank_status_by_building(
            building_id=building_id,
            mode=resolved_tank_mode,
            at_time=at_time,
        )
        pump_status = self.get_pump_status_by_building(
            building_id=building_id,
            mode=resolved_pump_mode,
            at_time=at_time,
        )

        now_iso = pd.Timestamp.utcnow().isoformat()
        return {
            "building_id": building_id,
            "mode": mode,
            "view_modes": {
                "tank": resolved_tank_mode,
                "pump": resolved_pump_mode,
            },
            "at_time": at_time,
            "timestamp": now_iso,
            "assets": {
                "water": {
                    "tank": tank_status,
                    "pump": pump_status,
                }
            },
            # Backward compatibility for current UI consumers.
            "tank_status": tank_status,
            "pump_status": pump_status,
        }
