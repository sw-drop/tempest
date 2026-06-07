import time
import logging
from flask import Flask, jsonify
from app.collector import weather_state, fetch_now_event
from app.config import Config

app = Flask(__name__)
config = Config()
logger = logging.getLogger("tempest_api")

@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response

@app.route("/api/observations", methods=["GET"])
def get_observations():
    # 1. Update the client request timestamp to show someone has the dashboard open
    weather_state.record_request()
    
    # 2. Get current state
    data, last_update = weather_state.get_data()
    current_time = time.time()
    
    is_missing = data is None
    is_stale = (current_time - last_update) >= config.POLL_INTERVAL_SECONDS
    
    if is_missing or is_stale:
        logger.info("Data is missing or stale. Triggering immediate collector fetch...")
        fetch_now_event.set()
        
        # Block client request briefly (up to 2.5s) to wait for fresh data
        start_wait = time.time()
        while time.time() - start_wait < 2.5:
            time.sleep(0.1)
            data, last_update = weather_state.get_data()
            if data is not None and (time.time() - last_update) < config.POLL_INTERVAL_SECONDS:
                logger.info("Fresh data fetched successfully during wait window.")
                break

    if data is None:
        return jsonify({
            "status": "error",
            "message": "Observations not fetched yet. Collector is working..."
        }), 503
        
    return jsonify(data)

@app.route("/healthz", methods=["GET"])
def healthz():
    data, _ = weather_state.get_data()
    status_code = 200 if data is not None else 503
    return jsonify({
        "status": "healthy" if data is not None else "degraded",
        "has_data": data is not None
    }), status_code
