# discord_extractor.py v1.4.15

import os
import json
import csv
import sqlite3
import datetime
import pytz
import time
import requests
from astral import LocationInfo
from astral.sun import dusk, dawn

# ==================== CONFIGURATION ====================
TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise ValueError("DISCORD_TOKEN environment variable not set.")

START_DATE = os.getenv("START_DATE", "2025-12-10") 

DATA_DIR = "data"
STATE_DB = os.path.join(DATA_DIR, "state.db")

LAT = float(os.getenv("LAT", "31.546944"))
LON = float(os.getenv("LON", "-99.382222"))
ALTITUDE = float(os.getenv("ALTITUDE", "466"))
TIMEZONE = os.getenv("TIMEZONE", "America/Chicago")

SCOPES_ENV = os.getenv("SCOPES", "FRA400:1407795208200126516,75Q:1440079351516237864")
ROOF_CHANNEL = os.getenv("ROOF_CHANNEL", "1448055610523259102")

CHANNELS = {}
for pair in SCOPES_ENV.split(","):
    name, cid = pair.split(":")
    CHANNELS[int(cid.strip())] = name.strip()
if ROOF_CHANNEL:
    CHANNELS[int(ROOF_CHANNEL.strip())] = "Roof"

HEADERS = {"Authorization": f"Bot {TOKEN}", "User-Agent": "StarfrontDashboard/1.0"}
CENTRAL_TZ = pytz.timezone(TIMEZONE)

IGNORE_LIST = ["downloaded", "messages so far", "scanning", "scanned", "loop detected", "checked", "events found"]
# =======================================================

os.makedirs(DATA_DIR, exist_ok=True)
loc = LocationInfo("Starfront", "Texas", TIMEZONE, LAT, LON)

def normalize_time(timestamp_str):
    dt = datetime.datetime.fromisoformat(timestamp_str)
    if dt.tzinfo is None: dt = pytz.utc.localize(dt)
    return dt.astimezone(CENTRAL_TZ).isoformat()

def date_to_snowflake(date_str):
    dt = datetime.datetime.strptime(date_str, "%Y-%m-%d")
    dt = pytz.utc.localize(dt)
    ms_since_epoch = int((dt.timestamp() * 1000) - 1420070400000)
    return str(ms_since_epoch << 22)

def fetch_discord_messages(channel_id, channel_name, triggers, after_id=None):
    messages = []
    url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
    current_after = after_id if after_id else date_to_snowflake(START_DATE)
    latest_scanned_id = current_after
    
    flat_triggers = []
    for k in triggers: flat_triggers.extend(triggers[k])
    if channel_name == "Roof": flat_triggers.extend(["opening", "closing"])

    print(f"\n> Rebuilding {channel_name} timeline from {START_DATE}...")

    max_retries = 3
    retry_count = 0

    while True:
        params = {"limit": 100, "after": current_after}
        try:
            resp = requests.get(url, headers=HEADERS, params=params, timeout=10)
            
            # Handle Rate Limits
            if resp.status_code == 429:
                time.sleep(resp.json().get("retry_after", 1))
                continue
                
            # Handle Transient Server Errors
            if resp.status_code in [500, 502, 503, 504]:
                retry_count += 1
                if retry_count <= max_retries:
                    print(f"  [!] Discord API Error {resp.status_code}. Retrying ({retry_count}/{max_retries}) in 5 seconds...")
                    time.sleep(5)
                    continue
                    
            resp.raise_for_status()
            retry_count = 0 # Reset on success
            batch = resp.json()
            if not batch: break
            
        except requests.exceptions.RequestException as e:
            retry_count += 1
            if retry_count <= max_retries:
                print(f"  [!] Network error: {e}. Retrying ({retry_count}/{max_retries}) in 5 seconds...")
                time.sleep(5)
                continue
            else:
                print(f"  [!] Max retries reached for {channel_name}. Aborting fetch, will resume next scheduled run.")
                break # Safely break and return what we have so far

        batch.sort(key=lambda x: int(x['id']))

        for msg in batch:
            content = msg.get("content", "")
            if any(term in content.lower() for term in IGNORE_LIST): continue
            
            embed_text = " ".join([e.get("title", "") + " " + e.get("description", "") for e in msg.get("embeds", [])])
            field_text = " ".join([f.get("name", "") + " " + str(f.get("value", "")) for e in msg.get("embeds", []) for f in e.get("fields", [])])
            full_text = (content + " " + embed_text + " " + field_text).lower()
            
            if any(t in full_text for t in flat_triggers):
                messages.append(msg)
        
        current_after = batch[-1]["id"]
        latest_scanned_id = current_after
        if len(batch) < 100: break
        
    return messages, latest_scanned_id

def load_scope_triggers(csv_path):
    triggers = {'target_start': [], 'target_end': [], 'wait_start': [], 'wait_end': [], 'flip_start': [], 'flip_end': [], 'night_end': []}
    if not csv_path or not os.path.exists(csv_path): return triggers
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        next(reader, []) 
        for row in reader:
            if not row: continue
            event = str(row[0]).strip().lower()
            for val in row[1:]:
                val = str(val).strip().lower()
                if not val or val == 'nan' or 'note' in val: continue
                
                if "xxx" in val: clean = val.split("xxx")[0].strip()
                elif ":" in val and any(x in event for x in ["target", "shooting", "completed"]): clean = val.split(":")[0].strip() + ":"
                else: clean = val.strip()
                    
                if "wait start" in event or "wait started" in event: triggers['wait_start'].append(clean)
                elif "wait end" in event or "wait ended" in event: triggers['wait_end'].append(clean)
                elif "flip start" in event or "meridian flip start" in event: triggers['flip_start'].append(clean)
                elif "flip end" in event or "meridian flip end" in event: triggers['flip_end'].append(clean)
                elif "night" in event and ("finish" in event or "end" in event): triggers['night_end'].append(clean)
                elif "start" in event or "new target" in event or "imaging new" in event: triggers['target_start'].append(clean)
                elif "finish" in event or "complet" in event or "end" in event or "shooting" in event: triggers['target_end'].append(clean)
    return triggers

def get_astral_times(night_key):
    dt = datetime.datetime.strptime(night_key, "%Y-%m-%d").date()
    n_dusk = dusk(loc.observer, date=dt, depression=12.0, tzinfo=CENTRAL_TZ)
    n_dawn = dawn(loc.observer, date=dt + datetime.timedelta(days=1), depression=12.0, tzinfo=CENTRAL_TZ)
    return n_dusk.isoformat(), n_dawn.isoformat()

def initialize_night_record(night_key):
    dusk_str, dawn_str = get_astral_times(night_key)
    return {
        "astral": {"nautical_dusk": dusk_str, "nautical_dawn": dawn_str},
        "roof": {"status": "Roof did not open", "open_events": [], "closed_events": []},
        "events": {"meridian_flips": [], "target_waits": [], "targets": []}
    }

def get_night_key(timestamp_str):
    dt = datetime.datetime.fromisoformat(timestamp_str)
    if dt.tzinfo is None: dt = pytz.utc.localize(dt)
    local_dt = dt.astimezone(CENTRAL_TZ)
    return (local_dt - datetime.timedelta(hours=12)).date().isoformat()

def main():
    print(f"--- Starfront Extractor v1.4.15 ---")
    conn = sqlite3.connect(STATE_DB)
    conn.execute("CREATE TABLE IF NOT EXISTS cursor_state (channel_id TEXT PRIMARY KEY, last_msg_id TEXT)")
    
    scope_triggers = {}
    data_stores = {}
    
    scopes = [name for name in CHANNELS.values() if name != "Roof"]
    for s_name in scopes:
        csv_name = f"{s_name}-Table 1.csv"
        csv_path = next((p for p in [csv_name, os.path.join(DATA_DIR, csv_name)] if os.path.exists(p)), None)
        scope_triggers[s_name] = load_scope_triggers(csv_path)
        data_stores[s_name] = {}

    # PRE-LOAD EXISTING JSON INTO MEMORY TO PREVENT SHALLOW OVERWRITES
    for name in data_stores:
        out_path = os.path.join(DATA_DIR, f"{name}_log.json")
        if os.path.exists(out_path):
            try:
                with open(out_path, 'r') as f: data_stores[name] = json.load(f)
            except json.JSONDecodeError: pass

    for s_id, s_name in CHANNELS.items():
        last_id = conn.execute("SELECT last_msg_id FROM cursor_state WHERE channel_id = ?", (str(s_id),)).fetchone()
        msgs, latest_scanned_id = fetch_discord_messages(s_id, s_name, scope_triggers.get(s_name, {}), last_id[0] if last_id else None)
        
        if msgs:
            for msg in msgs:
                ts_raw = msg.get("timestamp")
                ts = normalize_time(ts_raw)
                night_key = get_night_key(ts_raw)
                
                raw_text = msg.get("content", "") + " " + " ".join([str(e.get("title", "")) + " " + str(e.get("description", "")) for e in msg.get("embeds", [])])
                field_text = " ".join([str(f.get("name", "")) + " " + str(f.get("value", "")) for e in msg.get("embeds", []) for f in e.get("fields", [])])
                full_low = (raw_text + " " + field_text).lower()
                
                if s_name == "Roof":
                    for d_name in data_stores:
                        if night_key not in data_stores[d_name]: data_stores[d_name][night_key] = initialize_night_record(night_key)
                        if "opening" in full_low and ts not in data_stores[d_name][night_key]["roof"]["open_events"]: 
                            data_stores[d_name][night_key]["roof"]["open_events"].append(ts)
                            data_stores[d_name][night_key]["roof"]["status"] = "Events recorded"
                        elif "closing" in full_low and ts not in data_stores[d_name][night_key]["roof"]["closed_events"]: 
                            data_stores[d_name][night_key]["roof"]["closed_events"].append(ts)
                            data_stores[d_name][night_key]["roof"]["status"] = "Events recorded"
                            if "events" in data_stores[d_name][night_key]:
                                evs = data_stores[d_name][night_key]["events"]
                                if evs["targets"] and evs["targets"][-1]["end"] is None: evs["targets"][-1]["end"] = ts
                                if evs["target_waits"] and evs["target_waits"][-1]["end"] is None: evs["target_waits"][-1]["end"] = ts
                                if evs["meridian_flips"] and evs["meridian_flips"][-1]["end"] is None: evs["meridian_flips"][-1]["end"] = ts
                else:
                    if night_key not in data_stores[s_name]: data_stores[s_name][night_key] = initialize_night_record(night_key)
                    events = data_stores[s_name][night_key]["events"]
                    triggers = scope_triggers[s_name]

                    if any(t in full_low for t in triggers['target_start']):
                        if events["targets"] and events["targets"][-1]["end"] is None: events["targets"][-1]["end"] = ts
                        if events["target_waits"] and events["target_waits"][-1]["end"] is None: events["target_waits"][-1]["end"] = ts
                        
                        t_used = next(t for t in triggers['target_start'] if t in full_low)
                        idx = raw_text.lower().find(t_used) + len(t_used)
                        target_name = raw_text[idx:].split("\n")[0].strip() or "Undefined"
                        if not any(t.get("start") == ts for t in events["targets"]):
                            events["targets"].append({"name": target_name, "start": ts, "end": None})
                        
                    elif any(t in full_low for t in triggers['target_end'] + triggers['night_end']):
                        if events["targets"] and events["targets"][-1]["end"] is None: events["targets"][-1]["end"] = ts
                        if any(t in full_low for t in triggers['night_end']):
                            if events["target_waits"] and events["target_waits"][-1]["end"] is None: events["target_waits"][-1]["end"] = ts
                            if events["meridian_flips"] and events["meridian_flips"][-1]["end"] is None: events["meridian_flips"][-1]["end"] = ts
                    elif any(t in full_low for t in triggers['wait_start']):
                        if events["targets"] and events["targets"][-1]["end"] is None: events["targets"][-1]["end"] = ts
                        if not any(w.get("start") == ts for w in events["target_waits"]): events["target_waits"].append({"start": ts, "end": None})
                    elif any(t in full_low for t in triggers['wait_end']) and events["target_waits"]: events["target_waits"][-1]["end"] = ts
                    elif any(t in full_low for t in triggers['flip_start']): 
                        if not any(f.get("start") == ts for f in events["meridian_flips"]): events["meridian_flips"].append({"start": ts, "end": None})
                    elif any(t in full_low for t in triggers['flip_end']) and events["meridian_flips"]: events["meridian_flips"][-1]["end"] = ts

        if latest_scanned_id:
            conn.execute("REPLACE INTO cursor_state (channel_id, last_msg_id) VALUES (?, ?)", (str(s_id), latest_scanned_id))
            conn.commit()

    # SAVE MERGED STATE BACK TO DISK
    for name, data in data_stores.items():
        out_path = os.path.join(DATA_DIR, f"{name}_log.json")
        with open(out_path, 'w') as f: json.dump(data, f, indent=4)
        
    print("\nExtraction complete. JSON files updated.")

    try:
        import forecast_generator
        print("\n> Checking for live forecasts to append...")
        forecast_generator.main()
    except ImportError:
        pass

if __name__ == "__main__":
    main()
