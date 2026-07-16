#!/usr/bin/env python3
import urllib.request
import json
import os
import sys
import argparse

import math

def main():
    parser = argparse.ArgumentParser(description="Fetch coordinate weather from MET Norway (yr.no) and output in V5 Universal List format.")
    parser.add_argument("--lat", required=True, type=float, help="Latitude")
    parser.add_argument("--lon", required=True, type=float, help="Longitude")
    parser.add_argument("-t", "--title", default="Weather Station", help="Custom Title for the Card")
    parser.add_argument("-o", "--out", default="v5-test/data/atmos_right.json", help="Output JSON path")
    args = parser.parse_args()

    url = f"https://api.met.no/weatherapi/locationforecast/2.0/compact?lat={args.lat:.4f}&lon={args.lon:.4f}"
    
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Tempest-V5-Fetcher/1.0 gary@pillay.net"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw_data = json.loads(resp.read().decode('utf-8'))
    except Exception as e:
        print(f"Error fetching data from MET Norway API: {e}", file=sys.stderr)
        sys.exit(1)

    properties = raw_data.get("properties", {})
    timeseries = properties.get("timeseries", [])
    if not timeseries:
        print("Error: No weather timeseries found in API response.", file=sys.stderr)
        sys.exit(1)

    # Extract current instant observations
    instant_data = timeseries[0].get("data", {})
    details = instant_data.get("instant", {}).get("details", {})
    
    # Extract precip from next 1 hours
    next_1_hours = instant_data.get("next_1_hours", {})
    precip_mm = next_1_hours.get("data", {}).get("details", {}).get("precipitation_amount", 0.0)

    # Extract metrics
    temp_c = details.get("air_temperature")
    humidity = details.get("relative_humidity")
    wind_avg_mps = details.get("wind_speed")
    wind_gust_mps = details.get("wind_speed_of_gust")
    current_cloud = details.get("cloud_area_fraction")

    # Calculate dew point using Magnus-Tetens formula (compact API does not supply it)
    dew_point_c = None
    if temp_c is not None and humidity is not None:
        try:
            b = 17.625
            c = 243.04
            alpha = math.log(humidity / 100.0) + (b * temp_c) / (c + temp_c)
            dew_point_c = (c * alpha) / (b - alpha)
        except Exception:
            pass

    # Perform conversions & math
    wind_avg_mph = wind_avg_mps * 2.23694 if wind_avg_mps is not None else None
    
    # Use average wind if gust is not supplied by API
    if wind_gust_mps is None and wind_avg_mps is not None:
        wind_gust_mps = wind_avg_mps
    wind_gust_mph = wind_gust_mps * 2.23694 if wind_gust_mps is not None else None
    
    dew_point_margin_c = (temp_c - dew_point_c) if (temp_c is not None and dew_point_c is not None) else None
    
    temp_f = (temp_c * 9/5) + 32 if temp_c is not None else None
    dew_point_margin_f = (temp_f - ((dew_point_c * 9/5) + 32)) if (temp_f is not None and dew_point_c is not None) else None

    # Safety limits evaluation (using V4 thresholds)
    wind_ok = wind_avg_mph <= 28.0 if wind_avg_mph is not None else False
    gust_ok = wind_gust_mph <= 35.0 if wind_gust_mph is not None else False
    humidity_ok = humidity <= 98.0 if humidity is not None else False
    temp_ok = 28.0 <= temp_f <= 110.0 if temp_f is not None else False
    dp_ok = dew_point_margin_f >= 3.0 if dew_point_margin_f is not None else False
    cloud_ok = current_cloud <= 60.0 if current_cloud is not None else True

    # Compile item rows in the requested order and layout
    items = []
    
    # Row 1: Cloud
    if current_cloud is not None:
        items.append({
            "label": "Cloud",
            "value": f"{current_cloud:.0f} %",
            "color": "var(--green)" if cloud_ok else "var(--red)"
        })
    else:
        items.append({"label": "Cloud", "value": "-- %", "color": "var(--red)"})

    # Row 2: Wind/Gust
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

    # Row 3: Temp
    if temp_c is not None:
        items.append({
            "label": "Temp",
            "value": f"{temp_c:.1f} °C",
            "color": "#fff" if temp_ok else "var(--red)"
        })
    else:
        items.append({"label": "Temp", "value": "--", "color": "#fff"})

    # Row 4: Humidity
    if humidity is not None:
        items.append({
            "label": "Humidity",
            "value": f"{humidity:.0f} %",
            "color": "#fff" if humidity_ok else "var(--red)"
        })
    else:
        items.append({"label": "Humidity", "value": "--", "color": "#fff"})

    # Row 5: Dew Pt/Margin
    if dew_point_c is not None and dew_point_margin_c is not None:
        items.append({
            "label": "Dew Pt/Margin",
            "value": f"{dew_point_c:.1f} / {dew_point_margin_c:.1f} °C",
            "color": "#fff" if dp_ok else "var(--red)"
        })
    else:
        items.append({"label": "Dew Pt/Margin", "value": "-- / --", "color": "#fff"})

    # Compile the final card data
    card_data = {
        "title": args.title,
        "subtitle": f"{args.lat:.4f}, {args.lon:.4f}",
        "type": "list",
        "data": {
            "items": items
        }
    }

    # Atomically write output
    out_dir = os.path.dirname(args.out)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    temp_out = f"{args.out}.tmp"
    try:
        with open(temp_out, "w") as f:
            json.dump(card_data, f, indent=2)
        os.replace(temp_out, args.out)
        print(f"Successfully updated {args.out} using coordinates ({args.lat}, {args.lon}) (Title: {args.title})")
    except Exception as e:
        print(f"Error writing output file: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
