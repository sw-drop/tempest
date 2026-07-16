#!/usr/bin/env python3
import os
import sys
import json
import urllib.request
from urllib.error import URLError
from datetime import datetime, timezone

HERMES_HOME = os.environ.get("HERMES_HOME", "/opt/data")
STATE_FILE = os.path.join(HERMES_HOME, ".hermes", "observatory_roof_state.json")

def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_state(state):
    try:
        os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
        with open(STATE_FILE, "w") as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        print(f"Warning: Could not save state: {e}", file=sys.stderr)

def check_starfront_api():
    url = "https://alpaca-api.tx.starfront.space/api/v1/roof/state"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=10) as response:
        data = json.loads(response.read().decode('utf-8'))
        if not isinstance(data, list):
            raise ValueError("Starfront API did not return a list")
        for building in data:
            if building.get("device_number") == 5:
                is_open = building.get("is_open")
                if is_open is True:
                    return "Open"
                elif is_open is False:
                    return "Closed"
        raise ValueError("Building 5 (device_number 5) not found in Starfront API response")

def check_local_api():
    url = "http://192.168.1.60:8081/api/observations"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=10) as response:
        data = json.loads(response.read().decode('utf-8'))
        status = data.get("physical_roof_status")
        if status:
            return status.strip().title()
        raise ValueError("physical_roof_status not found in local observations API")

def check_cloudflare_api():
    url = "https://sfro.cosmiclight.space/api/observations"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=10) as response:
        data = json.loads(response.read().decode('utf-8'))
        status = data.get("physical_roof_status")
        if status:
            return status.strip().title()
        raise ValueError("physical_roof_status not found in Cloudflare observations API")

def main():
    status = None
    errors = []
    source = None
    
    # 1. Try Starfront Alpaca API (Primary)
    try:
        status = check_starfront_api()
        source = "Starfront Alpaca API"
    except Exception as e:
        errors.append(f"Starfront API: {e}")
        
    # 2. Try Local weather station API (Fallback 1)
    if status is None:
        try:
            status = check_local_api()
            source = "Local weather station API"
        except Exception as e:
            errors.append(f"Local Weather API: {e}")
            
    # 3. Try Cloudflare tunnel API (Fallback 2)
    if status is None:
        try:
            status = check_cloudflare_api()
            source = "Cloudflare Weather API"
        except Exception as e:
            errors.append(f"Cloudflare Weather API: {e}")
            
    if status is None:
        # All sources failed
        err_msg = "; ".join(errors)
        print(f"⚠️ Error checking observatory roof status: {err_msg}", file=sys.stderr)
        sys.exit(1)
        
    now_gmt = datetime.now(timezone.utc)
    today_date = now_gmt.strftime("%Y-%m-%d")
    is_7am_gmt = (now_gmt.hour == 7 and now_gmt.minute < 5)

    state = load_state()
    last_status = state.get("last_status")
    last_7am_alert_date = state.get("last_7am_alert_date")

    should_alert = False
    alert_msg = ""

    if last_status is None:
        # First run: save state without alerting unless it is 7am GMT and open
        state["last_status"] = status
        save_state(state)
        if status == "Open" and is_7am_gmt:
            should_alert = True
            alert_msg = f"⚠️ Observatory roof (Building 5) is OPEN (Source: {source})"
            state["last_7am_alert_date"] = today_date
            save_state(state)
    else:
        if status != last_status:
            should_alert = True
            alert_msg = f"⚠️ Observatory roof (Building 5) status changed: it is now {status.upper()} (Source: {source})"
            state["last_status"] = status
            save_state(state)
        elif status == "Open" and is_7am_gmt and last_7am_alert_date != today_date:
            should_alert = True
            alert_msg = f"⚠️ Daily Check: Observatory roof (Building 5) is OPEN (Source: {source})"
            state["last_7am_alert_date"] = today_date
            save_state(state)

    if should_alert:
        print(alert_msg)

if __name__ == "__main__":
    main()
