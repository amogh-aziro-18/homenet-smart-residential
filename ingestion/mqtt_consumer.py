"""
MQTT Consumer - Real-time sensor data ingestion
Consumes IoT sensor data from MQTT broker and triggers agents
"""
import json
import logging
from datetime import datetime
from typing import Callable, Optional
import sys
import os

# Add parent directory to path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    import paho.mqtt.client as mqtt
    MQTT_AVAILABLE = True
except ImportError:
    logger.warning("paho-mqtt not installed. Run: pip install paho-mqtt")
    MQTT_AVAILABLE = False


class MQTTSensorConsumer:
    """
    MQTT Consumer for HOMENET sensor data
    """
    
    def __init__(self, 
                 broker_url: str = "localhost",
                 port: int = 1883,
                 username: Optional[str] = None,
                 password: Optional[str] = None,
                 callback: Optional[Callable] = None):
        """
        Initialize MQTT consumer
        
        Args:
            broker_url: MQTT broker address
            port: MQTT broker port
            username: Optional authentication username
            password: Optional authentication password
            callback: Optional function to call when message received
        """
        self.broker_url = broker_url
        self.port = port
        self.username = username
        self.password = password
        self.callback = callback
        self.client = None
        self.connected = False
        
        if not MQTT_AVAILABLE:
            logger.error("MQTT not available - install paho-mqtt")
            return
        
        # Initialize MQTT client
        self.client = mqtt.Client(client_id=f"homenet_consumer_{datetime.now().timestamp()}")
        
        # Set authentication if provided
        if username and password:
            self.client.username_pw_set(username, password)
        
        # Set callbacks
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message
    
    def _on_connect(self, client, userdata, flags, rc):
        """Callback when connected to MQTT broker"""
        if rc == 0:
            self.connected = True
            logger.info(f"✅ Connected to MQTT broker: {self.broker_url}:{self.port}")
        else:
            logger.error(f"❌ Connection failed with code: {rc}")
    
    def _on_disconnect(self, client, userdata, rc):
        """Callback when disconnected from MQTT broker"""
        self.connected = False
        if rc != 0:
            logger.warning(f"⚠️ Unexpected disconnection. Code: {rc}")
    
    def _on_message(self, client, userdata, msg):
        """Callback when message received"""
        try:
            # Parse message
            payload = msg.payload.decode('utf-8')
            topic = msg.topic
            
            logger.info(f"📨 Received message on topic: {topic}")
            
            # Parse JSON payload
            data = parse_mqtt_message(payload)
            
            if not data:
                logger.warning(f"⚠️ Failed to parse message: {payload}")
                return
            
            # Add metadata
            data['received_at'] = datetime.now().isoformat()
            data['topic'] = topic
            
            # Log parsed data
            logger.info(f"📊 Parsed data: {json.dumps(data, indent=2)}")
            
            # Call custom callback if provided
            if self.callback:
                self.callback(data)
            
            # Store to file (POC - in production, store to DB)
            self._store_data(data)
            
            # Check for critical alerts and trigger agents
            self._check_critical_alerts(data)
            
        except Exception as e:
            logger.error(f"❌ Error processing message: {e}")
    
    def _store_data(self, data: dict):
        """Store sensor data to file (POC placeholder)"""
        try:
            # Create data directory if not exists
            os.makedirs("data/realtime", exist_ok=True)
            
            # Append to daily log file
            date_str = datetime.now().strftime("%Y%m%d")
            filename = f"data/realtime/sensors_{date_str}.jsonl"
            
            with open(filename, "a") as f:
                f.write(json.dumps(data) + "\n")
            
            logger.debug(f"💾 Data stored to: {filename}")
            
        except Exception as e:
            logger.error(f"❌ Error storing data: {e}")
    
    def _check_critical_alerts(self, data: dict):
        """Check if data triggers critical alerts"""
        try:
            sensor_type = data.get("sensor_type", "")
            value = data.get("value", 0)
            asset_id = data.get("asset_id", "")
            
            # Critical thresholds
            if sensor_type == "vibration" and value > 8.0:
                logger.critical(f"🚨 CRITICAL: High vibration on {asset_id}: {value}")
                self._trigger_agent_alert(asset_id, "vibration", "CRITICAL", value)
                
            elif sensor_type == "temperature" and value > 85:
                logger.critical(f"🚨 CRITICAL: High temperature on {asset_id}: {value}°C")
                self._trigger_agent_alert(asset_id, "temperature", "CRITICAL", value)
                
            elif sensor_type == "water_level" and value < 10:
                logger.warning(f"⚠️ WARNING: Low water level on {asset_id}: {value}%")
                self._trigger_agent_alert(asset_id, "water_level", "HIGH", value)
                
        except Exception as e:
            logger.error(f"❌ Error checking alerts: {e}")
    
    def _trigger_agent_alert(self, asset_id: str, alert_type: str, severity: str, value: float):
        """Trigger agent workflow on critical alert"""
        try:
            logger.info(f"🤖 Triggering agents for {asset_id} - {alert_type} alert")
            
            # In production, this would call the LangGraph workflow
            # For now, just log the alert
            alert = {
                "timestamp": datetime.now().isoformat(),
                "asset_id": asset_id,
                "alert_type": alert_type,
                "severity": severity,
                "value": value,
                "triggered_agents": True
            }
            
            # Store alert
            os.makedirs("data/alerts", exist_ok=True)
            with open("data/alerts/critical_alerts.jsonl", "a") as f:
                f.write(json.dumps(alert) + "\n")
            
        except Exception as e:
            logger.error(f"❌ Error triggering agents: {e}")
    
    def connect(self):
        """Connect to MQTT broker"""
        if not MQTT_AVAILABLE:
            logger.error("❌ MQTT not available")
            return False
        
        try:
            logger.info(f"🔌 Connecting to {self.broker_url}:{self.port}...")
            self.client.connect(self.broker_url, self.port, keepalive=60)
            return True
        except Exception as e:
            logger.error(f"❌ Connection failed: {e}")
            return False
    
    def subscribe(self, topic: str):
        """Subscribe to MQTT topic"""
        if not self.connected:
            logger.error("❌ Not connected to broker")
            return False
        
        try:
            self.client.subscribe(topic)
            logger.info(f"📡 Subscribed to topic: {topic}")
            return True
        except Exception as e:
            logger.error(f"❌ Subscription failed: {e}")
            return False
    
    def start(self, topics: list[str]):
        """Start consuming messages"""
        if not MQTT_AVAILABLE:
            logger.error("❌ MQTT not available")
            return
        
        # Connect to broker
        if not self.connect():
            return
        
        # Subscribe to topics
        for topic in topics:
            self.subscribe(topic)
        
        # Start listening loop
        logger.info("🎧 Starting MQTT consumer loop...")
        try:
            self.client.loop_forever()
        except KeyboardInterrupt:
            logger.info("⏹️ Stopping consumer...")
            self.stop()
    
    def stop(self):
        """Stop consumer and disconnect"""
        if self.client:
            self.client.disconnect()
            logger.info("✅ Consumer stopped")


def parse_mqtt_message(payload: str) -> dict:
    """
    Convert MQTT payload into structured sensor record
    
    Args:
        payload: JSON string from MQTT message
        
    Returns:
        Parsed sensor data dictionary
    """
    try:
        # Parse JSON
        data = json.loads(payload)
        
        # Validate required fields
        required_fields = ["asset_id", "sensor_type", "value", "timestamp"]
        if not all(field in data for field in required_fields):
            logger.warning(f"⚠️ Missing required fields in message")
            return {}
        
        # Return structured data
        return {
            "asset_id": data.get("asset_id"),
            "sensor_type": data.get("sensor_type"),
            "value": float(data.get("value", 0)),
            "timestamp": data.get("timestamp"),
            "unit": data.get("unit", ""),
            "building_id": data.get("building_id", ""),
            "site_id": data.get("site_id", "SITE_001"),
            "metadata": data.get("metadata", {})
        }
        
    except json.JSONDecodeError as e:
        logger.error(f"❌ Invalid JSON: {e}")
        return {}
    except Exception as e:
        logger.error(f"❌ Error parsing message: {e}")
        return {}


def start_mqtt_consumer(broker_url: str = "localhost",
                       port: int = 1883,
                       topics: list[str] = None,
                       callback: Optional[Callable] = None) -> None:
    """
    Start MQTT consumer with specified configuration
    
    Args:
        broker_url: MQTT broker address
        port: MQTT broker port  
        topics: List of topics to subscribe to
        callback: Optional callback function for messages
    """
    if topics is None:
        topics = [
            "homenet/sensors/#",  # All sensors
            "homenet/pumps/#",    # All pump data
            "homenet/tanks/#",    # All tank data
            "homenet/alerts/#"    # All alerts
        ]
    
    consumer = MQTTSensorConsumer(
        broker_url=broker_url,
        port=port,
        callback=callback
    )
    
    consumer.start(topics)


if __name__ == "__main__":
    """Test MQTT consumer"""
    print("="*70)
    print("🎧 HOMENET MQTT CONSUMER")
    print("="*70)
    
    # Example usage
    print("\n📋 Configuration:")
    print("  Broker: localhost:1883")
    print("  Topics: homenet/sensors/#, homenet/pumps/#")
    
    print("\n⚠️ Make sure MQTT broker is running!")
    print("  Install: pip install paho-mqtt")
    print("  Broker: mosquitto (or use test.mosquitto.org)")
    
    # Start consumer
    try:
        start_mqtt_consumer(
            broker_url="localhost",
            port=1883,
            topics=["homenet/#"]
        )
    except KeyboardInterrupt:
        print("\n✅ Consumer stopped by user")

