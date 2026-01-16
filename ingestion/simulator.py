def generate_water_sensor_data(site_id: str, asset_id: str, n_rows: int = 100) -> list[dict]:
    """
    Generate synthetic sensor readings for water system assets.
    Example signals: water_level, flow_rate, vibration, motor_current.
    """
    return []


def save_sensor_data_csv(rows: list[dict], out_path: str) -> str:
    """
    Save generated sensor data into CSV.
    """
    return out_path
