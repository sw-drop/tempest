#!/usr/bin/env python3
import os
import sys
import json
import urllib.request
import datetime
from urllib.error import URLError

HERMES_HOME = os.environ.get("HERMES_HOME", "/opt/data")
BASELINE_FILE = os.path.join(HERMES_HOME, ".hermes", "container_backup_baseline.json")
API_URL = "http://192.168.1.60:8083/api/infrastructure"

def fetch_running_containers(host_target):
    req = urllib.request.Request(API_URL, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            data = json.loads(response.read().decode('utf-8'))
    except Exception as e:
        print(f"⚠️ Error fetching Infrastructure Dashboard API: {e}", file=sys.stderr)
        sys.exit(0)  # Exit 0 to handle transient network outages gracefully without crashing cron check loop

    for host_info in data:
        if host_info.get("host", "").lower() == host_target.lower():
            running = []
            for container in host_info.get("containers", []):
                if container.get("state") == "running":
                    running.append(container.get("name"))
            return running
    
    print(f"⚠️ Warning: Target host '{host_target}' not found in Dashboard API response.", file=sys.stderr)
    return None

def main():
    host_target = None
    if len(sys.argv) >= 2:
        host_target = sys.argv[1]
    else:
        # Fallback: Parse jobs.json to find target hostname from arguments of our job
        jobs_file = os.path.join(HERMES_HOME, "cron", "jobs.json")
        if os.path.exists(jobs_file):
            try:
                with open(jobs_file, "r") as f:
                    jobs_data = json.load(f)
                for job in jobs_data.get("jobs", []):
                    if job.get("id") in ("e8f9a2b3c4d7", "e8f9a2b3c4d8"):
                        args = job.get("args", [])
                        if args:
                            host_target = args[0]
                            break
            except Exception as e:
                print(f"⚠️ Error reading jobs.json for fallback hostname: {e}", file=sys.stderr)
        
    if not host_target:
        print("Usage: python3 check_container_backup_recovery.py <hostname>", file=sys.stderr)
        sys.exit(1)
    now_utc = datetime.datetime.now(datetime.timezone.utc)

    # Check if Sunday (6) or Wednesday (2) in UTC
    if now_utc.weekday() not in (2, 6):
        sys.exit(0)

    # Trigger times (UTC)
    is_pre = (now_utc.hour == 7 and 50 <= now_utc.minute < 55)
    is_post = (now_utc.hour == 9 and 0 <= now_utc.minute < 5)

    if not is_pre and not is_post:
        sys.exit(0)

    if is_pre:
        # Pre-backup: Capture baseline of running containers
        running = fetch_running_containers(host_target)
        if running is not None:
            try:
                os.makedirs(os.path.dirname(BASELINE_FILE), exist_ok=True)
                with open(BASELINE_FILE, "w") as f:
                    json.dump({
                        "host": host_target,
                        "timestamp": now_utc.isoformat(),
                        "running_containers": running
                    }, f, indent=2)
            except Exception as e:
                print(f"⚠️ Error saving baseline file: {e}", file=sys.stderr)
        sys.exit(0)

    if is_post:
        # Post-backup: Verify all containers in the baseline are back up
        if not os.path.exists(BASELINE_FILE):
            print(f"⚠️ Warning: Pre-backup baseline file '{BASELINE_FILE}' not found. Cannot verify recovery.", file=sys.stderr)
            sys.exit(0)

        try:
            with open(BASELINE_FILE, "r") as f:
                baseline_data = json.load(f)
        except Exception as e:
            print(f"⚠️ Error reading baseline file: {e}", file=sys.stderr)
            sys.exit(0)

        baseline_containers = set(baseline_data.get("running_containers", []))
        current_running = fetch_running_containers(host_target)

        if current_running is None:
            sys.exit(0)

        current_running_set = set(current_running)
        missing_containers = baseline_containers - current_running_set

        if missing_containers:
            missing_list = sorted(list(missing_containers))
            print(f"❌ Container Backup Recovery Failure on {host_target}: The following containers failed to recover: {', '.join(missing_list)}")
        
        # Cleanup baseline file
        try:
            os.remove(BASELINE_FILE)
        except Exception:
            pass

if __name__ == "__main__":
    main()
