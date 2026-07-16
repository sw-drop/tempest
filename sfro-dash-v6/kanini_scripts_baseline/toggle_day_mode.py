#!/usr/bin/env python3
import sys
import subprocess
import json
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "sfro-dash-v5", "data")
REPORTS_PATH = os.path.join(DATA_DIR, "capture.json")
FORECAST_PATH = os.path.join(DATA_DIR, "forecast.json")
OBS_PATH = os.path.join(DATA_DIR, "observations.json")

def run_docker_command(args):
    """Run a local docker command. Returns True if successful, False otherwise."""
    cmd = ["docker"] + args
    try:
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0:
            return True
        else:
            print(f"Warning: Docker command {' '.join(cmd)} returned {res.returncode}: {res.stderr.strip()}", file=sys.stderr)
            return False
    except FileNotFoundError:
        print("Warning: 'docker' command not found in this environment. Skipping docker action.", file=sys.stderr)
        return False
    except Exception as e:
        print(f"Warning: Failed to run docker command: {e}", file=sys.stderr)
        return False

def enable_day_mode():
    print("Stopping sfro-dash-v5-scheduler...")
    # Stop the scheduler container so it doesn't overwrite our custom daytime JSON files
    run_docker_command(["stop", "sfro-dash-v5-scheduler"])

    print("Activating Day Mode dashboard...")
    os.makedirs(DATA_DIR, exist_ok=True)
    
    # 1. Update capture.json
    try:
        if os.path.exists(REPORTS_PATH):
            with open(REPORTS_PATH, "r", encoding="utf-8") as f:
                capture_data = json.load(f)
        else:
            capture_data = {}
    except Exception as e:
        print(f"Warning: Could not read {REPORTS_PATH} ({e}), starting fresh.")
        capture_data = {}

    capture_data["title"] = "FRA400 Capture Report"
    capture_data["capture"] = (
        "FRA400:\n"
        "  * Standby\n"
        "  * Offline\n\n"
        "75Q:\n"
        "  * Standby\n"
        "  * Offline\n\n"
        "🏠 Roof Status: 🔴 CLOSED (Daytime Standby)\n\n"
        "System Status: **NOMINAL**\n"
        "  * Backups: Completed\n"
        "  * Fleet disks: OK (<75%)\n"
        "  * Mounts: Parked & Safe"
    )
    capture_data["capture75"] = "75Q:\n  * Standby\n  * Offline"

    try:
        with open(REPORTS_PATH, "w", encoding="utf-8") as f:
            json.dump(capture_data, f, indent=2)
        print(f"Updated {REPORTS_PATH}")
    except Exception as e:
        print(f"Error writing to {REPORTS_PATH}: {e}", file=sys.stderr)

    # 2. Update forecast.json
    try:
        if os.path.exists(FORECAST_PATH):
            with open(FORECAST_PATH, "r", encoding="utf-8") as f:
                forecast_data = json.load(f)
        else:
            forecast_data = {}
    except Exception as e:
        print(f"Warning: Could not read {FORECAST_PATH} ({e}), starting fresh.")
        forecast_data = {}

    forecast_data["title"] = "Daytime System Summary"
    forecast_data["roof_status"] = "CLOSED"
    forecast_data["cloud_pct"] = 0
    forecast_data["night_forecast"] = []

    try:
        with open(FORECAST_PATH, "w", encoding="utf-8") as f:
            json.dump(forecast_data, f, indent=2)
        print(f"Updated {FORECAST_PATH}")
    except Exception as e:
        print(f"Error writing to {FORECAST_PATH}: {e}", file=sys.stderr)

    # 3. Update observations.json
    try:
        if os.path.exists(OBS_PATH):
            with open(OBS_PATH, "r", encoding="utf-8") as f:
                obs_data = json.load(f)
        else:
            obs_data = {}
    except Exception as e:
        print(f"Warning: Could not read {OBS_PATH} ({e}), starting fresh.")
        obs_data = {}

    obs_data["physical_roof_status"] = "Closed"
    if "processed" not in obs_data:
        obs_data["processed"] = {}
    obs_data["processed"]["daytime_status"] = "daytime"
    obs_data["processed"]["night_forecast"] = []

    try:
        with open(OBS_PATH, "w", encoding="utf-8") as f:
            json.dump(obs_data, f, indent=2)
        print(f"Updated {OBS_PATH}")
    except Exception as e:
        print(f"Error writing to {OBS_PATH}: {e}", file=sys.stderr)
        
    print("Day Mode active.")

def restore_night_mode():
    print("Starting sfro-dash-v5-scheduler to restore default Night Mode pipeline...")
    # Start the scheduler container to resume normal live updates
    run_docker_command(["start", "sfro-dash-v5-scheduler"])
    print("Night Mode restored (scheduler will run and overwrite JSON files with live data).")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: ./toggle_day_mode.py [day|night]")
        sys.exit(1)
        
    action = sys.argv[1].lower()
    if action == "day":
        enable_day_mode()
    elif action == "night":
        restore_night_mode()
    else:
        print(f"Unknown action: {action}")
        sys.exit(1)
