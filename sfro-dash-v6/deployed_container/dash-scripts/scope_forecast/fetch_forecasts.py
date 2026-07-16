#!/usr/bin/env python3
import sys
import urllib.request
import json
import os
import argparse
from datetime import datetime

def fetch_json(url):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            return json.loads(response.read().decode('utf-8'))
    except Exception as e:
        print(f"Error fetching API {url}: {e}", file=sys.stderr)
        return None

def load_local_json(filepath):
    if not os.path.exists(filepath):
        return None
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error reading local file {filepath}: {e}", file=sys.stderr)
        return None

def get_scheduled_targets(data):
    if not data:
        return "No forecast data available."
        
    fc_keys = [k for k in data.keys() if k.endswith('_forecast')]
    if not fc_keys:
        return "No upcoming forecast found."
        
    latest_fc_key = sorted(fc_keys)[-1]
    fc_record = data[latest_fc_key]
    
    # Get nautical dusk for filtering waits
    naut_dusk_str = fc_record.get("astral", {}).get("nautical_dusk", "2099-01-01T00:00:00")
    try:
        naut_dusk = datetime.fromisoformat(naut_dusk_str)
    except Exception:
        naut_dusk = datetime.min
        
    events = []
    
    # Process targets
    targets = fc_record.get("events", {}).get("targets", [])
    for t in targets:
        name = t.get("name", "Unknown Target")
        start_str = t.get("start")
        try:
            start_dt = datetime.fromisoformat(start_str)
            events.append({
                "time": start_dt,
                "label": name
            })
        except Exception:
            continue
            
    # Process waits
    waits = fc_record.get("events", {}).get("target_waits", [])
    for w in waits:
        start_str = w.get("start")
        end_str = w.get("end")
        try:
            start_dt = datetime.fromisoformat(start_str)
            end_dt = datetime.fromisoformat(end_str)
            
            # Filter wait states: only show if wait ends after nautical dusk
            if end_dt > naut_dusk:
                start_label = start_dt.strftime("%H:%M")
                end_label = end_dt.strftime("%H:%M")
                events.append({
                    "time": start_dt,
                    "label": f"<span style='color: #facc15; font-weight: bold;'>Wait ({start_label} - {end_label})</span>"
                })
        except Exception:
            continue
            
    if not events:
        return "No targets scheduled for tonight."
        
    # Sort chronologically by start time
    events.sort(key=lambda x: x["time"])
    
    lines = [f"• {e['label']}" for e in events]
    return "\n".join(lines)

def main():
    parser = argparse.ArgumentParser(description="Fetch planned NINA target schedules for the scopes and generate text card JSONs.")
    parser.add_argument("-o", "--out-dir", default="v5-test/data", help="Output directory for JSON files")
    parser.add_argument("--host", default="http://192.168.1.51:5002", help="Remote dashboard host log API")
    parser.add_argument("--local-dir", help="Optional local directory to read log files from directly (instead of API)")
    parser.add_argument("--title-fra", default="FRA400 Forecast", help="Card Title for FRA400")
    parser.add_argument("--title-q75", default="75Q Forecast", help="Card Title for 75Q")
    args = parser.parse_args()
    
    os.makedirs(args.out_dir, exist_ok=True)
    
    scopes_config = {
        "fra400": {
            "log_file": "FRA400_log.json",
            "out_file": "nina_fra400.json",
            "title": args.title_fra
        },
        "75q": {
            "log_file": "75Q_log.json",
            "out_file": "nina_75q.json",
            "title": args.title_q75
        }
    }
    
    for scope_key, config in scopes_config.items():
        data = None
        
        # Load from local dir if provided, otherwise query remote API
        if args.local_dir:
            local_path = os.path.join(args.local_dir, config["log_file"])
            print(f"Reading local logs for {scope_key.upper()} from {local_path}...")
            data = load_local_json(local_path)
        else:
            api_url = f"{args.host}/data/{config['log_file']}"
            print(f"Fetching remote logs for {scope_key.upper()} from {api_url}...")
            data = fetch_json(api_url)
            
        targets_text = get_scheduled_targets(data)
        
        # Extract forecast date if available to add as subtitle
        subtitle_date = ""
        if data:
            fc_keys = [k for k in data.keys() if k.endswith('_forecast')]
            if fc_keys:
                subtitle_date = f"Tonight ({sorted(fc_keys)[-1].replace('_forecast', '')})"
                
        # Build JSON card payload
        card_data = {
            "title": config["title"],
            "subtitle": subtitle_date,
            "type": "text",
            "data": {
                "text": targets_text
            }
        }
        
        out_path = os.path.join(args.out_dir, config["out_file"])
        temp_path = f"{out_path}.tmp"
        try:
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(card_data, f, indent=2)
            os.replace(temp_path, out_path)
            print(f"  [✓] Successfully updated {out_path}")
        except Exception as e:
            print(f"  [!] Failed to write {out_path}: {e}", file=sys.stderr)

if __name__ == "__main__":
    main()
