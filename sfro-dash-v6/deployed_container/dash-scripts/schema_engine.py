#!/usr/bin/env python3
import json
import os
import sys
import urllib.request
from datetime import datetime, timedelta, timezone

LAT = float(os.getenv("LAT", "31.546944"))
LON = float(os.getenv("LON", "-99.382222"))

def get_forecast_roof_prospect(lat=LAT, lon=LON):
    """
    Fetches the yr.no forecast for Starfront and checks if there are >= 2 consecutive hours
    of < 20% clouds during the upcoming/current night (18:00 to 06:00 UTC).
    Returns True if clear window found, False otherwise.
    """
    url = f"https://api.met.no/weatherapi/locationforecast/2.0/compact?lat={lat:.4f}&lon={lon:.4f}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Tempest-V5-SchemaEngine/1.0 gary@pillay.net"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode('utf-8'))
    except Exception as e:
        print(f"Error fetching forecast for schema engine: {e}", file=sys.stderr)
        return False
        
    ts = data.get('properties', {}).get('timeseries', [])
    now_utc = datetime.now(timezone.utc)
    
    # Define "tonight" boundaries (18:00 UTC today to 06:00 UTC tomorrow)
    # If it's already past midnight but before 6am, "tonight" started yesterday.
    if now_utc.hour < 12:
        start_night = now_utc.replace(hour=18, minute=0, second=0, microsecond=0) - timedelta(days=1)
    else:
        start_night = now_utc.replace(hour=18, minute=0, second=0, microsecond=0)
        
    end_night = start_night + timedelta(hours=12)
    
    clouds = []
    for entry in ts:
        try:
            t = datetime.fromisoformat(entry['time'].replace('Z', '+00:00'))
            # Only consider times strictly within the night window AND in the future/present
            if t >= now_utc and start_night <= t <= end_night:
                c = entry['data']['instant']['details'].get('cloud_area_fraction')
                if c is not None:
                    clouds.append((t, float(c)))
        except:
            pass
            
    # Find windows: >=2h consecutive with cloud < 20%
    start_clear = None
    for t, c in clouds:
        if c < 20:
            if start_clear is None:
                start_clear = t
            else:
                dur = (t - start_clear).total_seconds() / 3600
                if dur >= 2:
                    return True # Found a 2hr window!
        else:
            start_clear = None
            
    return False

def get_actual_roof_state(roof_path):
    """Reads roof.json to determine if roof is currently OPEN."""
    try:
        with open(roof_path, 'r') as f:
            r = json.load(f)
            return r.get("data", {}).get("status", "").upper() == "OPEN"
    except:
        return False

def evaluate_schema(app_dir="/app/app_data", agent_dir="/app/data", lat=LAT, lon=LON):
    override_path = os.path.join(agent_dir, "override.json")
    roof_path = os.path.join(app_dir, "roof.json")
    
    # 1. Check override
    try:
        if os.path.exists(override_path):
            with open(override_path, 'r') as f:
                o = json.load(f)
                if "override" in o and o["override"]:
                    return o["override"]
    except Exception as e:
        print(f"Override read error: {e}", file=sys.stderr)

    # 2. Evaluate state matrix
    now_utc = datetime.now(timezone.utc)
    hour = now_utc.hour
    
    # We evaluate weather and roof states
    roof_is_open = get_actual_roof_state(roof_path)
    forecast_open = get_forecast_roof_prospect(lat=lat, lon=lon)
    
    # Rule alias
    prospect_open = roof_is_open or forecast_open

    schema = "RoofClosedEvening1" # Fallback
    if 0 <= hour < 6:
        schema = "RoofOpenNight1" if prospect_open else "RoofClosedNight1"
    elif 6 <= hour < 9:
        schema = "RoofOpenDawn1" if prospect_open else "RoofClosedDawn1"
    elif 9 <= hour < 12:
        schema = "RoofOpenMorning1" if prospect_open else "RoofClosedMorning1"
    elif 12 <= hour < 15:
        schema = "RoofOpenLunch1" if prospect_open else "RoofClosedLunch1"
    elif 15 <= hour < 18:
        schema = "Afternoon1"
    elif 18 <= hour < 21:
        schema = "Supper1"
    elif 21 <= hour <= 23:
        schema = "RoofOpenEvening1" if prospect_open else "RoofClosedEvening1"

    out_path = os.path.join(app_dir, "active_schema.json")
    temp_out = f"{out_path}.tmp"
    try:
        with open(temp_out, "w") as f:
            json.dump({"schema": schema, "updated_at": now_utc.isoformat()}, f, indent=2)
        os.replace(temp_out, out_path)
        print(f"Schema Engine Active: Set to {schema} at {now_utc.isoformat()}")
    except Exception as e:
        print(f"Error writing schema file: {e}", file=sys.stderr)

    return schema

def main():
    app_dir = os.environ.get("APP_DIR", "/app/app_data")
    agent_dir = os.environ.get("AGENT_DIR", "/app/data")
    out_path = os.path.join(app_dir, "active_schema.json")
    
    schema = evaluate_schema(app_dir=app_dir, agent_dir=agent_dir)
    
    out_dir = os.path.dirname(out_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
        
    temp_out = f"{out_path}.tmp"
    try:
        with open(temp_out, "w") as f:
            json.dump({"schema": schema, "updated_at": datetime.now(timezone.utc).isoformat()}, f, indent=2)
        os.replace(temp_out, out_path)
        print(f"Schema Engine Active: Set to {schema}")
    except Exception as e:
        print(f"Error writing schema file: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
