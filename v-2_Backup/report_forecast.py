#!/usr/bin/env python3
import urllib.request
import json
import os
from datetime import datetime

# Remote endpoints for JSON data
HOST_URL = os.getenv("DASHBOARD_HOST", "http://192.168.1.51:5002")
FRA400_URL = f"{HOST_URL}/data/FRA400_log.json"
Q75_URL = f"{HOST_URL}/data/75Q_log.json"

def fetch_json(url):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            return json.loads(response.read().decode('utf-8'))
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None

def parse_iso(dt_str):
    """Converts a naive or timezone-aware ISO string to a comparable naive datetime."""
    # Takes the first 19 chars: YYYY-MM-DDTHH:MM:SS
    return datetime.fromisoformat(dt_str[:19])

def get_forecast_logic(data):
    if not data: return None
    fc_keys = [k for k in data.keys() if k.endswith('_forecast')]
    if not fc_keys: return None
    
    night_key = sorted(fc_keys)[-1]
    fc = data[night_key]
    
    # 1. Analyze Cloud Cover
    weather_series = fc.get("weather", [])
    open_windows = []
    current_window = []
    
    for entry in weather_series:
        cloud = entry.get("cloud", 100)
        time_parsed = parse_iso(entry["time"])
        if cloud < 20:
            current_window.append((time_parsed, cloud))
        else:
            if len(current_window) > 1:
                open_windows.append(current_window)
            current_window = []
    if len(current_window) > 1:
        open_windows.append(current_window)
        
    # 2. Filter Wait States
    astral_data = fc.get("astral", {})
    naut_dusk = parse_iso(astral_data.get("nautical_dusk", "2099-01-01T00:00:00"))
    
    relevant_waits = []
    for w in fc.get("events", {}).get("target_waits", []):
        w_start = parse_iso(w["start"])
        w_end = parse_iso(w["end"])
        if w_end > naut_dusk:
            relevant_waits.append((w_start, w_end))
            
    targets = fc.get("events", {}).get("targets", [])
    moon = fc.get("moon", {})
    
    return {
        "date": night_key.replace("_forecast", ""),
        "open_windows": open_windows,
        "waits": relevant_waits,
        "targets": targets,
        "moon": moon
    }

def main():
    fra_data = fetch_json(FRA400_URL)
    q75_data = fetch_json(Q75_URL)
    
    if not fra_data and not q75_data:
        print("Error: Could not fetch data from either scope.")
        return
        
    # We use FRA400 for the baseline weather/moon logic since weather is location-wide
    fc = get_forecast_logic(fra_data or q75_data)
    
    if not fc:
        print("No upcoming forecast found.")
        return
        
    # Parse the date string to get the weekday
    fc_date = datetime.strptime(fc['date'], "%Y-%m-%d")
    weekday_str = fc_date.strftime("%A")
    print(f"🌌 **Tonight's Observatory Forecast {weekday_str} ({fc['date']})**")
    
    # Roof Forecast
    if fc["open_windows"]:
        print("Roof Open Likelihood: **HIGH**")
        for idx, win in enumerate(fc["open_windows"]):
            s = win[0][0].strftime("%H:%M")
            e = win[-1][0].strftime("%H:%M")
            avg_cloud = sum(x[1] for x in win) / len(win)
            print(f"  * Window {idx+1}: {s} - {e} (Avg Cloud: {avg_cloud:.1f}%)")
    else:
        print("Roof Open Likelihood: **LOW** (No clear blocks >1 hour)")
        
    # Moon
    moon = fc["moon"]
    if moon:
        print(f"\n🌙 **Moon Phase**: {moon.get('phase')} ({moon.get('illum')} illum, Age: {moon.get('age')} days)")
        print(f"⏰ {moon.get('events_string', '').replace('&nbsp;&bull;&nbsp;', ' | ')}")
        
    # Targets (Combined)
    print("\n🔭 **Target Summary**")
    
    if fra_data:
        fra_fc = get_forecast_logic(fra_data)
        targets = [t['name'] for t in (fra_fc['targets'] if fra_fc else [])]
        print(f"  * FRA400: {', '.join(targets) if targets else 'None Scheduled'}")
        
    if q75_data:
        q75_fc = get_forecast_logic(q75_data)
        targets = [t['name'] for t in (q75_fc['targets'] if q75_fc else [])]
        print(f"  * 75Q: {', '.join(targets) if targets else 'None Scheduled'}")
        
    # Wait States
    waits = fc["waits"]
    if waits:
        print("\n⏳ **Wait States of Interest** (After Nautical Dusk):")
        for ws, we in waits:
            print(f"  * Wait: {ws.strftime('%H:%M')} to {we.strftime('%H:%M')}")

if __name__ == "__main__":
    main()
