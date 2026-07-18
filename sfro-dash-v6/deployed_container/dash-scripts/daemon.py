#!/usr/bin/env python3
import time
import os
import sys
import threading
import subprocess

try:
    import schedule
except ImportError:
    print("Error: 'schedule' package is not installed. Run 'pip install schedule'")
    sys.exit(1)

# Import the refactored modules
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.extend([
    os.path.join(ROOT_DIR, 'yr_forecast'),
    os.path.join(ROOT_DIR, 'Tempest'),
    os.path.join(ROOT_DIR, 'scope_forecast'),
    os.path.join(ROOT_DIR, 'scope_captures'),
    os.path.join(ROOT_DIR, 'currency_rates'),
    os.path.join(ROOT_DIR, 'apod'),
    os.path.join(ROOT_DIR, 'dashboard_controller')
])

try:
    import fetch_forecast
    import update_weather
    import fetch_forecasts
    import fetch_captures
    import fetch_rates
    import fetch_apod
    import fetch_roof
    import image_watcher
    import schema_engine
    import controller
except ImportError as e:
    print(f"Error importing modules: {e}")
    sys.exit(1)

APP_DIR = os.path.abspath(os.path.join(ROOT_DIR, "..", "app_data"))
AGENT_DIR = os.path.abspath(os.path.join(ROOT_DIR, "..", "data"))
IMAGES_DIR = os.path.abspath(os.path.join(ROOT_DIR, "..", "images"))
API_KEY = os.environ.get("TEMPEST_API_KEY", "") or getattr(update_weather, "DEFAULT_API_KEY", "")

def safe_run(func, *args, **kwargs):
    """Wrapper to catch exceptions and prevent the scheduler from crashing."""
    try:
        func(*args, **kwargs)
    except Exception as e:
        print(f"Error in {func.__name__}: {e}", file=sys.stderr)

# ---------------------------------------------------------
# Job Definitions
# ---------------------------------------------------------

def job_image_watcher():
    # Since image_watcher is not fully refactored, we can use subprocess for now
    try:
        script = os.path.join(ROOT_DIR, 'scope_captures', 'image_watcher.py')
        subprocess.run([sys.executable, script, "-o", APP_DIR, "--images-dir", IMAGES_DIR], check=False)
    except Exception as e:
        print(f"Error in job_image_watcher: {e}", file=sys.stderr)

def job_tempest():
    config = os.path.join(ROOT_DIR, "Tempest", "locations.json")
    safe_run(update_weather.fetch_weather, API_KEY, APP_DIR, config)

def job_roof():
    try:
        script = os.path.join(ROOT_DIR, 'scope_captures', 'fetch_roof.py')
        subprocess.run([sys.executable, script, "-o", APP_DIR], check=False)
    except Exception as e:
        print(f"Error in job_roof: {e}", file=sys.stderr)

def job_schema():
    safe_run(schema_engine.evaluate_schema, APP_DIR, AGENT_DIR, schema_engine.LAT, schema_engine.LON)

def job_controller():
    safe_run(controller.update_dashboard, APP_DIR, AGENT_DIR)

def job_weather_starfront():
    safe_run(fetch_forecast.fetch_forecast, lat=31.546944, lon=-99.382222, title="Observatory Forecast", subtitle="Starfront Observatory", timezone_str="America/Chicago", hours=8, out=os.path.join(APP_DIR, "forecast_starfront.json"))

def job_weather_wandsworth():
    safe_run(fetch_forecast.fetch_forecast, subtitle="London/Wandsworth", out=os.path.join(APP_DIR, "forecast_wandsworth.json"))

def job_apod():
    try:
        script = os.path.join(ROOT_DIR, 'apod', 'fetch_apod.py')
        apod_out = os.path.join(IMAGES_DIR, "apod.jpg")
        subprocess.run([sys.executable, script, "-o", apod_out], check=False)
    except Exception as e:
        print(f"Error in job_apod: {e}", file=sys.stderr)

def job_forecasts():
    safe_run(fetch_forecasts.fetch_forecasts, out_dir=APP_DIR)

def job_captures():
    try:
        script = os.path.join(ROOT_DIR, 'scope_captures', 'fetch_captures.py')
        subprocess.run([sys.executable, script, "-o", APP_DIR], check=False)
    except Exception as e:
        print(f"Error in job_captures: {e}", file=sys.stderr)

def job_rates():
    safe_run(fetch_rates.fetch_rates, out_dir=APP_DIR)

# ---------------------------------------------------------
# Main Execution
# ---------------------------------------------------------
def main():
    os.makedirs(APP_DIR, exist_ok=True)
    os.makedirs(AGENT_DIR, exist_ok=True)
    os.makedirs(IMAGES_DIR, exist_ok=True)
    
    print("Starting SFRO Dash V6 Daemon...")
    
    # Run initial sync
    print("Running initial jobs...")
    job_tempest()
    job_weather_starfront()
    job_weather_wandsworth()
    job_rates()
    job_forecasts()
    job_captures()
    job_roof()
    job_apod()
    job_image_watcher()
    
    # Evaluate schema and route immediately
    job_schema()
    job_controller()
    
    print("Initial sync complete. Starting schedules.")

    # High frequency jobs
    schedule.every(15).seconds.do(job_image_watcher)
    schedule.every(15).seconds.do(job_controller)
    schedule.every(1).minutes.do(job_tempest)
    schedule.every(1).minutes.do(job_roof)
    
    # Low frequency jobs
    schedule.every(15).minutes.do(job_schema)
    schedule.every(15).minutes.do(job_forecasts)
    schedule.every(15).minutes.do(job_captures)
    schedule.every(15).minutes.do(job_rates)
    
    # Low frequency API jobs
    schedule.every(30).minutes.do(job_weather_starfront)
    schedule.every(30).minutes.do(job_weather_wandsworth)
    schedule.every(12).hours.do(job_apod)

    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    main()
