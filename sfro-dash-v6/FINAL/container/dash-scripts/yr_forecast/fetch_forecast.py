#!/usr/bin/env python3
import urllib.request
import json
import os
import sys
import argparse
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import time

def main():
    parser = argparse.ArgumentParser(description="Fetch hourly weather forecast from yr.no (MET Norway) for Wandsworth and compile it for V5 Dashboard.")
    parser.add_argument("--lat", default=51.45695971753735, type=float, help="Latitude")
    parser.add_argument("--lon", default=-0.18686539472508437, type=float, help="Longitude")
    parser.add_argument("-t", "--title", default="Observatory Forecast", help="Card Title")
    parser.add_argument("-s", "--subtitle", default="London/Wandsworth", help="Card Subtitle")
    parser.add_argument("-z", "--timezone", default="Europe/London", help="Timezone of the station location")
    parser.add_argument("-n", "--hours", type=int, default=8, help="Number of hours to forecast")
    parser.add_argument("--sunset", help="Sunset time for event insertion (e.g. 17:15)")
    parser.add_argument("--sunrise", help="Sunrise time for event insertion (e.g. 05:30)")
    parser.add_argument("-o", "--out", default="v5-test/data/forecast.json", help="Output JSON path")
    args = parser.parse_args()

    url = f"https://api.met.no/weatherapi/locationforecast/2.0/compact?lat={args.lat:.4f}&lon={args.lon:.4f}"
    
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Tempest-V5-Fetcher/1.0 gary@pillay.net"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw_data = json.loads(resp.read().decode('utf-8'))
    except Exception as e:
        print(f"Error fetching forecast from MET Norway API: {e}", file=sys.stderr)
        sys.exit(1)

    properties = raw_data.get("properties", {})
    timeseries = properties.get("timeseries", [])
    if not timeseries:
        print("Error: No weather timeseries found in API response.", file=sys.stderr)
        sys.exit(1)

    # Establish target timezone
    try:
        tz = ZoneInfo(args.timezone)
    except Exception as e:
        print(f"Warning: Timezone '{args.timezone}' not recognized. Falling back to local system timezone. Error: {e}", file=sys.stderr)
        tz = datetime.now().astimezone().tzinfo

    # Determine dynamic starting time in the target timezone
    # "step forward to the next hour from 45 minutes past the previous hour"
    now_in_tz = datetime.now(tz)
    if now_in_tz.minute >= 45:
        # Step forward to the next hour (e.g. 13:45 -> 14:00)
        start_dt = (now_in_tz + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
    else:
        # Round down to the current hour (e.g. 13:44 -> 13:00)
        start_dt = now_in_tz.replace(minute=0, second=0, microsecond=0)

    start_ts = start_dt.timestamp()

    # Define events list (e.g. Sunset / Sunrise) relative to the target local date
    events = []
    
    # Generate local date strings for today and tomorrow to support overnight boundaries
    local_dates = [
        start_dt.strftime("%Y-%m-%d"),
        (start_dt + timedelta(days=1)).strftime("%Y-%m-%d")
    ]
    
    for date_str in local_dates:
        sunset_time = args.sunset
        sunrise_time = args.sunrise
        
        if not sunset_time or not sunrise_time:
            try:
                api_url = f"https://api.sunrise-sunset.org/json?lat={args.lat:.4f}&lng={args.lon:.4f}&date={date_str}&formatted=0"
                req_ss = urllib.request.Request(api_url, headers={"User-Agent": "Tempest-V5-Fetcher/1.0 gary@pillay.net"})
                with urllib.request.urlopen(req_ss, timeout=5) as resp_ss:
                    ss_data = json.loads(resp_ss.read().decode('utf-8'))
                if ss_data.get("status") == "OK":
                    results = ss_data.get("results", {})
                    if not sunrise_time:
                        sunrise_utc = datetime.fromisoformat(results["sunrise"])
                        sunrise_local = sunrise_utc.astimezone(tz)
                        sunrise_time = sunrise_local.strftime("%H:%M")
                    if not sunset_time:
                        sunset_utc = datetime.fromisoformat(results["sunset"])
                        sunset_local = sunset_utc.astimezone(tz)
                        sunset_time = sunset_local.strftime("%H:%M")
            except Exception as e:
                print(f"Warning: Failed to dynamically fetch sunrise/sunset for {date_str}: {e}", file=sys.stderr)
        
        if sunset_time:
            try:
                # Parse relative to the target local timezone
                sunset_naive = datetime.strptime(f"{date_str} {sunset_time}", "%Y-%m-%d %H:%M")
                sunset_dt = sunset_naive.replace(tzinfo=tz)
                events.append({
                    "timestamp": sunset_dt.timestamp(),
                    "time": sunset_time,
                    "symbol_code": "sunset",
                    "event": "Sunset"
                })
            except Exception as e:
                print(f"Warning: Failed to parse sunset time for {date_str}: {e}", file=sys.stderr)
    
        if sunrise_time:
            try:
                # Parse relative to the target local timezone
                sunrise_naive = datetime.strptime(f"{date_str} {sunrise_time}", "%Y-%m-%d %H:%M")
                sunrise_dt = sunrise_naive.replace(tzinfo=tz)
                events.append({
                    "timestamp": sunrise_dt.timestamp(),
                    "time": sunrise_time,
                    "symbol_code": "sunrise",
                    "event": "Sunrise"
                })
            except Exception as e:
                print(f"Warning: Failed to parse sunrise time for {date_str}: {e}", file=sys.stderr)

    # Sort events by timestamp
    events.sort(key=lambda x: x["timestamp"])

    # Filter timeseries to only include current and future hours (starting from start_ts)
    future_timeseries = []
    for entry in timeseries:
        time_str = entry.get("time")
        try:
            dt_utc = datetime.strptime(time_str, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
            ts = dt_utc.timestamp()
            if ts >= start_ts:
                future_timeseries.append(entry)
        except Exception:
            continue

    timeline = []
    prev_ts = None
    
    # We loop through a slightly larger window in case events are inserted,
    # then slice the final timeline array to exactly args.hours.
    for entry in future_timeseries[:args.hours + len(events)]:
        time_str = entry.get("time")
        try:
            dt_utc = datetime.strptime(time_str, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
            ts = dt_utc.timestamp()
            # Format time label in the location's local timezone (including DST)
            local_dt = dt_utc.astimezone(tz)
            time_label = local_dt.strftime("%H:00")
        except Exception:
            continue

        # Chronologically insert event if it falls between the previous and current timestamp
        if prev_ts is not None:
            for ev in events:
                if prev_ts < ev["timestamp"] <= ts:
                    timeline.append({
                        "time": ev["time"],
                        "symbol_code": ev["symbol_code"],
                        "event": ev["event"]
                    })

        data = entry.get("data", {})
        details = data.get("instant", {}).get("details", {})
        
        temp = details.get("air_temperature")
        cloud = details.get("cloud_area_fraction")
        wind_mps = details.get("wind_speed")
        wind_mph = wind_mps * 2.23694 if wind_mps is not None else None
        
        # Extract hourly precipitation
        next_1_hours = data.get("next_1_hours", {})
        precip = next_1_hours.get("data", {}).get("details", {}).get("precipitation_amount", 0.0)
        
        # Get symbol code from next 1 hours (or next 6 hours fallback)
        symbol_code = data.get("next_1_hours", {}).get("summary", {}).get("symbol_code", "")
        if not symbol_code:
            symbol_code = data.get("next_6_hours", {}).get("summary", {}).get("symbol_code", "")

        timeline.append({
            "time": time_label,
            "temp": temp,
            "cloud": cloud,
            "symbol_code": symbol_code,
            "wind": wind_mph,
            "precip": precip
        })
        
        prev_ts = ts

    # Slices to exactly args.hours to replace standard hourly columns with events
    timeline = timeline[:args.hours]

    # Wrap in universal card response
    card_data = {
        "title": args.title,
        "subtitle": args.subtitle,
        "type": "forecast",
        "data": {
            "timeline": timeline
        }
    }

    # Write output atomically
    out_dir = os.path.dirname(args.out)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    temp_out = f"{args.out}.tmp"
    try:
        with open(temp_out, "w") as f:
            json.dump(card_data, f, indent=2)
        os.replace(temp_out, args.out)
        print(f"Successfully updated forecast at {args.out} for {args.subtitle}")
    except Exception as e:
        print(f"Error writing output file: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
