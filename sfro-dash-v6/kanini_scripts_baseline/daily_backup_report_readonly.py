#!/usr/bin/env python3
"""
Read-only variant of daily_backup_report.py.
Fetches and reports the NAS backup metrics CSV WITHOUT clearing the ledger.
Safe to run as a once-off at any time without destroying data.
"""
import subprocess
import csv
import os

NAS_HOST = "gary@192.168.1.100"
SSH_KEY = "/opt/data/keys/id_ed25519"
CSV_NAS_PATH = "/volume1/automation/backup_metrics.csv"
TMP_CSV = "/tmp/backup_metrics.csv"

def format_bytes(b):
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if b < 1024.0:
            if unit == 'B':
                return f"{int(b)} {unit}"
            return f"{b:.2f} {unit}"
        b /= 1024.0
    return f"{b:.2f} PB"

def main():
    cmd = [
        "scp", "-O", "-i", SSH_KEY, "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=10",
        f"{NAS_HOST}:{CSV_NAS_PATH}", TMP_CSV
    ]
    res = subprocess.run(cmd, capture_output=True)

    if res.returncode != 0 or not os.path.exists(TMP_CSV):
        print("📊 **Daily Backup Volume Report** 📊\n*No data transferred in the last 24 hours.*")
        return

    jobs = {"hot": {}, "warm": {}, "archive": {}}
    total_bytes = 0

    with open(TMP_CSV, 'r') as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) < 4:
                continue
            timestamp, job, share, bytes_str = row
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

    report = ["📊 **Daily Backup Volume Report** 📊", "*Timeframe: Since last daily report*\n"]

    emoji_map = {"hot": "🔥", "warm": "🔶", "archive": "📦"}

    for job, shares in jobs.items():
        if shares:
            emoji = emoji_map.get(job, "📁")
            report.append(f"{emoji} **{job.capitalize()} Shares**:")
            for share, data in shares.items():
                b_str = format_bytes(data["bytes"])
                report.append(f"- {share}: {b_str} ({data['runs']} runs)")
            report.append("")

    report.append(f"**Total Data Protected**: {format_bytes(total_bytes)} ✅")
    # NOTE: No NAS ledger wipe — this is the read-only variant.

    print("\n".join(report))

    # Cleanup local tmp
    if os.path.exists(TMP_CSV):
        os.remove(TMP_CSV)

if __name__ == "__main__":
    main()
