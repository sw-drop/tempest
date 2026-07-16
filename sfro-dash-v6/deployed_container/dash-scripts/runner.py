#!/usr/bin/env python3
import time
import subprocess
import os
import sys
import json

# Resolve project root directory
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

def run_script(cmd):
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Running: {' '.join(cmd)}")
    try:
        # Run subprocess and print output
        result = subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.stdout:
            print(result.stdout.strip())
    except subprocess.CalledProcessError as e:
        print(f"[!] Error: Script execution failed with exit code {e.returncode}", file=sys.stderr)
        if e.stderr:
            print(e.stderr.strip(), file=sys.stderr)
    except Exception as e:
        print(f"Error running {' '.join(cmd)}: {e}", file=sys.stderr)

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Dashboard scheduler daemon loop.")
    parser.add_argument("-o", "--out-dir", default="data", help="Output directory for compiled JSONs")
    args = parser.parse_args()
    
    print("Dashboard scheduler daemon started.")
    
    # Resolve output directory relative to project root
    if not os.path.isabs(args.out_dir):
        project_root = os.path.dirname(ROOT_DIR)
        data_dir = os.path.abspath(os.path.join(project_root, args.out_dir))
    else:
        data_dir = os.path.abspath(args.out_dir)
    os.makedirs(data_dir, exist_ok=True)
    
    # Write default skycam.json if it does not exist (self-healing)
    skycam_path = os.path.join(data_dir, "skycam.json")
    if not os.path.exists(skycam_path) or os.path.getsize(skycam_path) == 0:
        default_skycam = {
            "title": "Live All-Sky Camera",
            "subtitle": "Connected (embedded)",
            "type": "image",
            "data": {
                "src": "https://files-api.tx.starfront.space/status-assets-public/building-0009/allsky/images/image.jpg",
                "alt": "Live All-Sky Camera"
            }
        }
        try:
            with open(skycam_path, "w", encoding="utf-8") as f:
                json.dump(default_skycam, f, indent=2)
            print(f"Created default skycam configuration at {skycam_path}")
        except Exception as e:
            print(f"Warning: Could not create default skycam config: {e}", file=sys.stderr)
    
    # Paths to scripts
    schema_engine_script = os.path.join(ROOT_DIR, "schema_engine.py")
    controller_script = os.path.join(ROOT_DIR, "dashboard_controller", "controller.py")
    weather_script = os.path.join(ROOT_DIR, "yr_forecast", "fetch_forecast.py")
    roof_script = os.path.join(ROOT_DIR, "scope_captures", "fetch_roof.py")
    image_watcher_script = os.path.join(ROOT_DIR, "scope_captures", "image_watcher.py")
    tempest_script = os.path.join(ROOT_DIR, "Tempest", "update_weather.py")
    apod_script = os.path.join(ROOT_DIR, "apod", "fetch_apod.py")
    
    # Run intervals (seconds)
    watcher_interval = 15     # 15 seconds
    tempest_interval = 60     # 1 minute
    roof_interval = 60        # 1 minute
    schema_interval = 900     # 15 minutes
    controller_interval = 15  # 15 seconds (routes rapidly based on schema)
    weather_interval = 7200   # 2 hours
    apod_interval = 43200     # 12 hours
    
    last_watcher_run = 0
    last_tempest_run = 0
    last_roof_run = 0
    last_schema_run = 0
    last_controller_run = 0
    last_weather_run = 0
    last_apod_run = 0
    
    while True:
        now = time.time()
        
        # 1. Run image watcher (FITS converter)
        if now - last_watcher_run >= watcher_interval:
            run_script([sys.executable, image_watcher_script, "-o", data_dir])
            last_watcher_run = now
            
        # 2. Run Tempest weather updater
        if now - last_tempest_run >= tempest_interval:
            run_script([sys.executable, tempest_script, "-o", data_dir])
            last_tempest_run = now
            
        # 3. Run roof status scraper
        if now - last_roof_run >= roof_interval:
            run_script([sys.executable, roof_script, "-o", data_dir])
            last_roof_run = now
            
        # 4. Run Schema Engine
        if now - last_schema_run >= schema_interval:
            run_script([sys.executable, schema_engine_script])
            last_schema_run = now
            
        # 5. Run active card controller (router)
        if now - last_controller_run >= controller_interval:
            run_script([sys.executable, controller_script, "-o", data_dir])
            last_controller_run = now
            
        # 6. Run weather forecast compiler
        if now - last_weather_run >= weather_interval:
            run_script([sys.executable, weather_script, "-o", os.path.join(data_dir, "forecast.json")])
            last_weather_run = now
            
        # 7. Fetch NASA APOD (runs every 12 hours)
        if now - last_apod_run >= apod_interval:
            run_script([sys.executable, apod_script, "-o", os.path.join(data_dir, "..", "images", "apod.jpg")])
            last_apod_run = now
            
        time.sleep(5)

if __name__ == "__main__":
    main()
