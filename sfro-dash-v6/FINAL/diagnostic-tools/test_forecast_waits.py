import urllib.request
import json
from datetime import datetime

url = "http://192.168.1.51:5002/data/75Q_log.json"
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req, timeout=5) as response:
    data = json.loads(response.read().decode('utf-8'))

fc_keys = [k for k in data.keys() if k.endswith('_forecast')]
latest_fc_key = sorted(fc_keys)[-1]
fc_record = data[latest_fc_key]

naut_dusk_str = fc_record.get("astral", {}).get("nautical_dusk", "2099-01-01T00:00:00")
naut_dusk = datetime.fromisoformat(naut_dusk_str)

events = []

targets = fc_record.get("events", {}).get("targets", [])
for t in targets:
    name = t.get("name", "Unknown Target")
    start_str = t.get("start")
    start_dt = datetime.fromisoformat(start_str)
    events.append({
        "time": start_dt,
        "label": name
    })

waits = fc_record.get("events", {}).get("target_waits", [])
for w in waits:
    start_str = w.get("start")
    end_str = w.get("end")
    start_dt = datetime.fromisoformat(start_str)
    end_dt = datetime.fromisoformat(end_str)
    
    if end_dt > naut_dusk:
        start_label = start_dt.strftime("%H:%M")
        end_label = end_dt.strftime("%H:%M")
        events.append({
            "time": start_dt,
            "label": f"Wait ({start_label} - {end_label})"
        })

events.sort(key=lambda x: x["time"])
for e in events:
    print(f"• {e['label']}")
