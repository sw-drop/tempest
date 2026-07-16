# forecast_generator.py v1.6.3

import os
import json
import requests
import socket
import re
import warnings
from urllib.parse import urlparse
from datetime import datetime, timedelta
import pytz
from astral import LocationInfo
from astral.sun import sun, dusk, dawn

import numpy as np
from astropy.time import Time
from astropy.coordinates import get_body, AltAz, EarthLocation, get_sun
import astropy.units as u

try:
    from urllib3.exceptions import NotOpenSSLWarning
    warnings.filterwarnings("ignore", category=NotOpenSSLWarning)
except ImportError:
    pass

# ==================== CONFIGURATION ====================
DATA_DIR = "data"
SCOPES_ENV = os.getenv("SCOPES", "FRA400:1407795208200126516,75Q:1440079351516237864")
SCOPES = []
for pair in SCOPES_ENV.split(","):
    name, _ = pair.split(":")
    SCOPES.append(name.strip())

LAT = float(os.getenv("LAT", "31.546944"))
LON = float(os.getenv("LON", "-99.382222"))
ALTITUDE = int(float(os.getenv("ALTITUDE", "466")))
TIMEZONE = os.getenv("TIMEZONE", "America/Chicago")
CENTRAL_TZ = pytz.timezone(TIMEZONE)
loc = LocationInfo("Starfront", "Texas", TIMEZONE, LAT, LON)

WEATHER_CACHE = None 
WEATHER_CACHE_TIME = 0.0
# =======================================================

def load_json(filepath):
    if not os.path.exists(filepath): return {}
    with open(filepath, 'r', encoding='utf-8') as f: return json.load(f)

def save_json(filepath, data):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)

def is_host_reachable(url, timeout=1.0):
    parsed = urlparse(url)
    host = parsed.hostname
    port = parsed.port or 80
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False

def parse_net_time(ts_str):
    if not ts_str: return None
    clean_str = re.sub(r'(\.\d{6})\d+', r'\1', ts_str)
    return datetime.fromisoformat(clean_str).astimezone(CENTRAL_TZ)

def fetch_api(url):
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return None

def fetch_weather_api():
    url = "https://api.met.no/weatherapi/locationforecast/2.0/compact"
    params = {"lat": LAT, "lon": LON, "altitude": ALTITUDE}
    headers = {"User-Agent": "StarfrontDashboard/1.0 purchase@pillay.co.uk"}
    try:
        response = requests.get(url, params=params, headers=headers, timeout=5)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"  [!] Failed to fetch Yr.no weather data: {e}")
        return None

def prune_old_forecasts(data, current_time):
    keys_to_delete = []
    for key in list(data.keys()):
        if key.endswith("_forecast"):
            date_str = key.replace("_forecast", "")
            try:
                dt = datetime.strptime(date_str, "%Y-%m-%d").date()
                n_dawn = dawn(loc.observer, date=dt + timedelta(days=1), depression=12.0, tzinfo=CENTRAL_TZ)
                cutoff_time = n_dawn - timedelta(hours=1)
                
                if current_time >= cutoff_time:
                    print(f"  [*] Pruning expired forecast: {key}")
                    keys_to_delete.append(key)
                    
                    # ARCHITECTURAL FIX: If the extractor didn't write a real record, preserve an empty husk
                    if date_str not in data:
                        print(f"  [*] Preserving {date_str} as closed-roof night.")
                        data[date_str] = {
                            "astral": data[key].get("astral", {}),
                            "roof": {"status": "Roof did not open", "open_events": [], "closed_events": []},
                            "events": {"meridian_flips": [], "target_waits": [], "targets": []}
                        }
            except Exception as e:
                pass
                
    for k in keys_to_delete:
        if k in data:
            del data[k]
    return data

def inject_weather(forecast_record):
    global WEATHER_CACHE
    global WEATHER_CACHE_TIME
    import time

    current_time = time.time()
    
    # If cache is empty OR older than 15 minutes (900 seconds), fetch new data
    if WEATHER_CACHE is None or (current_time - WEATHER_CACHE_TIME) > 900:
        fetched_data = fetch_weather_api()
        if fetched_data:
            WEATHER_CACHE = fetched_data
            WEATHER_CACHE_TIME = current_time

    if not WEATHER_CACHE:
        return

    try:
        roof_open = datetime.fromisoformat(forecast_record["roof"]["open_events"][0])
        n_dawn = datetime.fromisoformat(forecast_record["astral"]["nautical_dawn"])
    except Exception:
        return
        
    # RETENTION LOGIC: Load existing weather blocks into a time-keyed dictionary
    existing_weather = {w["time"]: w for w in forecast_record.get("weather", [])}
    
    timeseries = WEATHER_CACHE.get('properties', {}).get('timeseries', [])
    for entry in timeseries:
        utc_time = datetime.strptime(entry['time'], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=pytz.utc)
        local_time = utc_time.astimezone(CENTRAL_TZ)
        
        # If Yr.no provides data in our window, update or append it.
        # If Yr.no dropped past hours, those remain safely untouched in existing_weather.
        if roof_open - timedelta(hours=1) <= local_time <= n_dawn + timedelta(hours=1):
            details = entry['data']['instant']['details']
            summary = entry['data'].get('next_1_hours', {}).get('summary', {}).get('symbol_code', 'clearsky_night')
            
            existing_weather[local_time.isoformat()] = {
                "time": local_time.isoformat(),
                "temp": details.get('air_temperature', 0),
                "cloud": details.get('cloud_area_fraction', 0),
                "wind": details.get('wind_speed', 0),
                "symbol": summary
            }
            
    # Convert back to list and sort chronologically before saving
    forecast_record["weather"] = [existing_weather[k] for k in sorted(existing_weather.keys())]

def inject_moon(forecast_record, date_key):
    dt = datetime.strptime(date_key, "%Y-%m-%d").date()
    s_today = sun(loc.observer, date=dt, tzinfo=CENTRAL_TZ)
    s_tmrw = sun(loc.observer, date=dt + timedelta(days=1), tzinfo=CENTRAL_TZ)
    sunset_dt = s_today["sunset"]
    sunrise_dt = s_tmrw["sunrise"]
    
    sunset_t = Time(sunset_dt)
    m_at_s = get_body('moon', sunset_t)
    sun_at_s = get_sun(sunset_t)
    phase_deg = (m_at_s.geocentrictrueecliptic.lon.deg - sun_at_s.geocentrictrueecliptic.lon.deg) % 360
    illumination = (1 + np.cos(np.radians(180 - phase_deg))) / 2.0
    lunar_age = (phase_deg / 360.0) * 29.53
    
    phase_map = [
        (0, 11.25, "New Moon"), (11.25, 78.75, "Waxing Crescent"),
        (78.75, 101.25, "First Quarter"), (101.25, 168.75, "Waxing Gibbous"),
        (168.75, 191.25, "Full Moon"), (191.25, 258.75, "Waning Gibbous"),
        (258.75, 281.25, "Last Quarter"), (281.25, 348.75, "Waning Crescent"),
        (348.75, 360, "New Moon")
    ]
    p_name = next(n for low, high, n in phase_map if low <= phase_deg < high)
    
    start_dt = sunset_dt - timedelta(hours=1)
    end_dt = sunrise_dt + timedelta(hours=1)
    num_points = int((end_dt - start_dt).total_seconds() / 600) + 1 
    times_dt = [start_dt + timedelta(minutes=10*i) for i in range(num_points)]
    
    location = EarthLocation(lat=LAT*u.deg, lon=LON*u.deg, height=ALTITUDE*u.m)
    times_t = Time(times_dt)
    moon_alts = get_body('moon', times_t).transform_to(AltAz(obstime=times_t, location=location)).alt.deg
    
    path = []
    max_alt = -90
    moon_events = []
    prev_alt = None
    
    for pt_dt, alt in zip(times_dt, moon_alts):
        a = float(alt)
        
        # Only consider peak elevation during the dark hours (between sunset and sunrise)
        if sunset_dt <= pt_dt <= sunrise_dt:
            if a > max_alt: max_alt = a
            
        path.append({"time": pt_dt.isoformat(), "alt": round(a, 2)})
        
        if prev_alt is not None:
            if prev_alt < 0 and a >= 0:
                moon_events.append((pt_dt, "Moonrise"))
            elif prev_alt > 0 and a <= 0:
                moon_events.append((pt_dt, "Moonset"))
        prev_alt = a
        
    all_events = [(sunset_dt, "Sunset"), (sunrise_dt, "Sunrise")] + moon_events
    all_events.sort(key=lambda x: x[0])
    events_string = " &nbsp;&bull;&nbsp; ".join([f"{name}: {dt.strftime('%I:%M %p').lower()}" for dt, name in all_events])
        
    forecast_record["moon"] = {
        "phase": p_name,
        "age": round(lunar_age, 1),
        "illum": f"{illumination*100:.1f}%",
        "peak": round(max_alt, 1),
        "sunset": sunset_dt.strftime("%I:%M %p").lower(),
        "sunrise": sunrise_dt.strftime("%I:%M %p").lower(),
        "events_string": events_string,
        "path": path
    }

def get_forecast_key_from_api(api_data):
    if not api_data: return None
    first_event_start = parse_net_time(api_data[0]["StartTime"])
    night_date = (first_event_start - timedelta(hours=12)).date()
    return f"{night_date.isoformat()}_forecast"

def process_forecast_schedule(api_data):
    first_event_start = parse_net_time(api_data[0]["StartTime"])
    night_date = (first_event_start - timedelta(hours=12)).date()
    
    s = sun(loc.observer, date=night_date, tzinfo=CENTRAL_TZ)
    n_dusk = dusk(loc.observer, date=night_date, depression=12.0, tzinfo=CENTRAL_TZ)
    n_dawn = dawn(loc.observer, date=night_date + timedelta(days=1), depression=12.0, tzinfo=CENTRAL_TZ)
    roof_open = s["sunset"] - timedelta(minutes=15)
    
    forecast_record = {
        "astral": {"nautical_dusk": n_dusk.isoformat(), "nautical_dawn": n_dawn.isoformat()},
        "roof": {"status": "Forecast", "open_events": [roof_open.isoformat()], "closed_events": [(n_dawn + timedelta(minutes=5)).isoformat()]},
        "weather": [],
        "events": {"meridian_flips": [], "target_waits": [], "targets": []}
    }
    events = forecast_record["events"]
    
    if roof_open < n_dusk: events["target_waits"].append({"start": roof_open.isoformat(), "end": n_dusk.isoformat()})

    for block in api_data:
        start = parse_net_time(block["StartTime"])
        end = parse_net_time(block["EndTime"])
        if start < n_dusk: start = n_dusk
        if end <= start: continue
            
        if block.get("WaitPeriod"): events["target_waits"].append({"start": start.isoformat(), "end": end.isoformat()})
        else: events["targets"].append({"name": block.get("Name") or "Unknown Target", "start": start.isoformat(), "end": end.isoformat()})
            
    return forecast_record

def update_scope_forecast(json_path, api_url, scope_name):
    print(f"\n--- Updating Forecast: {scope_name} ---")
    data = load_json(json_path)
    now = datetime.now(CENTRAL_TZ)
    data = prune_old_forecasts(data, now)

    weather_updated = False
    for k, record in data.items():
        if k.endswith("_forecast"):
            inject_weather(record)
            inject_moon(record, k.replace("_forecast", ""))
            weather_updated = True

    if not is_host_reachable(api_url, timeout=1.0):
        print(f"  [!] NINA API unreachable.")
        if weather_updated: print("  [*] Successfully updated weather and lunar data for locked forecast.")
        save_json(json_path, data)
        return

    api_data = fetch_api(api_url)
    forecast_key = get_forecast_key_from_api(api_data)
    
    if not forecast_key:
        print(f"  [!] NINA API returned no schedule.")
        if weather_updated: print("  [*] Successfully updated weather and lunar data for locked forecast.")
        save_json(json_path, data)
        return
        

        
    real_key = forecast_key.replace("_forecast", "")
    # Check if a historical record exists AND either has targets shot OR is marked as a closed-roof night
    if real_key in data and (len(data[real_key].get("events", {}).get("targets", [])) > 0 or 
                             data[real_key].get("roof", {}).get("status") == "Roof did not open"):
        print(f"  [*] Archived history exists for {real_key}. Skipping schedule injection.")
        if weather_updated: print("  [*] Successfully updated weather and lunar data.")
        save_json(json_path, data)
        return

    forecast_data = process_forecast_schedule(api_data)
    if forecast_data:
        if forecast_key in data:
            forecast_data["weather"] = data[forecast_key].get("weather", [])
        inject_weather(forecast_data)
        inject_moon(forecast_data, real_key)
        data[forecast_key] = forecast_data
        print(f"  [✓] Target schedule updated and injected for {forecast_key}")
        save_json(json_path, data)

def main():
    for scope_name in SCOPES:
        default_api = ""
        if scope_name == "75Q":
            default_api = "http://100.100.218.98:8188/ts/v0/profiles/9f4f477e-c148-4672-a0dc-26411abb444b/preview"
        elif scope_name == "FRA400":
            default_api = "http://100.123.140.100:8188/ts/v0/profiles/ef60f4b0-5072-47e0-a2db-83ed16edf290/preview"
            
        api_url = os.getenv(f"API_{scope_name}", default_api)
        if api_url:
            json_path = os.path.join(DATA_DIR, f"{scope_name}_log.json")
            update_scope_forecast(json_path, api_url, scope_name)
    print("\nForecast update complete.")

if __name__ == "__main__":
    main()
