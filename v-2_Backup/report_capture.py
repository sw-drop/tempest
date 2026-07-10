#!/usr/bin/env python3
import sys
import urllib.request
import json
import os
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

# Configuration
TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    # Look for .env in the parent folder if running locally
    try:
        with open("../.env", "r") as f:
            for line in f:
                if line.startswith("DISCORD_TOKEN"):
                    TOKEN = line.split("=")[1].strip().strip('"').strip("'")
    except Exception:
        pass

if not TOKEN:
    print("Warning: DISCORD_TOKEN is not defined. Exiting gracefully for test run.")
    sys.exit(0)

HEADERS = {"Authorization": f"Bot {TOKEN}", "User-Agent": "StarfrontDashboard/1.0"}

CHANNELS = {
    "fra400": "1407795208200126516",
    "75q": "1440079351516237864",
    "announcements": "1409490508803211345"
}

def fetch_messages(channel_id, limit=100):
    url = f"https://discord.com/api/v10/channels/{channel_id}/messages?limit={limit}"
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            return json.loads(response.read().decode('utf-8'))
    except Exception as e:
        print(f"Error fetching channel {channel_id}: {e}")
        return []

def parse_discord_time(ts_str):
    # Returns a naive UTC datetime
    if not ts_str: return None
    dt_str = ts_str.split('+')[0][:19]
    return datetime.fromisoformat(dt_str)

def get_local_time_string(utc_dt):
    # Convert naive UTC datetime to timezone-aware UTC, then convert to America/Chicago
    utc_dt = utc_dt.replace(tzinfo=ZoneInfo("UTC"))
    local_dt = utc_dt.astimezone(ZoneInfo("America/Chicago"))
    return local_dt.strftime("%Y-%m-%d %H:%M:%S Central")

def get_local_time_string_short(utc_dt):
    utc_dt = utc_dt.replace(tzinfo=ZoneInfo("UTC"))
    local_dt = utc_dt.astimezone(ZoneInfo("America/Chicago"))
    return local_dt.strftime("%H:%M Central")

def main():
    # Calculate the logical "astrophotography night" (current time - 12 hours)
    astro_night = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=12)
    astro_weekday = astro_night.strftime("%A")
    print(f"🔭 **Nightly Capture & Operations Report - {astro_weekday}**\n")
    
    # Establish time boundary: 18 hours ago
    cutoff_time = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=18)
    
    # --- 1. Tally Exposures ---
    print("📸 **Exposure Summary**")
    for scope_name in ["fra400", "75q"]:
        msgs = fetch_messages(CHANNELS[scope_name], limit=100)
        
        target_tallies = {}
        
        for msg in msgs:
            msg_time = parse_discord_time(msg["timestamp"])
            if msg_time < cutoff_time:
                continue
                
            content = msg.get("content", "").lower()
            if "_exps_" in content:
                # Extract target name from embed
                embeds = msg.get("embeds", [])
                target_name = "Unknown Target"
                for embed in embeds:
                    for field in embed.get("fields", []):
                        if field.get("name") == "Target":
                            target_name = field.get("value")
                
                target_tallies[target_name] = target_tallies.get(target_name, 0) + 1
        
        print(f"  * {scope_name.upper()}:")
        if not target_tallies:
            print("    * No exposures recorded in the last 18 hours.")
        else:
            for t, count in target_tallies.items():
                print(f"    * Target: {t} x {count} Images")
                
    # --- 2. Roof & Weather Reports ---
    print("\n🏠")
    announcements = fetch_messages(CHANNELS["announcements"], limit=20)
    
    latest_roof = "Unknown"
    latest_roof_time = None
    latest_report = "None"
    latest_report_time = None
    
    for msg in announcements:
        msg_time = parse_discord_time(msg["timestamp"])
        
        # Check for Weather Report
        if msg.get("content", "").startswith("**Nightly Plan") and not latest_report_time:
            latest_report = msg.get("content")
            latest_report_time = msg_time
            
        # Check for Roof embeds
        for embed in msg.get("embeds", []):
            title = embed.get("title", "")
            if "Roofs Closing" in title or "Roofs Opening" in title:
                if not latest_roof_time:
                    latest_roof = embed.get("description", "").split("\n")[0].replace("**", "")
                    latest_roof_time = msg_time
                    
    if latest_roof_time:
        status = latest_roof.strip().rstrip('.')
        if "opening" in status.lower():
            status_text = "🟢 OPENING"
        elif "closing" in status.lower():
            status_text = "🔴 CLOSING"
        elif "open" in status.lower():
            status_text = "🟢 OPEN"
        elif "closed" in status.lower():
            status_text = "🔴 CLOSED"
        else:
            status_text = status.upper()
        print(f"Roof Status: {status_text} (at {get_local_time_string_short(latest_roof_time)})")
    else:
        print("Roof Status: No events found")
        
    if latest_report_time:
        print()
        print(latest_report.strip())

if __name__ == "__main__":
    main()
