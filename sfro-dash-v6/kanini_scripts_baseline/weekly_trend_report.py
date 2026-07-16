#!/usr/bin/env python3
import subprocess
import csv
import sys
import datetime
from io import StringIO

NAS_HOST = "gary@192.168.1.100"
SSH_KEY = "/opt/data/keys/id_ed25519"

def main():
    cmd = [
        "ssh", "-i", SSH_KEY, "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=10",
        NAS_HOST, "cat /volume1/automation/backup_history_*.csv 2>/dev/null"
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    
    if res.returncode != 0 or not res.stdout.strip():
        print("📈 **Weekly Backup Trend Report** 📈\n*No historical data found.*")
        return

    cutoff_time = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=7)
    
    overall_runs = 0
    overall_failures = 0
    
    # format: {job_name: {"runs": 0, "failures": 0}}
    job_stats = {"hot": {"runs": 0, "failures": 0}, "warm": {"runs": 0, "failures": 0}, "archive": {"runs": 0, "failures": 0}}
    
    # format: {"share_name (job)": {"failures": 0, "last_exit_code": 0}}
    problem_shares = {}
    
    reader = csv.reader(StringIO(res.stdout))
    for row in reader:
        if len(row) < 5:
            continue
        timestamp_str, job, share, status, exit_code_str = [x.strip() for x in row]
        try:
            row_time = datetime.datetime.strptime(timestamp_str, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc)
        except ValueError:
            continue
            
        if row_time < cutoff_time:
            continue
            
        overall_runs += 1
        job = job.lower()
        if job not in job_stats:
            job_stats[job] = {"runs": 0, "failures": 0}
            
        job_stats[job]["runs"] += 1
        
        if status != "success":
            overall_failures += 1
            job_stats[job]["failures"] += 1
            
            share_key = f"{share} ({job.capitalize()})"
            if share_key not in problem_shares:
                problem_shares[share_key] = {"failures": 0, "last_exit_code": exit_code_str}
            problem_shares[share_key]["failures"] += 1
            problem_shares[share_key]["last_exit_code"] = exit_code_str

    if overall_runs == 0:
        print("📈 **Weekly Backup Trend Report** 📈\n*No runs recorded in the last 7 days.*")
        return

    success_rate = 100.0
    if overall_runs > 0:
        success_rate = ((overall_runs - overall_failures) / overall_runs) * 100.0

    report = [
        "📈 **Weekly Backup Trend Report** 📈",
        "*Timeframe: Last 7 Days*\n",
        f"**Overall System Health**: {success_rate:.1f}% Success Rate ({overall_runs} Runs / {overall_failures} Failures)\n"
    ]
    
    emoji_map = {"hot": "🔥", "warm": "🔶", "archive": "📦"}
    
    for job, data in job_stats.items():
        if data["runs"] == 0:
            continue
        emoji = emoji_map.get(job, "📁")
        j_success_rate = ((data["runs"] - data["failures"]) / data["runs"]) * 100.0
        fail_str = f" ({data['failures']} Failures)" if data["failures"] > 0 else ""
        report.append(f"{emoji} **{job.capitalize()} Job**: {j_success_rate:.1f}% Success{fail_str}")
        
    report.append("")
    
    if problem_shares:
        report.append("⚠️ **Problematic Shares**:")
        for share_key, data in problem_shares.items():
            report.append(f"- `{share_key}`: Failed {data['failures']} times (Last Exit Code: {data['last_exit_code']})")
    else:
        report.append("✅ **Problematic Shares**: None! All shares are healthy.")
        
    report.append("\n*NAS currently holding up to 3 months of historical data.*")
    
    print("\n".join(report))

if __name__ == "__main__":
    main()
