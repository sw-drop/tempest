#!/usr/bin/env python3
"""
Monitor Minimum Execution Score for currency conversion alerts
Queries FX Horizon API to check GBP/ZAR, GBP/USD, GBP/EUR scores
against dynamic user-defined thresholds and alerts via stdout/Telegram.
Suppresses alerts within time windows: 00:00-12:00, 12:00-18:00, 18:00-24:00.
"""

import os
import sys
import json
import urllib.request
from datetime import datetime

# === Configuration ===
API_HOST = "192.168.1.60"
CONFIG_URL = f"http://{API_HOST}:8100/api/config"
LANDSCAPE_URL = f"http://{API_HOST}:8100/api/landscape"

# Paths
HERMES_HOME = os.environ.get("HERMES_HOME", "/opt/data")
STATE_FILE = os.path.join(HERMES_HOME, ".hermes", "min_score_state.json")
LOG_FILE = os.path.join(HERMES_HOME, ".hermes", "min_score_monitor.log")

def fetch_json(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as response:
            return json.loads(response.read().decode())
    except Exception as e:
        print(f"❌ Min Score Monitor Error: Failed to fetch data from {url}: {e}", file=sys.stderr)
        sys.exit(1)

def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_state(state):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    try:
        with open(STATE_FILE, "w") as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        print(f"⚠️ Error saving state file: {e}", file=sys.stderr)

def log_event(msg):
    timestamp = datetime.now().strftime("%a %b %d %H:%M:%S London %Y")
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    try:
        with open(LOG_FILE, "a") as f:
            f.write(f"{timestamp}: {msg}\n")
    except Exception:
        pass

def main():
    now = datetime.now()
    
    # 1. Determine current suppression window interval
    # Interval 1: 00:00 - 11:59
    # Interval 2: 12:00 - 17:59
    # Interval 3: 18:00 - 23:59
    if now.hour < 12:
        interval_num = 1
    elif now.hour < 18:
        interval_num = 2
    else:
        interval_num = 3
    
    interval_id = f"{now.strftime('%Y-%m-%d')}_{interval_num}"
    
    # 2. Fetch config and landscape API data
    config = fetch_json(CONFIG_URL)
    landscape = fetch_json(LANDSCAPE_URL)
    
    # 3. Load previous alert states
    state = load_state()
    state_changed = False
    
    # Map the config keys to landscape keys and readable names
    pairs = [
        ("gbp_zar", "GBP_ZAR", "GBP/ZAR"),
        ("gbp_usd", "GBP_USD", "GBP/USD"),
        ("gbp_eur", "GBP_EUR", "GBP/EUR")
    ]
    
    for conf_key, land_key, display_name in pairs:
        alert_enabled = config.get(f"alert_{conf_key}", False)
        target_threshold = config.get(f"min_score_{conf_key}", 100)
        
        pair_data = landscape.get(land_key)
        if not pair_data:
            log_event(f"Warning: Pair {land_key} data missing from landscape.")
            continue
            
        current_score = pair_data.get("score", 0)
        spot_rate = pair_data.get("spot", 0)
        
        # Check condition: Alert enabled and score is equal or greater than threshold
        if alert_enabled and current_score >= target_threshold:
            # Check if alert already sent in the current time interval
            last_alerted_interval = state.get(land_key)
            if last_alerted_interval == interval_id:
                log_event(f"{display_name} score {current_score:.1f} >= {target_threshold:.1f}, but already alerted in interval {interval_id}. Suppressed.")
            else:
                # Trigger alert (stdout is forwarded to Telegram by Hermes)
                msg = (
                    f"🚨 MINIMUM EXECUTION SCORE ALERT 🚨\n\n"
                    f"Pair: {display_name}\n"
                    f"Score: {current_score:.1f} (Target: ≥ {target_threshold:.1f})\n"
                    f"Spot Rate: {spot_rate}\n"
                    f"Time: {now.strftime('%H:%M')} (London)\n\n"
                    f"Recommended action: Currency conversion opportunity detected."
                )
                print(msg)
                
                log_event(f"ALERT SENT: {display_name} score {current_score:.1f} >= {target_threshold:.1f} (Spot: {spot_rate})")
                state[land_key] = interval_id
                state_changed = True
        else:
            # Condition no longer holds or alert disabled, clear the state for this pair
            if land_key in state:
                log_event(f"Clearing alert state for {display_name} (current score {current_score:.1f} < {target_threshold:.1f} or alert disabled).")
                del state[land_key]
                state_changed = True
            else:
                log_event(f"{display_name} score {current_score:.1f} < {target_threshold:.1f} or alert disabled. No action.")
                
    if state_changed:
        save_state(state)
        
    log_event("Monitor run completed")

if __name__ == "__main__":
    main()
