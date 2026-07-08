import time
import logging
import os
import glob
import subprocess
import io
import threading
from flask import Flask, jsonify, send_file, Response
from app.collector import weather_state, fetch_now_event
from app.config import Config

app = Flask(__name__)
config = Config()
logger = logging.getLogger("tempest_api")

@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, X-Original-Filename"
    response.headers["Access-Control-Expose-Headers"] = "X-Original-Filename"
    return response

def _get_fresh_data():
    weather_state.record_request()
    data, last_update = weather_state.get_data()
    current_time = time.time()
    
    is_missing = data is None
    is_stale = (current_time - last_update) >= config.POLL_INTERVAL_SECONDS
    
    if is_missing or is_stale:
        fetch_now_event.set()
        start_wait = time.time()
        while time.time() - start_wait < 2.5:
            time.sleep(0.1)
            data, last_update = weather_state.get_data()
            if data is not None and (time.time() - last_update) < config.POLL_INTERVAL_SECONDS:
                break
    return data

@app.route("/api/observations", methods=["GET"])
def get_observations():
    data = _get_fresh_data()
    if data is None:
        return jsonify({"status": "error", "message": "Collector is working..."}), 503
    return jsonify(data)

@app.route("/api/summary", methods=["GET"])
def get_summary():
    data = _get_fresh_data()
    if data is None:
        return jsonify({"status": "error", "message": "Collector is working..."}), 503
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

# --- FITS IMAGE ENDPOINT ---
def _convert_fits_to_jpeg(fits_path):
    try:
        from astropy.io import fits
        from PIL import Image
        import numpy as np
    except ImportError:
        logger.error("Missing astropy, PIL, or numpy")
        return None

    try:
        with fits.open(fits_path) as hdul:
            data = hdul[0].data
            if data is None and len(hdul) > 1:
                data = hdul[1].data
            if data is None:
                return None

            p_lo = np.percentile(data, 5)
            p_hi = np.percentile(data, 99.5)
            if p_hi == p_lo:
                p_hi = p_lo + 1
            data = np.clip(data, p_lo, p_hi)
            data = (data - p_lo) / (p_hi - p_lo)
            data = (data * 255).astype(np.uint8)
            
            if data.ndim == 3 and data.shape[0] == 3: 
                data = np.moveaxis(data, 0, -1)
            
            img = Image.fromarray(data)
            img_io = io.BytesIO()
            img.save(img_io, 'JPEG', quality=85)
            img_io.seek(0)
            return img_io
    except Exception as e:
        logger.error(f"Failed to convert FITS: {e}")
        return None

@app.route("/api/latest-image/<scope>", methods=["GET"])
def get_latest_image(scope):
    import pathlib
    
    # Mapping for scope directory
    scope_dir_map = {
        "fra400": "FRA400",
        "75q": "75Q"
    }
    safe_scope = scope.lower()
    if safe_scope not in scope_dir_map:
        return "Invalid scope", 400
        
    img_dir = f"/app/images/{scope_dir_map[safe_scope]}"
    
    # FOR LOCAL TESTING: If /app/images doesn't exist, try local dir
    if not os.path.exists(img_dir):
        img_dir = "."
        
    p = pathlib.Path(img_dir)
    fits_files = list(p.rglob("*.fit*"))
    fits_files = [str(f) for f in fits_files if f.is_file()]
    
    # For local test prototype (if testing outside Docker)
    if not fits_files and img_dir == ".":
        fits_files = [str(f) for f in p.rglob(f"*{scope_dir_map[safe_scope]}*.fit*") if f.is_file()]

    if not fits_files:
        # Fallback to local jpeg if it exists (from our quick conversion test)
        fallback_jpg = f"{scope_dir_map[safe_scope]}.jpg"
        if os.path.exists(fallback_jpg):
            resp = send_file(fallback_jpg, mimetype='image/jpeg')
            resp.headers["X-Original-Filename"] = fallback_jpg
            return resp
        return "No images found", 404

    # Get latest by modification time
    latest_file = max(fits_files, key=os.path.getmtime)
    
    img_io = _convert_fits_to_jpeg(latest_file)
    if not img_io:
        return "Error processing image", 500
        
    # Remove the extension cleanly
    filename = os.path.splitext(os.path.basename(latest_file))[0]
    resp = send_file(img_io, mimetype='image/jpeg')
    resp.headers["X-Original-Filename"] = filename
    return resp

# --- REPORTS ENDPOINT ---
# Cache for report outputs
report_cache = {
    "capture": {"data": None, "time": 0},
    "forecast": {"data": None, "time": 0}
}
CACHE_TTL = 300 # 5 minutes
cache_lock = threading.Lock()

def _run_script(script_name):
    # Depending on where we run, it might be in current dir (local test) or /app (Docker)
    path = f"./{script_name}"
    if not os.path.exists(path) and os.path.exists(f"/app/{script_name}"):
        path = f"/app/{script_name}"
        
    try:
        res = subprocess.run(["python3", path], capture_output=True, text=True, timeout=15)
        return res.stdout
    except Exception as e:
        logger.error(f"Failed to run {script_name}: {e}")
        return f"Error running script: {e}"

@app.route("/api/reports", methods=["GET"])
def get_reports():
    global report_cache
    current_time = time.time()
    
    with cache_lock:
        if current_time - report_cache["capture"]["time"] > CACHE_TTL:
            out = _run_script("report_capture.py")
            report_cache["capture"]["data"] = out
            report_cache["capture"]["time"] = current_time
            
        if current_time - report_cache["forecast"]["time"] > CACHE_TTL:
            out = _run_script("report_forecast.py")
            report_cache["forecast"]["data"] = out
            report_cache["forecast"]["time"] = current_time
            
    return jsonify({
        "capture": report_cache["capture"]["data"],
        "forecast": report_cache["forecast"]["data"]
    })

@app.route("/healthz", methods=["GET"])
def healthz():
    data, _ = weather_state.get_data()
    return jsonify({
        "status": "healthy" if data is not None else "degraded",
        "has_data": data is not None
    }), 200 if data is not None else 503
