import os

class Config:
    TEMPEST_STATION_ID = int(os.environ.get("TEMPEST_STATION_ID", "174867"))
    TEMPEST_API_KEY = os.environ.get("TEMPEST_API_KEY", "6bff2f89-84ab-463c-886e-fc0f443da4cf")
    POLL_INTERVAL_SECONDS = int(os.environ.get("POLL_INTERVAL_SECONDS", "60"))
    
    MQTT_BROKER_HOST = os.environ.get("MQTT_BROKER_HOST", "").strip()
    MQTT_BROKER_PORT = int(os.environ.get("MQTT_BROKER_PORT", "1883"))
    MQTT_TOPIC = os.environ.get("MQTT_TOPIC", "tempest/observations")
    MQTT_USERNAME = os.environ.get("MQTT_USERNAME", "").strip()
    MQTT_PASSWORD = os.environ.get("MQTT_PASSWORD", "").strip()
    
    API_PORT = int(os.environ.get("API_PORT", "8000"))
    API_HOST = os.environ.get("API_HOST", "127.0.0.1")  # Listen locally, proxied by Nginx
