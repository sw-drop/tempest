#!/usr/bin/env python3
import urllib.request
import json
import os
import sys
import math
import argparse

DEFAULT_API_KEY = "6bff2f89-84ab-463c-886e-fc0f443da4cf"

def fetch_tempest_data(station_id, api_key):
    url = f"https://swd.weatherflow.com/swd/rest/observations/station/{station_id}?api_key={api_key}"
    req = urllib.request.Request(url, headers={"User-Agent": "Tempest-V5-Fetcher/1.0 gary@pillay.net"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode('utf-8'))

def fetch_met_norway_data(lat, lon):
    url = f"https://api.met.no/weatherapi/locationforecast/2.0/compact?lat={lat:.4f}&lon={lon:.4f}"
    req = urllib.request.Request(url, headers={"User-Agent": "Tempest-V5-Fetcher/1.0 gary@pillay.net"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode('utf-8'))

def process_tempest(loc, api_key, base_dir, out_dir=None):
    station_id = loc.get("station_id")
    title = loc.get("title")
    out_rel = loc.get("out")
    
    if not out_rel:
        return
    
    if out_dir:
        out_path = os.path.join(out_dir, os.path.basename(out_rel))
    else:
        out_path = os.path.join(base_dir, out_rel)

    print(f"Updating Tempest station {station_id} for '{title}'...")
    try:
        raw_data = fetch_tempest_data(station_id, api_key)
    except Exception as e:
        print(f"Error fetching Tempest data for {title} (ID {station_id}): {e}", file=sys.stderr)
        return

    obs_list = raw_data.get("obs", [])
    if not obs_list:
        print(f"Error: No observations in response for {title}", file=sys.stderr)
        return

    obs = obs_list[0]
    latitude = raw_data.get("latitude")
    longitude = raw_data.get("longitude")

    # Fetch Cloud Cover from MET Norway using coordinates
    current_cloud = None
    if latitude is not None and longitude is not None:
        try:
            met_raw = fetch_met_norway_data(latitude, longitude)
            timeseries = met_raw.get("properties", {}).get("timeseries", [])
            if timeseries:
                current_cloud = timeseries[0].get("data", {}).get("instant", {}).get("details", {}).get("cloud_area_fraction")
        except Exception as e:
            print(f"Warning: MET Norway cloud fetch failed for {title}: {e}", file=sys.stderr)

    # Extract metrics
    temp_c = obs.get("air_temperature")
    dew_point_c = obs.get("dew_point")
    humidity = obs.get("relative_humidity")
    wind_avg_mps = obs.get("wind_avg")
    wind_gust_mps = obs.get("wind_gust")
    precip_mm = obs.get("precip")

    # Conversions
    wind_avg_mph = wind_avg_mps * 2.23694 if wind_avg_mps is not None else None
    wind_gust_mph = wind_gust_mps * 2.23694 if wind_gust_mps is not None else None
    dew_point_margin_c = (temp_c - dew_point_c) if (temp_c is not None and dew_point_c is not None) else None
    
    temp_f = (temp_c * 9/5) + 32 if temp_c is not None else None
    dew_point_margin_f = (temp_f - ((dew_point_c * 9/5) + 32)) if (temp_f is not None and dew_point_c is not None) else None

    # Safety limits
    wind_ok = wind_avg_mph <= 28.0 if wind_avg_mph is not None else False
    gust_ok = wind_gust_mph <= 35.0 if wind_gust_mph is not None else False
    humidity_ok = humidity <= 98.0 if humidity is not None else False
    temp_ok = 28.0 <= temp_f <= 110.0 if temp_f is not None else False
    dp_ok = dew_point_margin_f >= 3.0 if dew_point_margin_f is not None else False
    cloud_ok = current_cloud <= 60.0 if current_cloud is not None else True

    items = build_items_list(current_cloud, cloud_ok, wind_avg_mph, wind_ok, wind_gust_mph, gust_ok, 
                             temp_c, temp_ok, humidity, humidity_ok, dew_point_c, dew_point_margin_c, dp_ok, precip_mm)

    write_json_card(title, f"{raw_data.get('station_name', '').strip()} (Tempest Live)", items, out_path)

def process_coordinates(loc, base_dir, out_dir=None):
    title = loc.get("title")
    lat = loc.get("latitude")
    lon = loc.get("longitude")
    out_rel = loc.get("out")

    if not out_rel:
        return
        
    if out_dir:
        out_path = os.path.join(out_dir, os.path.basename(out_rel))
    else:
        out_path = os.path.join(base_dir, out_rel)

    print(f"Updating coordinates ({lat}, {lon}) for '{title}'...")
    try:
        raw_data = fetch_met_norway_data(lat, lon)
    except Exception as e:
        print(f"Error fetching MET Norway data for {title}: {e}", file=sys.stderr)
        return

    properties = raw_data.get("properties", {})
    timeseries = properties.get("timeseries", [])
    if not timeseries:
        print(f"Error: No timeseries found for {title}", file=sys.stderr)
        return

    instant_data = timeseries[0].get("data", {})
    details = instant_data.get("instant", {}).get("details", {})
    
    # precip from next 1 hours
    next_1_hours = instant_data.get("next_1_hours", {})
    precip_mm = next_1_hours.get("data", {}).get("details", {}).get("precipitation_amount", 0.0)

    # metrics
    temp_c = details.get("air_temperature")
    humidity = details.get("relative_humidity")
    wind_avg_mps = details.get("wind_speed")
    wind_gust_mps = details.get("wind_speed_of_gust")
    current_cloud = details.get("cloud_area_fraction")

    # Math & Dew Point Calculation
    wind_avg_mph = wind_avg_mps * 2.23694 if wind_avg_mps is not None else None
    if wind_gust_mps is None and wind_avg_mps is not None:
        wind_gust_mps = wind_avg_mps
    wind_gust_mph = wind_gust_mps * 2.23694 if wind_gust_mps is not None else None
    
    dew_point_c = None
    if temp_c is not None and humidity is not None:
        try:
            b = 17.625
            c = 243.04
            alpha = math.log(humidity / 100.0) + (b * temp_c) / (c + temp_c)
            dew_point_c = (c * alpha) / (b - alpha)
        except Exception:
            pass
            
    dew_point_margin_c = (temp_c - dew_point_c) if (temp_c is not None and dew_point_c is not None) else None
    temp_f = (temp_c * 9/5) + 32 if temp_c is not None else None
    dew_point_margin_f = (temp_f - ((dew_point_c * 9/5) + 32)) if (temp_f is not None and dew_point_c is not None) else None

    # Safety limits
    wind_ok = wind_avg_mph <= 28.0 if wind_avg_mph is not None else False
    gust_ok = wind_gust_mph <= 35.0 if wind_gust_mph is not None else False
    humidity_ok = humidity <= 98.0 if humidity is not None else False
    temp_ok = 28.0 <= temp_f <= 110.0 if temp_f is not None else False
    dp_ok = dew_point_margin_f >= 3.0 if dew_point_margin_f is not None else False
    cloud_ok = current_cloud <= 60.0 if current_cloud is not None else True

    items = build_items_list(current_cloud, cloud_ok, wind_avg_mph, wind_ok, wind_gust_mph, gust_ok, 
                             temp_c, temp_ok, humidity, humidity_ok, dew_point_c, dew_point_margin_c, dp_ok, precip_mm)

    write_json_card(title, f"{lat:.4f}, {lon:.4f} (yr.no Forecast)", items, out_path)

def build_items_list(current_cloud, cloud_ok, wind_avg_mph, wind_ok, wind_gust_mph, gust_ok, 
                     temp_c, temp_ok, humidity, humidity_ok, dew_point_c, dew_point_margin_c, dp_ok, precip_mm):
    items = []
    
    # 1. Cloud
    if current_cloud is not None:
        items.append({
            "label": "Cloud",
            "value": f"{current_cloud:.0f} %",
            "color": "var(--green)" if cloud_ok else "var(--red)"
        })
    else:
        items.append({"label": "Cloud", "value": "-- %", "color": "var(--red)"})

    # 2. Wind/Gust
    if wind_avg_mph is not None and wind_gust_mph is not None:
        items.append({
            "label": "Wind/Gust",
            "value": f"{wind_avg_mph:.1f} / {wind_gust_mph:.1f} mph",
            "color": "var(--green)" if (wind_ok and gust_ok) else "var(--red)"
        })
    elif wind_avg_mph is not None:
        items.append({
            "label": "Wind/Gust",
            "value": f"{wind_avg_mph:.1f} / -- mph",
            "color": "var(--green)" if wind_ok else "var(--red)"
        })
    else:
        items.append({"label": "Wind/Gust", "value": "-- / -- mph", "color": "var(--red)"})

    # 3. Temp
    if temp_c is not None:
        items.append({
            "label": "Temp",
            "value": f"{temp_c:.1f} °C",
            "color": "#fff" if temp_ok else "var(--red)"
        })
    else:
        items.append({"label": "Temp", "value": "--", "color": "#fff"})

    # 4. Humidity
    if humidity is not None:
        items.append({
            "label": "Humidity",
            "value": f"{humidity:.0f} %",
            "color": "#fff" if humidity_ok else "var(--red)"
        })
    else:
        items.append({"label": "Humidity", "value": "--", "color": "#fff"})

    # 5. Dew Pt/Margin
    if dew_point_c is not None and dew_point_margin_c is not None:
        items.append({
            "label": "Dew Pt/Margin",
            "value": f"{dew_point_c:.1f} / {dew_point_margin_c:.1f} °C",
            "color": "#fff" if dp_ok else "var(--red)"
        })
    else:
        items.append({"label": "Dew Pt/Margin", "value": "-- / --", "color": "#fff"})

    # 6. Precip
    if precip_mm is not None:
        items.append({
            "label": "Precip",
            "value": f"{precip_mm:.2f} mm",
            "color": "#fff"
        })
    else:
        items.append({"label": "Precip", "value": "--", "color": "#fff"})
        
    return items

def write_json_card(title, subtitle, items, out_path):
    card_data = {
        "title": title,
        "subtitle": subtitle,
        "type": "list",
        "data": {
            "items": items
        }
    }
    
    out_dir = os.path.dirname(out_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
        
    temp_out = f"{out_path}.tmp"
    try:
        with open(temp_out, "w") as f:
            json.dump(card_data, f, indent=2)
        os.replace(temp_out, out_path)
        print(f"Successfully updated {out_path} for '{title}'")
    except Exception as e:
        print(f"Error writing to {out_path}: {e}", file=sys.stderr)

def fetch_weather(api_key, out_dir, config_path):
    if not os.path.exists(config_path):
        print(f"Error: Config file not found at {config_path}", file=sys.stderr)
        return

    with open(config_path, "r") as f:
        config_data = json.load(f)

    # Determine project root based on the script location
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir) # parent of Tempest/

    locations = config_data.get("locations", [])
    for loc in locations:
        source = loc.get("source")
        if source == "tempest":
            process_tempest(loc, api_key, project_root, out_dir)
        elif source == "coordinates":
            process_coordinates(loc, project_root, out_dir)
        else:
            print(f"Warning: Unknown source '{source}' for location '{loc.get('title')}'")

def main():
    parser = argparse.ArgumentParser(description="Master weather updater for SFRO Dashboard V5.")
    parser.add_argument("-c", "--config", help="Path to locations config JSON")
    parser.add_argument("-k", "--api-key", default=os.environ.get("TEMPEST_API_KEY", DEFAULT_API_KEY), help="Tempest API Key")
    parser.add_argument("-o", "--out-dir", help="Output directory override for compiled JSONs")
    args = parser.parse_args()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = args.config if args.config else os.path.join(script_dir, "locations.json")

    fetch_weather(args.api_key, args.out_dir, config_path)

if __name__ == "__main__":
    main()
