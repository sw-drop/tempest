#!/usr/bin/env python3
import urllib.request
import json
import os
import sys
import argparse

DEFAULT_API_KEY = "6bff2f89-84ab-463c-886e-fc0f443da4cf"

def main():
    parser = argparse.ArgumentParser(description="Fetch Tempest weather station data and output in V5 Universal List format.")
    parser.add_argument("-s", "--station-id", required=True, help="Tempest Station ID")
    parser.add_argument("-k", "--api-key", default=os.environ.get("TEMPEST_API_KEY", DEFAULT_API_KEY), help="Tempest API Key")
    parser.add_argument("-t", "--title", default="Atmospheric Parameters", help="Custom Title for the Card")
    parser.add_argument("-o", "--out", default="v5-test/data/atmos.json", help="Output JSON path")
    args = parser.parse_args()

    # 1. Fetch current observations from Tempest
    url = f"https://swd.weatherflow.com/swd/rest/observations/station/{args.station_id}?api_key={args.api_key}"
    
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Tempest-V5-Fetcher/1.0 gary@pillay.net"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw_data = json.loads(resp.read().decode('utf-8'))
    except Exception as e:
        print(f"Error fetching data from Tempest API: {e}", file=sys.stderr)
        sys.exit(1)

    obs_list = raw_data.get("obs", [])
    if not obs_list:
        print("Error: No observations found in API response.", file=sys.stderr)
        sys.exit(1)

    obs = obs_list[0]

    # Extract coordinates
    latitude = raw_data.get("latitude")
    longitude = raw_data.get("longitude")

    # 2. Fetch cloud cover from MET Norway (compact API)
    current_cloud = None
    if latitude is not None and longitude is not None:
        met_url = f"https://api.met.no/weatherapi/locationforecast/2.0/compact?lat={latitude:.4f}&lon={longitude:.4f}"
        try:
            req_met = urllib.request.Request(met_url, headers={"User-Agent": "Tempest-V5-Fetcher/1.0 gary@pillay.net"})
            with urllib.request.urlopen(req_met, timeout=10) as resp:
                met_raw = json.loads(resp.read().decode('utf-8'))
                timeseries = met_raw.get("properties", {}).get("timeseries", [])
                if timeseries:
                    current_cloud = timeseries[0].get("data", {}).get("instant", {}).get("details", {}).get("cloud_area_fraction")
        except Exception as e:
            print(f"Warning: MET Norway cloud forecast fetch failed: {e}", file=sys.stderr)

    # Extract Tempest metrics
    temp_c = obs.get("air_temperature")
    dew_point_c = obs.get("dew_point")
    humidity = obs.get("relative_humidity")
    wind_avg_mps = obs.get("wind_avg")
    wind_gust_mps = obs.get("wind_gust")

    # Perform conversions & math
    wind_avg_mph = wind_avg_mps * 2.23694 if wind_avg_mps is not None else None
    wind_gust_mph = wind_gust_mps * 2.23694 if wind_gust_mps is not None else None
    dew_point_margin_c = (temp_c - dew_point_c) if (temp_c is not None and dew_point_c is not None) else None
    
    temp_f = (temp_c * 9/5) + 32 if temp_c is not None else None
    dew_point_margin_f = (temp_f - ((dew_point_c * 9/5) + 32)) if (temp_f is not None and dew_point_c is not None) else None

    # Safety limits evaluation
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
            "value": f"{humidity} %",
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
        "subtitle": raw_data.get("station_name", "Station Nominal").strip(),
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
        print(f"Successfully updated {args.out} for station {args.station_id} (Title: {args.title})")
    except Exception as e:
        print(f"Error writing output file: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
