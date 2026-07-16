#!/usr/bin/env python3
import json
import subprocess
import os
import sys
from datetime import datetime, timezone

# Configuration
NAS_HOST = "gary@192.168.1.100"
SSH_KEY = "/opt/data/keys/id_ed25519"
STATUS_FILES = ["hot_status.json", "warm_status.json", "archive_status.json"]
TMP_DIR = "/tmp"

# Thresholds in hours
THRESHOLDS = {
    "hot": 2.25,      # 2h 15m
    "warm": 4.5,      # 4h 30m
    "archive": 26.0   # 26h
}

def fetch_status_files():
    # We must use -O for legacy SCP protocol on Ugreen NAS
    cmd = [
        "scp",
        "-O",
        "-i", SSH_KEY,
        "-o", "StrictHostKeyChecking=no",
        "-o", "ConnectTimeout=10",
        f"{NAS_HOST}:/volume1/automation/*_status.json",
        f"{TMP_DIR}/"
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"🚨 **Backup Watchdog Error**: Failed to fetch status JSONs from NAS via SCP!")
        print(f"Details: {result.stderr.strip()}")
        sys.exit(1)

def check_backups():
    alerts = []
    
    for filename in STATUS_FILES:
        filepath = os.path.join(TMP_DIR, filename)
        if not os.path.exists(filepath):
            alerts.append(f"🚨 **Missing Status File**: Expected `{filename}` from NAS but it was not found.")
            continue
            
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
        except Exception as e:
            alerts.append(f"🚨 **Parse Error**: Failed to parse `{filename}`: {str(e)}")
            continue
            
        job = data.get("job", "unknown")
        timestamp_str = data.get("timestamp")
        overall_status = data.get("overall_status")
        shares = data.get("shares", [])
        
        # 1. Freshness Check
        if not timestamp_str:
            alerts.append(f"🚨 **Stale Backup**: `{job}` backup has no timestamp in status JSON.")
        else:
            try:
                # e.g., 2026-07-07T12:00:00Z
                dt = datetime.strptime(timestamp_str, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
                now = datetime.now(timezone.utc)
                delta_hours = (now - dt).total_seconds() / 3600.0
                
                max_hours = THRESHOLDS.get(job, 24.0)
                if delta_hours > max_hours:
                    alerts.append(f"🚨 **Stale Backup**: `{job}` backup is {delta_hours:.1f} hours old! (Threshold: {max_hours}h)")
            except Exception as e:
                alerts.append(f"🚨 **Date Parse Error**: Failed to parse timestamp `{timestamp_str}` for `{job}`: {str(e)}")
                
        # 2. Granular Share Check
        if overall_status != "success":
            failed_count = 0
            for share in shares:
                if share.get("status") != "success":
                    failed_count += 1
                    s_name = share.get("name", "Unknown")
                    s_code = share.get("exit_code", "N/A")
                    s_err = share.get("error_tail", "No error tail provided")
                    alerts.append(f"🚨 **Backup Failed on Share**: `{s_name}` in job `{job}` (Exit Code: {s_code})\n   *Details*: {s_err}")
            
            if failed_count == 0:
                # Fallback if overall status failed but no individual shares failed (e.g., syntax error)
                alerts.append(f"🚨 **Backup Failed**: Job `{job}` failed but no specific share errors were logged.")
                
    # Output alerts to stdout for Hermes cron engine to route to Telegram
    if alerts:
        print("\n".join(alerts))
    else:
        # Silent on success to avoid Telegram spam
        pass

if __name__ == "__main__":
    fetch_status_files()
    check_backups()
