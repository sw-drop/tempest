import logging
import sys
import os
import time
import threading

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import Config
from app.collector import TempestCollector
from app.mqtt import TempestMqttPublisher
from app.reports import ReportsDaemon
from app.image_watcher import ImageWatcher

# Configure logs to stdout
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("tempest_daemon_main")

def run_collector(collector):
    while True:
        try:
            collector.run_once()
        except Exception as e:
            logger.error(f"Error in collector loop: {e}", exc_info=True)
        time.sleep(collector.config.POLL_INTERVAL_SECONDS)

def run_reports(reports):
    while True:
        try:
            reports.run_once()
        except Exception as e:
            logger.error(f"Error in reports loop: {e}", exc_info=True)
        time.sleep(300) # Poll Discord/observatory schedules every 5 minutes

def run_image_watcher(watcher):
    while True:
        try:
            watcher.run_once()
        except Exception as e:
            logger.error(f"Error in image watcher loop: {e}", exc_info=True)
        time.sleep(10) # Scan directories for new FITS files every 10 seconds

def main():
    logger.info("Initializing Starfront Dashboard v3 Asynchronous Daemon...")
    config = Config()
    
    # 1. Start MQTT Publisher
    mqtt_publisher = TempestMqttPublisher(config)
    mqtt_publisher.connect()
    
    def on_weather_update(data):
        mqtt_publisher.publish(data)

    # 2. Setup Daemons
    collector = TempestCollector(config, on_update_callbacks=[on_weather_update])
    reports = ReportsDaemon(config)
    image_watcher = ImageWatcher(config)
    
    collector.start()
    reports.start()
    image_watcher.start()

    # 3. Spin up concurrent threads
    collector_thread = threading.Thread(target=run_collector, args=(collector,), name="CollectorThread", daemon=True)
    reports_thread = threading.Thread(target=run_reports, args=(reports,), name="ReportsThread", daemon=True)
    watcher_thread = threading.Thread(target=run_image_watcher, args=(image_watcher,), name="WatcherThread", daemon=True)
    
    collector_thread.start()
    reports_thread.start()
    watcher_thread.start()

    logger.info("All background threads successfully spawned.")
    
    # Keep the main process alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutdown requested.")
    finally:
        logger.info("Stopping MQTT services...")
        mqtt_publisher.stop()
        logger.info("Daemon exited.")

if __name__ == "__main__":
    main()
