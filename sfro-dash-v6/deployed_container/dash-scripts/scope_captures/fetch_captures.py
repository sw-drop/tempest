#!/usr/bin/env python3
import sys
import urllib.request
import json
import os
import argparse
from datetime import datetime, timedelta, timezone

# Configuration
TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    # Look for .env in the current folder or parent folder
    for path in [".env", "../.env", "cap_cards/.env"]:
        try:
            if os.path.exists(path):
                with open(path, "r") as f:
                    for line in f:
                        if line.startswith("DISCORD_TOKEN"):
                            TOKEN = line.split("=")[1].strip().strip('"').strip("'")
                            break
        except Exception:
            pass

if not TOKEN:
    print("Error: DISCORD_TOKEN is not defined. Exiting.", file=sys.stderr)
    sys.exit(1)

HEADERS = {"Authorization": f"Bot {TOKEN}", "User-Agent": "StarfrontDashboard/1.0"}

CHANNELS = {
    "fra400": "1407795208200126516",
    "75q": "1440079351516237864"
}

def fetch_messages(channel_id, limit=100):
    url = f"https://discord.com/api/v10/channels/{channel_id}/messages?limit={limit}"
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            return json.loads(response.read().decode('utf-8'))
    except Exception as e:
        print(f"Error fetching channel {channel_id}: {e}", file=sys.stderr)
        return []

def parse_discord_time(ts_str):
    if not ts_str: return None
    dt_str = ts_str.split('+')[0][:19]
    return datetime.fromisoformat(dt_str)

def main():
    parser = argparse.ArgumentParser(description="Fetch exposure summaries from Discord channels and generate text card JSONs.")
    parser.add_argument("-o", "--out-dir", default="v5-test/data", help="Output directory for JSON files")
    parser.add_argument("--title-fra", default="FRA400 Captured", help="Card Title for FRA400")
    parser.add_argument("--title-q75", default="75Q Captured", help="Card Title for 75Q")
    args = parser.parse_args()
    
    os.makedirs(args.out_dir, exist_ok=True)
    
    # Establish time boundary: 18 hours ago
    cutoff_time = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=18)
    
    for scope_name in ["fra400", "75q"]:
        print(f"Fetching Discord messages for {scope_name.upper()}...")
        msgs = fetch_messages(CHANNELS[scope_name], limit=100)
        
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
        
        # Gracefully degrade if no images found by leaving the forecast intact
        if not target_tallies:
            continue
            
        # Build text string
        lines = []
        for target_name, count in target_tallies.items():
            lines.append(f"• {target_name} x {count} Images")
        text_content = "\n".join(lines)
        
        # Build JSON card payload
        card_title = args.title_fra if scope_name == "fra400" else args.title_q75
        card_data = {
            "title": card_title,
            "subtitle": "",
            "type": "text",
            "data": {
                "text": text_content
            }
        }
        
        file_name_map = {"75q": "q75cap.json", "fra400": "fra400cap.json"}
        out_filename = file_name_map.get(scope_name, f"{scope_name}cap.json")
        out_path = os.path.join(args.out_dir, out_filename)
        
        # Write atomically
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
