#!/usr/bin/env python3
import sys
import os
import json
import time
import requests
from datetime import datetime, timezone

API_URL = "https://sfro.cosmiclight.space/api/observations"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(SCRIPT_DIR, ".roof_monitor_state.json")

def main():
    # Enforce run window check in script (7am UTC to 3pm UTC / 15:00 UTC)
    # The cron job runs every 10 min from 7am to 2:50pm UTC.
    now_utc = datetime.now(timezone.utc)
    current_hour = now_utc.hour
    if current_hour < 7 or current_hour >= 15:
        sys.exit(0)

    # Current date string to partition states by day
    today_str = now_utc.strftime("%Y-%m-%d")

    # Fetch API data
    try:
        resp = requests.get(API_URL, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"⚠️ Observatory API Error: {e}", file=sys.stderr)
        sys.exit(0)  # Exit 0 to prevent cron health check failures, but report to stderr

    roof_status = data.get("physical_roof_status") # e.g. "Open" or "Closed"
    if roof_status is None:
        roof_status = "Unknown"

    sunrise_epoch = data.get("processed", {}).get("sunrise") # UTC epoch in seconds

    if not sunrise_epoch:
        print("⚠️ Observatory API Error: Missing sunrise in response", file=sys.stderr)
        sys.exit(0)

    # Normalize roof status to Title Case (e.g. "Open" or "Closed")
    roof_status = roof_status.strip().title()

    # Load state
    state = {}
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                state = json.load(f)
        except Exception:
            state = {}

    # If the state is from a previous day, reset it
    if state.get("date") != today_str:
        state = {
            "date": today_str,
            "last_status": None,
            "alerted_initial": False,
            "alerted_sunrise": False,
            "completed_for_day": False
        }

    # If already completed for the day, exit silently
    if state.get("completed_for_day"):
        sys.exit(0)

    current_time_epoch = time.time()
    output_message = []

    # 1. At/After Sunrise
    if current_time_epoch >= sunrise_epoch:
        # A. If we haven't alerted sunrise yet:
        if not state.get("alerted_sunrise"):
            output_message.append(f"☀️ Texas Sunrise: The observatory roof is **{roof_status}**.")
            state["alerted_sunrise"] = True
            state["last_status"] = roof_status
            
            # If the roof is Closed at sunrise, we are done for the day
            if roof_status == "Closed":
                state["completed_for_day"] = True
                
        # B. If we have alerted sunrise, but are not completed yet (it was Open at sunrise)
        elif not state.get("completed_for_day"):
            # Check if status changed
            if state.get("last_status") is not None and state["last_status"] != roof_status:
                output_message.append(f"🔄 Observatory roof status changed: **{state['last_status']}** ➡️ **{roof_status}**.")
                state["last_status"] = roof_status
                
                # Once it switches to Closed, we are done for the day
                if roof_status == "Closed":
                    state["completed_for_day"] = True

    # 2. Before Sunrise
    else:
        # A. If initial run of the day
        if not state.get("alerted_initial"):
            state["alerted_initial"] = True
            state["last_status"] = roof_status
            if roof_status == "Open":
                output_message.append(f"⚠️ Observatory roof is **Open** at start of monitoring (07:00 UTC).")
            elif roof_status == "Unknown":
                output_message.append(f"⚠️ Observatory roof status is **Unknown** at start of monitoring (07:00 UTC).")
            # If Closed at start of monitoring (07:00 UTC), we stay silent
                
        # B. Subsequent runs before sunrise: check if status changed
        elif state.get("last_status") is not None and state["last_status"] != roof_status:
            output_message.append(f"🔄 Observatory roof status changed: **{state['last_status']}** ➡️ **{roof_status}**.")
            state["last_status"] = roof_status

    # Save state
    try:
        with open(STATE_FILE, "w") as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        print(f"⚠️ Failed to write state file: {e}", file=sys.stderr)

    # Print output if there is any (triggers Telegram delivery)
    if output_message:
        print("\n".join(output_message))

if __name__ == "__main__":
    main()
