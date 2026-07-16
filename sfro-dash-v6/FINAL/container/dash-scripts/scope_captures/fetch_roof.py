#!/usr/bin/env python3
import sys
import urllib.request
import json
import os
import argparse
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

def fetch_json(url, headers):
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as response:
            return json.loads(response.read().decode('utf-8'))
    except Exception as e:
        print(f"Error fetching API {url}: {e}", file=sys.stderr)
        return None

def parse_iso(ts_str):
    if not ts_str:
        return None
    # Truncate fractional seconds for compatibility
    return datetime.fromisoformat(ts_str.split('+')[0][:19])

def main():
    parser = argparse.ArgumentParser(description="Fetch latest roof status and nightly plans from Discord and generate roof card JSON.")
    parser.add_argument("-o", "--out-dir", default="v5-test/data", help="Output directory for JSON files")
    args = parser.parse_args()
    
    os.makedirs(args.out_dir, exist_ok=True)
    
    # Retrieve Discord Token
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        # Fallback to local .env searches
        for env_path in [".env", "../.env", "scope_captures/.env"]:
            if os.path.exists(env_path):
                try:
                    with open(env_path, "r") as f:
                        for line in f:
                            if line.strip().startswith("DISCORD_TOKEN"):
                                token = line.split("=")[1].strip().strip('"').strip("'")
                                break
                except Exception:
                    pass
            if token:
                break
                
    if not token:
        print("Error: DISCORD_TOKEN environment variable is not defined.", file=sys.stderr)
        sys.exit(1)
        
    headers = {
        "Authorization": f"Bot {token}",
        "User-Agent": "StarfrontDashboard/1.0"
    }
    
    # announcements channel ID
    channel_id = "1409490508803211345"
    url = f"https://discord.com/api/v10/channels/{channel_id}/messages?limit=25"
    
    print(f"Fetching announcements from Discord...")
    messages = fetch_json(url, headers)
    
    if not messages:
        print("Error: Could not retrieve messages from announcements channel.", file=sys.stderr)
        sys.exit(1)
        
    latest_roof_open = True
    latest_roof_time = None
    
    # Scan announcements history
    for msg in messages:
        embeds = msg.get("embeds", [])
        msg_time = parse_iso(msg.get("timestamp"))
        
        # Parse Roof Status Opening/Closing Embeds
        for embed in embeds:
            title = embed.get("title", "")
            desc = embed.get("description", "")
            if "Roofs Closing" in title or "Roofs Opening" in title:
                if not latest_roof_time or (msg_time and msg_time > latest_roof_time):
                    latest_roof_time = msg_time
                    if "opening" in desc.lower() or "open" in desc.lower():
                        latest_roof_open = True
                    else:
                        latest_roof_open = False
                        
    # Format Title and Status
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    if not latest_roof_time or (now - latest_roof_time).total_seconds() > 18 * 3600:
        latest_roof_open = False
        
    if latest_roof_open:
        title_text = "OBSERVATORY ROOF OPEN"
        title_color = "var(--green)"
    else:
        title_text = "OBSERVATORY ROOF CLOSED"
        title_color = "" # Default CSS color
        
    subtitle_text = f"Updated: {latest_roof_time.strftime('%H:%M UTC')}" if latest_roof_time else ""
        
    # Build payload
    payload = {
        "title": title_text,
        "title_color": title_color,
        "subtitle": subtitle_text,
        "type": "status",
        "data": {
            "status": "", # Kept empty to display only in title bar
            "details": "" # Empty, will be populated by controller.py with Hermes summary
        }
    }
    
    out_path = os.path.join(args.out_dir, "roof.json")
    temp_path = f"{out_path}.tmp"
    try:
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        os.replace(temp_path, out_path)
        print(f"  [✓] Successfully updated roof status in {out_path}")
    except Exception as e:
        print(f"  [!] Failed to write {out_path}: {e}", file=sys.stderr)

if __name__ == "__main__":
    main()
