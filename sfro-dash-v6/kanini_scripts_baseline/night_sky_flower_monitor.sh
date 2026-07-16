#!/usr/bin/env bash
# obsu_night_sky_flower_monitor.sh – improved clear-sky monitor
# Checks next 24h for >=2 consecutive hours with <15% cloud cover
# Sends Telegram alerts during 10-20 UTC runtime window

set -euo pipefail

LAT="51.5074"
LON="-0.1278"
API="https://api.met.no/weatherapi/locationforecast/2.0/compact"
USER_AGENT="Hermes-Agent/1.0 (test@pillay.uk)"

# 1. Runtime window check (10-20 UTC)
RUN_HOUR=$(date +%H)
if (( RUN_HOUR < 10 || RUN_HOUR > 20 )); then
    exit 0
fi

# 2. Fetch forecast
RESPONSE=$(curl -s -A "$USER_AGENT" "${API}?lat=${LAT}&lon=${LON}" || true)
if [[ -z "$RESPONSE" ]]; then
    # Hard fail so Merope alerts you that the API is unreachable
    echo "CRITICAL: Failed to fetch weather data from Met.no API." >&2
    exit 1
fi

# 3. Process and deliver alert via Python
python3 - <<'PYEOF' "$RESPONSE"
import sys, json, os, hashlib
from datetime import datetime, timedelta

try:
    data = json.loads(sys.argv[1])
except:
    # Hard fail so Merope alerts you that the API JSON format changed
    print("CRITICAL: Failed to parse Met.no JSON response. API may have changed.", file=sys.stderr)
    sys.exit(1)

ts = data.get('properties', {}).get('timeseries', [])
clouds = []
for e in ts[:25]:
    try:
        t = datetime.fromisoformat(e['time'].replace('Z', '+00:00'))
        c = e['data']['instant']['details'].get('cloud_area_fraction')
        if c is not None: clouds.append((t, float(c)))
    except: pass

# Find windows: >=2h consecutive with cloud <15% during night (19:00 - 07:00 BST)
wins = []
start = None
for t, c in clouds:
    t_bst = t + timedelta(hours=1)
    is_clear_night = (c < 15) and (t_bst.hour >= 19 or t_bst.hour < 7)
    if is_clear_night:
        if start is None: start = t
    else:
        if start:
            dur = (t - start).total_seconds() / 3600
            if dur >= 2: wins.append((start, t))
            start = None
if start:
    dur = (clouds[-1][0] - start).total_seconds() / 3600
    if dur >= 2: wins.append((start, clouds[-1][0]))

if not wins:
    sys.exit(0)

# Build BST message
lines = []
for s, e in wins:
    sm = (s + timedelta(hours=1)).strftime('%H:%M')
    em = (e + timedelta(hours=1)).strftime('%H:%M')
    cvs = [c for _, c in clouds if s <= _ <= e]
    mc = int(min(cvs)) if cvs else 0
    lines.append('• ' + sm + '-' + em + ' BST (' + str(mc) + '% cloud)')

msg = '🌙 **Clear-sky window(s):**\n' + '\n'.join(lines) + '\n\nCheck updates.'

# 4. Idempotency Check (Rule 5: Prevent duplicate alerts for the exact same window)
msg_hash = hashlib.md5(msg.encode()).hexdigest()
cache_file = '/opt/data/cache/last_sky_window.txt'

try:
    if os.path.exists(cache_file):
        with open(cache_file, 'r') as f:
            if f.read().strip() == msg_hash:
                sys.exit(0) # Already alerted this exact window, stay silent
except Exception as err:
    pass

try:
    os.makedirs(os.path.dirname(cache_file), exist_ok=True)
    with open(cache_file, 'w') as f:
        f.write(msg_hash)
except:
    pass

# Print the raw alert to stdout for Merope to pick up
print(msg)

# Mirror output to the V5 Dashboard Volume if it is mapped
dash_path = '/opt/data/v5-dash/data/reports/flower.txt'
try:
    os.makedirs(os.path.dirname(dash_path), exist_ok=True)
    with open(dash_path, 'w') as f:
        f.write(msg + '\n')
except:
    pass
PYEOF
