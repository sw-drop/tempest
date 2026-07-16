#!/usr/bin/env python3
import sys
import subprocess
from datetime import datetime

# Configuration
NAS_HOST = "gary@192.168.1.100"
SSH_KEY = "/opt/data/keys/id_ed25519"

def main():
    if len(sys.argv) < 3:
        print("Usage: run_nas_backup.py <job_name> <nas_script_path>")
        sys.exit(1)

    job_name = sys.argv[1]
    nas_script_path = sys.argv[2]
    log_file = f"/volume1/automation/{job_name}_backup.log"

    # print(f"[{datetime.now().isoformat()}] Triggering NAS backup `{job_name}` via path `{nas_script_path}`...")

    # 1. Check if the script is already running on the NAS
    check_cmd = [
        "ssh",
        "-i", SSH_KEY,
        "-o", "StrictHostKeyChecking=no",
        "-o", "ConnectTimeout=10",
        NAS_HOST,
        f"pgrep -f 'bash {nas_script_path}'"
    ]
    
    check_result = subprocess.run(check_cmd, capture_output=True, text=True)
    
    # If pgrep returns 0, it found matching processes
    if check_result.returncode == 0 and check_result.stdout.strip():
        # It's already running. Alert Telegram.
        print(f"🚨 **NAS Backup Alert**: Job `{job_name}` is already running on the NAS! Aborting new trigger.")
        sys.exit(0)
        
    # 2. Start the script in the background using nohup
    # We use nohup so it detaches, and > log_file 2>&1 &
    # We must properly escape the remote command.
    start_cmd = [
        "ssh",
        "-i", SSH_KEY,
        "-o", "StrictHostKeyChecking=no",
        "-o", "ConnectTimeout=10",
        "-n", # redirect stdin from /dev/null
        "-f", # go to background
        NAS_HOST,
        f"nohup bash {nas_script_path} > {log_file} 2>&1 &"
    ]
    
    start_result = subprocess.run(start_cmd, capture_output=True, text=True)
    
    if start_result.returncode != 0:
        print(f"❌ **NAS Backup Error**: Failed to trigger `{job_name}` on the NAS.")
        print(f"Error details: {start_result.stderr.strip()}")
        sys.exit(1)
        
    # Silent on success so Telegram doesn't get pinged every time
    # print(f"✅ Successfully triggered `{job_name}` on the NAS in the background.")
    # Exiting immediately; the NAS watchdog will handle checking the results later.

if __name__ == "__main__":
    main()
