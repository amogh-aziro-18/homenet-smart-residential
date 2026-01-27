import os
import json
from datetime import datetime, timezone
import pandas as pd
from prophet import Prophet
import joblib


DATA_PATH = "data/samples/water_consumption.csv"
ARTIFACT_DIR = "models/demand_forecast/artifacts"


def _find_timestamp_column(df: pd.DataFrame) -> str:
    candidates = ["timestamp", "time", "datetime", "date_time", "created_at"]
    for c in candidates:
        if c in df.columns:
            return c
    for c in df.columns:
        if "time" in c.lower() or "date" in c.lower():
            return c
    raise ValueError(f"Timestamp column not found in columns: {list(df.columns)}")


def _find_target_column(df: pd.DataFrame) -> str:
    candidates = [
        "consumption_liters",
        "water_consumption_liters",
        "consumption",
        "liters_used",
        "usage_liters",
        "usage",
        "demand_liters"
    ]
    for c in candidates:
        if c in df.columns:
            return c

    flow_candidates = ["flow_rate", "flow_rate_lpm", "flow_lpm"]
    for c in flow_candidates:
        if c in df.columns:
            return c

    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    if numeric_cols:
        return numeric_cols[0]

    raise ValueError(f"No numeric target column found in columns: {list(df.columns)}")


def _find_group_column(df: pd.DataFrame) -> str | None:
    candidates = ["building_id", "tower_id", "block_id", "asset_id", "site_id"]
    for c in candidates:
        if c in df.columns:
            return c
    return None


def _prepare_prophet_df(df: pd.DataFrame, ts_col: str, y_col: str) -> pd.DataFrame:
    out = df[[ts_col, y_col]].copy()
    out.columns = ["ds", "y"]
    out["ds"] = pd.to_datetime(out["ds"], errors="coerce")
    out["y"] = pd.to_numeric(out["y"], errors="coerce")

    out = out.dropna(subset=["ds", "y"])
    out = out.sort_values("ds")

    return out


def train_all_models(
    data_path: str = DATA_PATH,
    artifact_dir: str = ARTIFACT_DIR,
    freq: str = "h"
) -> None:
    os.makedirs(artifact_dir, exist_ok=True)

    print("=" * 60)
    print("DEMAND FORECAST MODEL TRAINING (WATER CONSUMPTION)")
    print("=" * 60)

    print("\n📊 Loading consumption data...")
    df = pd.read_csv(data_path)
    print(f"   Loaded {len(df)} rows")

    ts_col = _find_timestamp_column(df)
    y_col = _find_target_column(df)
    group_col = _find_group_column(df)

    print("\n🔎 Detected columns:")
    print(f"   Timestamp column : {ts_col}")
    print(f"   Target column    : {y_col}")
    print(f"   Group column     : {group_col if group_col else 'None (global model)'}")

    df[ts_col] = pd.to_datetime(df[ts_col], errors="coerce")
    df = df.dropna(subset=[ts_col])
    df = df.sort_values(ts_col)

    metadata = {
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "data_path": data_path,
        "timestamp_col": ts_col,
        "target_col": y_col,
        "group_col": group_col,
        "freq": freq,
        "models": []
    }

    if group_col:
        groups = df[group_col].unique().tolist()
        print(f"\n✅ Training Prophet models per {group_col}: {len(groups)} groups")

        for g in groups:
            sub = df[df[group_col] == g].copy()

            sub = sub.set_index(ts_col)
            sub = sub[[y_col]].resample(freq).sum().reset_index()

            prophet_df = _prepare_prophet_df(sub, ts_col, y_col)

            if len(prophet_df) < 24:
                print(f"⚠️ Skipping {g}: not enough points ({len(prophet_df)})")
                continue

            model = Prophet(
                daily_seasonality=True,
                weekly_seasonality=True,
                yearly_seasonality=False
            )
            model.fit(prophet_df)

            model_path = os.path.join(artifact_dir, f"prophet_{group_col}_{g}.pkl")
            joblib.dump(model, model_path)

            metadata["models"].append(
                {"group_value": str(g), "model_path": model_path, "n_rows": len(prophet_df)}
            )

            print(f"   ✅ Saved model for {g} -> {model_path}")

    else:
        print("\n✅ Training single global Prophet model (no group column found)")

        tmp = df.set_index(ts_col)[[y_col]].resample(freq).sum().reset_index()
        prophet_df = _prepare_prophet_df(tmp, ts_col, y_col)

        if len(prophet_df) < 24:
            raise ValueError(f"Not enough data points to train: {len(prophet_df)}")

        model = Prophet(
            daily_seasonality=True,
            weekly_seasonality=True,
            yearly_seasonality=False
        )
        model.fit(prophet_df)

        model_path = os.path.join(artifact_dir, "prophet_global.pkl")
        joblib.dump(model, model_path)

        metadata["models"].append(
            {"group_value": "GLOBAL", "model_path": model_path, "n_rows": len(prophet_df)}
        )

        print(f"   ✅ Saved global model -> {model_path}")

    meta_path = os.path.join(artifact_dir, "metadata.json")
    with open(meta_path, "w") as f:
        json.dump(metadata, f, indent=2)

    print("\n💾 Metadata saved:", meta_path)
    print("\n✅ TRAINING COMPLETE!")
    print("=" * 60)


if __name__ == "__main__":
    train_all_models()
