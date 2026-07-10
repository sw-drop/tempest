import logging
import sys
from app.config import Config
from app.collector import TempestCollector
from app.mqtt import TempestMqttPublisher
from app.api import app

# Set up logging to stdout
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("tempest_main")

def main():
    logger.info("Starting Tempest Weather Station Daemon...")
    
    # 1. Initialize configurations
    config = Config()
    logger.info(f"Station ID: {config.TEMPEST_STATION_ID}")
    logger.info(f"Poll Interval: {config.POLL_INTERVAL_SECONDS}s")
    
    # 2. Setup MQTT publisher
    mqtt_publisher = TempestMqttPublisher(config)
    mqtt_publisher.connect()
    
    # Callback to trigger MQTT publish whenever collector updates
    def on_weather_update(data):
        mqtt_publisher.publish(data)
        
    # 3. Setup Collector
    collector = TempestCollector(config, on_update_callbacks=[on_weather_update])
    collector.start()
    
    # 4. Start HTTP REST API server
    try:
        logger.info(f"Starting API Server on {config.API_HOST}:{config.API_PORT}...")
        # debug=False, threaded=True to run concurrently
        app.run(host=config.API_HOST, port=config.API_PORT, debug=False, threaded=True)
    except KeyboardInterrupt:
        logger.info("Shutdown requested.")
    finally:
        logger.info("Stopping services...")
        collector.stop()
        mqtt_publisher.stop()
        logger.info("Daemon exited.")

if __name__ == "__main__":
    main()
