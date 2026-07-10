import urllib.request
import json
import time
import os
import logging
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from calendar import timegm

logger = logging.getLogger("tempest_reports")

class ReportsDaemon:
    def __init__(self, config):
        self.config = config
        self.running = False
        self.token = os.getenv("DISCORD_TOKEN")
        
        # Load token from .env if present (fallback)
        if not self.token:
            try:
                env_path = "/app/.env" if os.path.exists("/app/.env") else ".env"
                if os.path.exists(env_path):
                    with open(env_path, "r") as f:
                        for line in f:
                            if line.startswith("DISCORD_TOKEN"):
                                self.token = line.split("=")[1].strip().strip('"').strip("'")
            except Exception:
                pass

    def start(self):
        self.running = True
        logger.info("Reports Daemon initialized.")

    def run_once(self):
        """Runs the reports compiler once and writes to reports.json."""
        logger.info("Compiling daily capture and operations reports...")
        
        capture_out = self._run_capture_report()
        forecast_out = self._run_forecast_report()
        
        payload = {
            "capture": capture_out,
            "forecast": forecast_out
        }
        
        # Write atomically to reports.json
        temp_path = os.path.join(self.config.STATIC_DIR, "reports.json.tmp")
        final_path = os.path.join(self.config.STATIC_DIR, "reports.json")
        try:
            with open(temp_path, "w") as f:
                json.dump(payload, f)
            os.replace(temp_path, final_path)
            logger.info(f"Successfully compiled and wrote reports.json to {final_path}")
        except Exception as e:
            logger.error(f"Failed to write reports.json: {e}")

    # --- 1. DISCORD CAPTURE REPORT LOGIC ---
    def _run_capture_report(self):
        if not self.token:
            return "Warning: DISCORD_TOKEN is not defined. Discord reports unavailable."

        headers = {"Authorization": f"Bot {self.token}", "User-Agent": "StarfrontDashboard/1.0"}
        channels = {
            "fra400": "1407795208200126516",
            "75q": "1440079351516237864",
            "announcements": "1409490508803211345"
        }

        def fetch_messages(channel_id, limit=100):
            url = f"https://discord.com/api/v10/channels/{channel_id}/messages?limit={limit}"
            req = urllib.request.Request(url, headers=headers)
            try:
                with urllib.request.urlopen(req, timeout=10) as response:
                    return json.loads(response.read().decode('utf-8'))
            except Exception as e:
                logger.error(f"Error fetching Discord channel {channel_id}: {e}")
                return []

        def parse_discord_time(ts_str):
            if not ts_str: return None
            return datetime.fromisoformat(ts_str.split('+')[0][:19])

        def get_local_time_string_short(utc_dt):
            utc_dt = utc_dt.replace(tzinfo=timezone.utc)
            local_dt = utc_dt.astimezone(ZoneInfo("America/Chicago"))
            return local_dt.strftime("%H:%M Central")

        # Establish astrophotography night (12 hours ago) and cutoff bounds (18 hours ago)
        current_utc = datetime.now(timezone.utc).replace(tzinfo=None)
        astro_night = current_utc - timedelta(hours=12)
        astro_weekday = astro_night.strftime("%A")
        cutoff_time = current_utc - timedelta(hours=18)
        
        output_lines = [f"🔭 **Nightly Capture & Operations Report - {astro_weekday}**\n"]
        output_lines.append("📸 **Exposure Summary**")

        for scope_name in ["fra400", "75q"]:
            msgs = fetch_messages(channels[scope_name], limit=100)
            target_tallies = {}
            
            for msg in msgs:
                msg_time = parse_discord_time(msg.get("timestamp"))
                if not msg_time or msg_time < cutoff_time:
                    continue
                    
                content = msg.get("content", "").lower()
                if "_exps_" in content:
                    embeds = msg.get("embeds", [])
                    target_name = "Unknown Target"
                    for embed in embeds:
                        for field in embed.get("fields", []):
                            if field.get("name") == "Target":
                                target_name = field.get("value")
                    target_tallies[target_name] = target_tallies.get(target_name, 0) + 1
            
            output_lines.append(f"  * {scope_name.upper()}:")
            if not target_tallies:
                output_lines.append("    * No exposures recorded in the last 18 hours.")
            else:
                for t, count in target_tallies.items():
                    output_lines.append(f"    * Target: {t} x {count} Images")
                    
        # Roof Announcements
        output_lines.append("\n🏠")
        announcements = fetch_messages(channels["announcements"], limit=20)
        
        latest_roof = "Unknown"
        latest_roof_time = None
        latest_report = "None"
        latest_report_time = None
        
        for msg in announcements:
            msg_time = parse_discord_time(msg.get("timestamp"))
            
            if msg.get("content", "").startswith("**Nightly Plan") and not latest_report_time:
                latest_report = msg.get("content")
                latest_report_time = msg_time
                
            for embed in msg.get("embeds", []):
                title = embed.get("title", "")
                if "Roofs Closing" in title or "Roofs Opening" in title:
                    if not latest_roof_time:
                        latest_roof = embed.get("description", "").split("\n")[0].replace("**", "")
                        latest_roof_time = msg_time
                        
        if latest_roof_time:
            status = latest_roof.strip().rstrip('.')
            if "opening" in status.lower():
                status_text = "🟢 OPENING"
            elif "closing" in status.lower():
                status_text = "🔴 CLOSING"
            elif "open" in status.lower():
                status_text = "🟢 OPEN"
            elif "closed" in status.lower():
                status_text = "🔴 CLOSED"
            else:
                status_text = status.upper()
            output_lines.append(f"Roof Status: {status_text} (at {get_local_time_string_short(latest_roof_time)})")
        else:
            output_lines.append("Roof Status: No events found")
            
        if latest_report_time:
            output_lines.append("")
            output_lines.append(latest_report.strip())
            
        return "\n".join(output_lines)

    # --- 2. OBSERVATORY FORECAST LOGIC ---
    def _run_forecast_report(self):
        host_url = os.getenv("DASHBOARD_HOST", "http://192.168.1.51:5002")
        fra_url = f"{host_url}/data/FRA400_log.json"
        q75_url = f"{host_url}/data/75Q_log.json"

        def fetch_json(url):
            try:
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=10) as response:
                    return json.loads(response.read().decode('utf-8'))
            except Exception as e:
                logger.error(f"Error fetching scope log {url}: {e}")
                return None

        def parse_iso(dt_str):
            return datetime.fromisoformat(dt_str[:19])

        def get_forecast_logic(data):
            if not data: return None
            fc_keys = [k for k in data.keys() if k.endswith('_forecast')]
            if not fc_keys: return None
            
            night_key = sorted(fc_keys)[-1]
            fc = data[night_key]
            
            weather_series = fc.get("weather", [])
            open_windows = []
            current_window = []
            
            for entry in weather_series:
                cloud = entry.get("cloud", 100)
                time_parsed = parse_iso(entry["time"])
                if cloud < 20:
                    current_window.append((time_parsed, cloud))
                else:
                    if len(current_window) > 1:
                        open_windows.append(current_window)
                    current_window = []
            if len(current_window) > 1:
                open_windows.append(current_window)
                
            astral_data = fc.get("astral", {})
            naut_dusk = parse_iso(astral_data.get("nautical_dusk", "2099-01-01T00:00:00"))
            
            relevant_waits = []
            for w in fc.get("events", {}).get("target_waits", []):
                w_start = parse_iso(w["start"])
                w_end = parse_iso(w["end"])
                if w_end > naut_dusk:
                    relevant_waits.append((w_start, w_end))
                    
            targets = fc.get("events", {}).get("targets", [])
            moon = fc.get("moon", {})
            
            return {
                "date": night_key.replace("_forecast", ""),
                "open_windows": open_windows,
                "waits": relevant_waits,
                "targets": targets,
                "moon": moon
            }

        fra_data = fetch_json(fra_url)
        q75_data = fetch_json(q75_url)
        
        if not fra_data and not q75_data:
            return "Error: Could not fetch forecast data from either scope."
            
        fc = get_forecast_logic(fra_data or q75_data)
        if not fc:
            return "No upcoming forecast found."
            
        fc_date = datetime.strptime(fc['date'], "%Y-%m-%d")
        weekday_str = fc_date.strftime("%A")
        
        output_lines = [f"🌌 **Tonight's Observatory Forecast {weekday_str} ({fc['date']})**"]
        
        # Open Windows
        if fc["open_windows"]:
            output_lines.append("Roof Open Likelihood: **HIGH**")
            for idx, win in enumerate(fc["open_windows"]):
                s = win[0][0].strftime("%H:%M")
                e = win[-1][0].strftime("%H:%M")
                avg_cloud = sum(x[1] for x in win) / len(win)
                output_lines.append(f"  * Window {idx+1}: {s} - {e} (Avg Cloud: {avg_cloud:.1f}%)")
        else:
            output_lines.append("Roof Open Likelihood: **LOW** (No clear blocks >1 hour)")
            
        # Moon
        moon = fc["moon"]
        if moon:
            output_lines.append(f"\n🌙 **Moon Phase**: {moon.get('phase')} ({moon.get('illum')} illum, Age: {moon.get('age')} days)")
            output_lines.append(f"⏰ {moon.get('events_string', '').replace('&nbsp;&bull;&nbsp;', ' | ')}")
            
        # Targets
        output_lines.append("\n🔭 **Target Summary**")
        if fra_data:
            fra_fc = get_forecast_logic(fra_data)
            targets = [t['name'] for t in (fra_fc['targets'] if fra_fc else [])]
            output_lines.append(f"  * FRA400: {', '.join(targets) if targets else 'None Scheduled'}")
            
        if q75_data:
            q75_fc = get_forecast_logic(q75_data)
            targets = [t['name'] for t in (q75_fc['targets'] if q75_fc else [])]
            output_lines.append(f"  * 75Q: {', '.join(targets) if targets else 'None Scheduled'}")
            
        # Waits
        waits = fc["waits"]
        if waits:
            output_lines.append("\n⏳ **Wait States of Interest** (After Nautical Dusk):")
            for ws, we in waits:
                output_lines.append(f"  * Wait: {ws.strftime('%H:%M')} to {we.strftime('%H:%M')}")
                
        return "\n".join(output_lines)
