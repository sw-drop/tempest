import urllib.request
import json
from datetime import datetime
from zoneinfo import ZoneInfo

lat = 51.45695971753735
lon = -0.18686539472508437
tz = ZoneInfo("Europe/London")
target_date_str = "2026-07-12"

api_url = f"https://api.sunrise-sunset.org/json?lat={lat:.4f}&lng={lon:.4f}&date={target_date_str}&formatted=0"
req_ss = urllib.request.Request(api_url, headers={"User-Agent": "Tempest-V5-Fetcher/1.0 gary@pillay.net"})
with urllib.request.urlopen(req_ss, timeout=5) as resp_ss:
    ss_data = json.loads(resp_ss.read().decode('utf-8'))

if ss_data.get("status") == "OK":
    results = ss_data.get("results", {})
    sunrise_utc = datetime.fromisoformat(results["sunrise"])
    sunrise_local = sunrise_utc.astimezone(tz)
    sunrise_time = sunrise_local.strftime("%H:%M")
    
    sunset_utc = datetime.fromisoformat(results["sunset"])
    sunset_local = sunset_utc.astimezone(tz)
    sunset_time = sunset_local.strftime("%H:%M")
    
    print("Sunrise:", sunrise_time)
    print("Sunset:", sunset_time)
else:
    print("API status error:", ss_data)
