def start_mqtt_consumer(broker_url: str, topic: str) -> None:
    """
    Consume sensor data from MQTT and store into DB / files (POC placeholder).
    """
    pass


def parse_mqtt_message(payload: bytes) -> dict:
    """
    Convert MQTT payload into structured sensor record.
    """
    return {}
