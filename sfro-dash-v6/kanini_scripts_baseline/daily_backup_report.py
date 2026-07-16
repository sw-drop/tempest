#!/usr/bin/env python3
import subprocess
import csv
import sys
import os
import datetime
from io import StringIO

NAS_HOST = "gary@192.168.1.100"
SSH_KEY = "/opt/data/keys/id_ed25519"
CSV_NAS_PATH = "/volume1/automation/backup_metrics.csv"

def format_bytes(b):
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if b < 1024.0:
            if unit == 'B':
                return f"{int(b)} {unit}"
            return f"{b:.2f} {unit}"
        b /= 1024.0
    return f"{b:.2f} PB"

def main():
    # 1. Fetch ledger directly via SSH cat (no local temp file state issues)
    cmd = [
        "ssh", "-i", SSH_KEY, "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=10",
        NAS_HOST, f"cat {CSV_NAS_PATH} 2>/dev/null"
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    
    if res.returncode != 0 or not res.stdout.strip():
        print("📊 **Daily Backup Volume Report** 📊\n*No data transferred in the last 24 hours.*")
        return

    # 2. Parse ledger
    jobs = {"hot": {}, "warm": {}, "archive": {}}
    total_bytes = 0
    
    cutoff_time = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=24)
    
    reader = csv.reader(StringIO(res.stdout))
    for row in reader:
        if len(row) < 4:
            continue
        timestamp, job, share, bytes_str = row
        
        try:
            row_time = datetime.datetime.strptime(timestamp.strip(), "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc)
        except ValueError:
            continue
            
        if row_time < cutoff_time:
            continue
            
        try:
            b = int(bytes_str.strip())
        except ValueError:
            continue
        
        job = job.strip().lower()
        share = share.strip()
        
        if job not in jobs:
            jobs[job] = {}
        if share not in jobs[job]:
            jobs[job][share] = {"bytes": 0, "runs": 0}
            
        jobs[job][share]["bytes"] += b
        jobs[job][share]["runs"] += 1
        total_bytes += b

    # 3. Format Report
    report = ["📊 **Daily Backup Volume Report** 📊", "*Timeframe: Last 24 Hours*\n"]
    
    emoji_map = {"hot": "🔥", "warm": "🔶", "archive": "📦"}
    
    for job, shares in jobs.items():
        if shares:
            emoji = emoji_map.get(job, "📁")
            report.append(f"{emoji} **{job.capitalize()} Shares**:")
            for share, data in shares.items():
                b_str = format_bytes(data["bytes"])
                report.append(f"- {share}: {b_str} ({data['runs']} runs)")
            report.append("")
            
    report.append(f"**Total Data Protected Today**: {format_bytes(total_bytes)} ✅")
    
    output_str = "\n".join(report)
    print(output_str)
    
    # Mirror output to the V5 Dashboard Volume if it is mapped
    dash_path = "/opt/data/v5-dash/data/reports/backup.txt"
    try:
        os.makedirs(os.path.dirname(dash_path), exist_ok=True)
        with open(dash_path, "w", encoding="utf-8") as f:
            f.write(output_str + "\n")
    except Exception:
        pass

if __name__ == "__main__":
    main()
