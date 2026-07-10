import json
import logging
import paho.mqtt.client as mqtt

logger = logging.getLogger("tempest_mqtt")

class TempestMqttPublisher:
    def __init__(self, config):
        self.config = config
        self.client = None
        self.connected = False

    def connect(self):
        if not self.config.MQTT_BROKER_HOST:
            logger.info("MQTT publisher disabled (no broker host configured).")
            return

        try:
            # Handle paho-mqtt v2.0+ deprecations gracefully by checking if CallbackAPIVersion exists
            try:
                from paho.mqtt.enums import CallbackAPIVersion
                self.client = mqtt.Client(callback_api_version=CallbackAPIVersion.VERSION2, client_id="tempest_script_host")
            except (ImportError, AttributeError):
                # Fallback for paho-mqtt v1.x
                self.client = mqtt.Client(client_id="tempest_script_host")

            if self.config.MQTT_USERNAME and self.config.MQTT_PASSWORD:
                self.client.username_pw_set(self.config.MQTT_USERNAME, self.config.MQTT_PASSWORD)

            self.client.on_connect = self._on_connect
            self.client.on_disconnect = self._on_disconnect

            logger.info(f"Connecting to MQTT broker at {self.config.MQTT_BROKER_HOST}:{self.config.MQTT_BROKER_PORT}...")
            self.client.connect(self.config.MQTT_BROKER_HOST, self.config.MQTT_BROKER_PORT, keepalive=60)
            self.client.loop_start()
        except Exception as e:
            logger.error(f"Failed to connect to MQTT broker: {e}", exc_info=True)

    def _on_connect(self, client, userdata, flags, rc, properties=None):
        rc_code = rc.value if hasattr(rc, "value") else rc
        if rc_code == 0:
            self.connected = True
            logger.info("Successfully connected to MQTT broker.")
        else:
            logger.error(f"MQTT connection refused with code: {rc_code}")

    def _on_disconnect(self, client, userdata, rc, properties=None):
        self.connected = False
        logger.warning(f"Disconnected from MQTT broker (code: {rc})")

    def publish(self, data):
        if not self.client or not self.connected:
            return

        try:
            payload = {
                "station_id": data.get("station_id"),
                "station_name": data.get("station_name"),
                "last_fetched": data.get("last_fetched"),
                "processed": data.get("processed"),
                "roof_status": data.get("roof_status")
            }
            payload_str = json.dumps(payload)
            
            logger.info(f"Publishing observation payload to topic: {self.config.MQTT_TOPIC}")
            info = self.client.publish(self.config.MQTT_TOPIC, payload_str, qos=1, retain=True)
            info.wait_for_publish(timeout=2)
        except Exception as e:
            logger.error(f"Failed to publish MQTT message: {e}", exc_info=True)

    def stop(self):
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()
            logger.info("MQTT client stopped.")
