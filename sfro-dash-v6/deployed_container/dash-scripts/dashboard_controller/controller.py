#!/usr/bin/env python3
import sys
import os
import json
import argparse
import subprocess
from datetime import datetime, timezone

# Resolve project root directory
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def load_json(path, default=None):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return default

def save_json(path, data):
    try:
        temp_path = f"{path}.tmp"
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        os.replace(temp_path, path)
    except Exception as e:
        print(f"Error saving {path}: {e}", file=sys.stderr)

def read_text_report(path, fallback=""):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except:
        return fallback

def summarize_backup_report(txt):
    if not txt or "Awaiting" in txt or "No data transferred" in txt:
        return txt
        
    lines = txt.split('\n')
    summary_lines = []
    
    current_category = None
    count = 0
    
    for line in lines:
        if "📊" in line or "Timeframe" in line:
            summary_lines.append(line)
        elif "Shares**:" in line:
            if current_category is not None:
                summary_lines.append(f"{current_category.replace(':', '')} {count} shares updated")
            current_category = line.strip()
            count = 0
        elif line.startswith("- "):
            count += 1
        elif "Total Data" in line:
            if current_category is not None:
                summary_lines.append(f"{current_category.replace(':', '')} {count} shares updated")
                current_category = None
            summary_lines.append("")
            summary_lines.append(line)
            
    if current_category is not None:
        summary_lines.append(f"{current_category.replace(':', '')} {count} shares updated")
        
    return "\n".join(summary_lines)

def run_subscript(script_rel_path, out_dir, extra_args=[]):
    target = os.path.join(ROOT_DIR, script_rel_path)
    if os.path.exists(target):
        cmd = [sys.executable, target, "-o", out_dir] + extra_args
        subprocess.run(cmd, check=False)

def update_dashboard(out_dir):
    os.makedirs(out_dir, exist_ok=True)
    
    reports_dir = os.path.join(out_dir, "reports")
    os.makedirs(reports_dir, exist_ok=True)

    schema_path = os.path.join(out_dir, "active_schema.json")
    schema_data = load_json(schema_path, {"schema": "RoofClosedNight1"})
    schema = schema_data.get("schema", "RoofClosedNight1")
    
    print(f"Controller executing for schema: {schema}")

    # ---------------------------------------------------------
    # Strict Finite State Machine Matrix
    # ---------------------------------------------------------
    # Each schema maps to explicit modes for each card slot.
    state_matrix = {
        "RoofClosedMorning1": {"fra400": "apod", "75q": "backup", "weather": "wandsworth", "captures": "rates"},
        "RoofClosedLunch1": {"fra400": "apod", "75q": "backup", "weather": "wandsworth", "captures": "rates"},
        "Afternoon1": {"fra400": "apod", "75q": "backup", "weather": "wandsworth", "captures": "rates"},
        "Supper1": {"fra400": "nightb", "75q": "backup", "weather": "wandsworth", "captures": "rates"},
        "RoofClosedEvening1": {"fra400": "apod", "75q": "backup", "weather": "wandsworth", "captures": "rates"},
        "RoofClosedNight1": {"fra400": "apod", "75q": "backup", "weather": "wandsworth", "captures": "rates"},
        "RoofClosedDawn1": {"fra400": "apod", "75q": "backup", "weather": "wandsworth", "captures": "rates"},
        
        "RoofOpenMorning1": {"fra400": "live", "75q": "live", "weather": "starfront", "captures": "nina"},
        "RoofOpenLunch1": {"fra400": "live", "75q": "live", "weather": "starfront", "captures": "nina"},
        "RoofOpenEvening1": {"fra400": "nightb", "75q": "nighta", "weather": "starfront", "captures": "nina"},
        "RoofOpenNight1": {"fra400": "live", "75q": "live", "weather": "starfront", "captures": "nina"},
        "RoofOpenDawn1": {"fra400": "live", "75q": "live", "weather": "starfront", "captures": "nina"},
    }
    
    # Default fallback if schema is unknown
    active_state = state_matrix.get(schema, {"fra400": "live", "75q": "live", "weather": "starfront", "captures": "nina"})
    
    # We no longer run data scrapers here (run_subscript removed).
    # They are executed on their own dedicated schedules by daemon.py.
        
    # ---------------------------------------------------------
    # Execute Actions Based on Active State
    # ---------------------------------------------------------
    
    # 1. Skycam (Always live, except Supper1)
    if os.path.exists(os.path.join(out_dir, "custom_skycam.json")):
        save_json(os.path.join(out_dir, "skycam.json"), load_json(os.path.join(out_dir, "custom_skycam.json")))
    elif schema == "Supper1":
        apod_data = load_json(os.path.join(ROOT_DIR, "apod", "apod.json"), {"url": "./images/apod_fallback.jpg", "title": "APOD"})
        save_json(os.path.join(out_dir, "skycam.json"), {
            "title": "NASA APOD", "subtitle": apod_data.get("title", ""), "type": "image",
            "data": {"src": apod_data.get("url", ""), "alt": "APOD"}
        })
    else:
        save_json(os.path.join(out_dir, "skycam.json"), {
            "title": "Live All-Sky Camera", "subtitle": "Connected", "type": "image",
            "data": {"src": "https://files-api.tx.starfront.space/status-assets-public/building-0009/allsky/images/image.jpg", "alt": "All-Sky"}
        })

    # 2. FRA400 Image
    if os.path.exists(os.path.join(out_dir, "custom_fra400.json")):
        save_json(os.path.join(out_dir, "fra400.json"), load_json(os.path.join(out_dir, "custom_fra400.json")))
    elif active_state["fra400"] == "apod":
        apod_data = load_json(os.path.join(ROOT_DIR, "apod", "apod.json"), {"url": "./images/apod_fallback.jpg", "title": "APOD"})
        save_json(os.path.join(out_dir, "fra400.json"), {
            "title": "NASA APOD", "subtitle": apod_data.get("title", ""), "type": "image",
            "data": {"src": apod_data.get("url", ""), "alt": "APOD"}
        })
    elif active_state["fra400"] == "nightb":
        save_json(os.path.join(out_dir, "fra400.json"), {
            "title": "FRA400 Night B", "subtitle": "Local file", "type": "image",
            "data": {"src": "./images/NightB.jpg", "alt": "Night B"}
        })
    elif active_state["fra400"] == "live":
        raw = load_json(os.path.join(out_dir, "fra400_raw.json"))
        if raw: 
            save_json(os.path.join(out_dir, "fra400.json"), raw)
        else:
            # FALLBACK: No images yet
            astrospheric_embed = (
                "<div id=\"AstrosphericEmbedContainer\" style=\"width: 100%; height: 100%; border-radius: 8px; overflow: hidden;\">"
                "<div style=\"display:flex; justify-content:center; align-items:center; height:100%; color:#94a3b8;\">Loading Astrospheric...</div>"
                "</div>"
            )
            save_json(os.path.join(out_dir, "fra400.json"), {
                "title": "Pending first image", "subtitle": "Astrospheric Forecast", "type": "text",
                "data": {"text": astrospheric_embed}
            })

    # 3. 75Q Image
    if os.path.exists(os.path.join(out_dir, "custom_75q.json")):
        save_json(os.path.join(out_dir, "75q.json"), load_json(os.path.join(out_dir, "custom_75q.json")))
    elif active_state["75q"] == "backup":
        txt = read_text_report(os.path.join(reports_dir, "backup.txt"), "Awaiting Backup Report...")
        summary_txt = summarize_backup_report(txt)
        save_json(os.path.join(out_dir, "75q.json"), {
            "title": "Daily Backup Volume Report", "subtitle": "Hermes Agent", "type": "text", "data": {"text": summary_txt}
        })
    elif active_state["75q"] == "nighta":
        save_json(os.path.join(out_dir, "75q.json"), {
            "title": "75Q Night A", "subtitle": "Local file", "type": "image",
            "data": {"src": "./images/NightA.jpg", "alt": "Night A"}
        })
    elif active_state["75q"] == "live":
        raw = load_json(os.path.join(out_dir, "75q_raw.json"))
        if raw: 
            save_json(os.path.join(out_dir, "75q.json"), raw)
        else:
            # FALLBACK: No images yet
            q75_forecast = load_json(os.path.join(out_dir, "nina_75q.json"))
            if q75_forecast:
                # Rename the title to match the image state requirement
                q75_forecast["title"] = "Observatory Forecast"
                save_json(os.path.join(out_dir, "75q.json"), q75_forecast)

    # 4. Roofbox Card (Discord Overrides)
    if os.path.exists(os.path.join(out_dir, "custom_roof.json")):
        save_json(os.path.join(out_dir, "roof.json"), load_json(os.path.join(out_dir, "custom_roof.json")))
    else:
        roof_data = load_json(os.path.join(out_dir, "roof.json"), {})
        if "Closed" in schema or schema in ["Afternoon1", "Supper1", "RoofOpenEvening1"]:
            hermes_summary = read_text_report(os.path.join(reports_dir, "roof_forecast_summary.txt"), "Awaiting Hermes analysis...")
            if "data" in roof_data:
                wait_alert = ""
                fra_text = load_json(os.path.join(out_dir, "nina_fra400.json"), {}).get("data", {}).get("text", "")
                q75_text = load_json(os.path.join(out_dir, "nina_75q.json"), {}).get("data", {}).get("text", "")
                if "Wait (" in fra_text or "Wait (" in q75_text:
                    wait_alert = "🚨 **ALERT: Wait state forecast for tonight** 🚨\n\n"
                    
                roof_data["data"]["details"] = f"{wait_alert}**Starfront Forecast:**\n{hermes_summary}"
                save_json(os.path.join(out_dir, "roof.json"), roof_data)

    # 5. Atmos Cards
    if active_state["weather"] == "wandsworth":
        left_data = load_json(os.path.join(out_dir, "atmos_wandsworth.json"))
        right_data = load_json(os.path.join(out_dir, "atmos_umhlanga.json"))
    else:
        left_data = load_json(os.path.join(out_dir, "atmos_starfront.json"))
        right_data = load_json(os.path.join(out_dir, "atmos_umhlanga.json"))
        
    if left_data: save_json(os.path.join(out_dir, "atmos_left.json"), left_data)
    if right_data: save_json(os.path.join(out_dir, "atmos_right.json"), right_data)

    # 6. Capture Cards
    if os.path.exists(os.path.join(out_dir, "custom_fra400cap.json")):
        save_json(os.path.join(out_dir, "fra400cap.json"), load_json(os.path.join(out_dir, "custom_fra400cap.json")))
    elif active_state.get("captures") == "rates":
        rates_left = load_json(os.path.join(out_dir, "rates_left.json"))
        if rates_left: save_json(os.path.join(out_dir, "fra400cap.json"), rates_left)
    else:
        nina_fra = load_json(os.path.join(out_dir, "nina_fra400.json"))
        if nina_fra: save_json(os.path.join(out_dir, "fra400cap.json"), nina_fra)

    if os.path.exists(os.path.join(out_dir, "custom_q75cap.json")):
        save_json(os.path.join(out_dir, "q75cap.json"), load_json(os.path.join(out_dir, "custom_q75cap.json")))
    elif active_state.get("captures") == "rates":
        rates_right = load_json(os.path.join(out_dir, "rates_right.json"))
        if rates_right: save_json(os.path.join(out_dir, "q75cap.json"), rates_right)
    else:
        nina_75q = load_json(os.path.join(out_dir, "nina_75q.json"))
        if nina_75q: save_json(os.path.join(out_dir, "q75cap.json"), nina_75q)

def main():
    parser = argparse.ArgumentParser(description="Master controller to route dashboard cards based on schema.")
    parser.add_argument("-o", "--out-dir", default="v5-test/data", help="Output directory for JSON files")
    args = parser.parse_args()
    update_dashboard(args.out_dir)

if __name__ == "__main__":
    main()
