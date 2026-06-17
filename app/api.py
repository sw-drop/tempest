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

def _get_fresh_data():
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
    return data

@app.route("/api/observations", methods=["GET"])
def get_observations():
    data = _get_fresh_data()
    if data is None:
        return jsonify({
            "status": "error",
            "message": "Observations not fetched yet. Collector is working..."
        }), 503
    return jsonify(data)

@app.route("/api/summary", methods=["GET"])
def get_summary():
    data = _get_fresh_data()
    if data is None:
        return jsonify({
            "status": "error",
            "message": "Observations not fetched yet. Collector is working..."
        }), 503
        
    processed = data.get("processed", {})
    metrics = processed.get("metrics", {})
    roof_status = data.get("roof_status", {})
    
    summary = {
        "temp_c": metrics.get("temp_c"),
        "temp_f": metrics.get("temp_f"),
        "humidity": metrics.get("humidity"),
        "wind_avg_mps": metrics.get("wind_avg_mps"),
        "wind_avg_mph": metrics.get("wind_avg_mph"),
        "wind_gust_mps": metrics.get("wind_gust_mps"),
        "wind_gust_mph": metrics.get("wind_gust_mph"),
        "dew_point_margin_c": metrics.get("dew_point_margin_c"),
        "dew_point_margin_f": metrics.get("dew_point_margin_f"),
        "roof_allowed": roof_status.get("allowed"),
        "roof_reasons": roof_status.get("reasons", []),
        "physical_roof_status": data.get("physical_roof_status", "Unknown")
    }
    return jsonify(summary)

@app.route("/api/text", methods=["GET"])
def get_text():
    data = _get_fresh_data()
    if data is None:
        return "Error: Observations not fetched yet.", 503
        
    processed = data.get("processed", {})
    metrics = processed.get("metrics", {})
    roof_status = data.get("roof_status", {})
    
    reasons_str = ", ".join(roof_status.get("reasons", [])) if roof_status.get("reasons") else "None"
    allowed_str = "Yes" if roof_status.get("allowed") else f"No (Reasons: {reasons_str})"
    
    lines = [
        f"Temperature: {metrics.get('temp_f')} °F ({metrics.get('temp_c')} °C)",
        f"Humidity: {metrics.get('humidity')}%",
        f"Wind Speed: {metrics.get('wind_avg_mph')} mph ({metrics.get('wind_avg_mps')} m/s)",
        f"Wind Gust: {metrics.get('wind_gust_mph')} mph ({metrics.get('wind_gust_mps')} m/s)",
        f"Dew Point Margin: {metrics.get('dew_point_margin_f')} °F ({metrics.get('dew_point_margin_c')} °C)",
        f"Roof Allowed: {allowed_str}",
        f"Physical Roof Status: {data.get('physical_roof_status', 'Unknown')}"
    ]
    return "\n".join(lines), 200, {"Content-Type": "text/plain; charset=utf-8"}

@app.route("/healthz", methods=["GET"])
def healthz():
    data, _ = weather_state.get_data()
    status_code = 200 if data is not None else 503
    return jsonify({
        "status": "healthy" if data is not None else "degraded",
        "has_data": data is not None
    }), status_code
