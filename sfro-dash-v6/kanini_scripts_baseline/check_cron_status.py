#!/usr/bin/env python3
import json
import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime, timezone

# Color codes for pretty terminal output
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RESET = "\033[0m"

def get_project_root():
    return Path(__file__).resolve().parent.parent

def is_sandbox(project_root):
    # In sandbox, /workspace exists but the cron folder does not
    return Path("/workspace").exists() and not (project_root / "cron").exists()

def check_gateway_running(project_root):
    # 1. If running on Eadu host (outside Docker)
    if not Path("/.dockerenv").exists():
        try:
            res = subprocess.run(
                ["docker", "inspect", "-f", "{{.State.Running}}", "hermes"],
                capture_output=True, text=True, timeout=5
            )
            return res.stdout.strip() == "true"
        except Exception:
            pass

    # 2. Inside Docker container
    try:
        pid_file = project_root / "gateway.pid"
        if pid_file.exists():
            pid = pid_file.read_text().strip()
            if os.path.exists(f"/proc/{pid}"):
                return True
        for proc in Path("/proc").glob("[0-9]*"):
            try:
                cmdline = (proc / "cmdline").read_text()
                if "hermes" in cmdline and "gateway" in cmdline:
                    return True
            except IOError:
                continue
    except Exception:
        pass
    return False

def check_cron_status():
    project_root = get_project_root()
    
    if is_sandbox(project_root):
        return [], [], ["Running inside sandbox container. Skipping active checks."]

    critical_issues = []
    job_issues = []
    successes = []
    
    # 1. Check Gateway process
    if check_gateway_running(project_root):
        successes.append("Gateway process is running.")
    else:
        critical_issues.append(f"{RED}❌ Gateway process is NOT running!{RESET}")
        
    # 2. Check jobs.json readability
    jobs_path = project_root / "cron" / "jobs.json"
    if not jobs_path.exists():
        critical_issues.append(f"{RED}❌ jobs.json does not exist at {jobs_path}{RESET}")
        return critical_issues, job_issues, successes
        
    try:
        data = json.loads(jobs_path.read_text())
        successes.append("jobs.json is readable.")
    except PermissionError as e:
        critical_issues.append(f"{RED}❌ Permission Denied reading jobs.json: {e}{RESET}")
        return critical_issues, job_issues, successes
    except Exception as e:
        critical_issues.append(f"{RED}❌ Error parsing jobs.json: {e}{RESET}")
        return critical_issues, job_issues, successes

    # 3. Check Jobs
    now_utc = datetime.now(timezone.utc)
    jobs = data.get("jobs", [])
    active_count = 0
    
    for job in jobs:
        name = job.get("name")
        enabled = job.get("enabled", False)
        script = job.get("script")
        last_status = job.get("last_status")
        last_error = job.get("last_error")
        next_run = job.get("next_run_at")
        
        # Skip self-checking to prevent a feedback loop of failures
        if job.get("id") == "gateway_health_check" or name == "Gateway Health Check":
            continue
            
        if not enabled:
            continue
            
        active_count += 1
        
        # Check script file if defined
        if script:
            script_path = project_root / "scripts" / script
            alt_path = project_root / "home" / ".hermes" / "scripts" / script
            
            resolved_path = None
            if script_path.exists():
                resolved_path = script_path
            elif alt_path.exists():
                resolved_path = alt_path
                
            if resolved_path is None:
                job_issues.append(f"{RED}❌ Job '{name}': Script file '{script}' is missing!{RESET}")
            elif not os.access(resolved_path, os.X_OK) and not script.endswith('.py'):
                job_issues.append(f"{RED}❌ Job '{name}': Script file '{script}' is not executable!{RESET}")
                
        # Check last status
        if last_status == "error":
            job_issues.append(f"{RED}❌ Job '{name}' failed during last run!{RESET}\n   Error: {last_error}\n   Check /opt/data/cron/output/{job.get('id')}/archive_errors.md for full logs.")
            
        # Check next run at (stalled check)
        if next_run:
            try:
                next_dt = datetime.fromisoformat(next_run.replace("Z", "+00:00"))
                delta_minutes = (now_utc - next_dt).total_seconds() / 60
                if delta_minutes > 10:
                    job_issues.append(f"{YELLOW}⚠️ Job '{name}' next run ({next_run}) is {int(delta_minutes)}m in the past! (Scheduler might be stalled){RESET}")
            except Exception:
                pass
                
    successes.append(f"Checked {active_count} active cron job(s).")
    
    # 4. Check errors.log for recent permission/IO issues (last 10 minutes)
    errors_path = project_root / "logs" / "errors.log"
    if errors_path.exists():
        try:
            with open(errors_path) as f:
                lines = f.readlines()[-100:]
            cron_errs = []
            for line in lines:
                if "cron" in line.lower() and ("error" in line.lower() or "denied" in line.lower()):
                    parts = line.split(maxsplit=2)
                    if len(parts) >= 2:
                        ts_str = f"{parts[0]} {parts[1].split(',')[0]}"
                        try:
                            log_dt = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
                            delta_sec = (now_utc - log_dt).total_seconds()
                            if 0 <= delta_sec <= 600:  # 10 minutes
                                cron_errs.append(line.strip())
                        except Exception:
                            cron_errs.append(line.strip())
            if cron_errs:
                job_issues.append(f"{RED}❌ Recent cron errors in errors.log (last 10m):{RESET}\n" + "\n".join(cron_errs[-5:]))
        except Exception:
            pass
            
    return critical_issues, job_issues, successes

def main():
    verbose = "-v" in sys.argv or "--verbose" in sys.argv
    critical_issues, job_issues, successes = check_cron_status()
    
    if critical_issues or job_issues:
        print(f"\n{RED}=== GATEWAY HEALTH ISSUES DETECTED ==={RESET}\n")
        
        if critical_issues:
            print(f"{RED}--- CRITICAL INFRASTRUCTURE ISSUES ---{RESET}")
            for issue in critical_issues:
                print(issue)
                print("-" * 50)
                
        if job_issues:
            print(f"{YELLOW}--- CRON JOB EXECUTION ISSUES ---{RESET}")
            for issue in job_issues:
                print(issue)
                print("-" * 50)
        
        # Exit 1 for infrastructure failures, but exit 0 for minor cron job status alerts
        if critical_issues:
            sys.exit(1)
        else:
            sys.exit(0)
    else:
        if verbose:
            print(f"\n{GREEN}✓ Gateway and Cron Scheduler are healthy!{RESET}")
            for s in successes:
                print(f"  {GREEN}✓{RESET} {s}")
            print()
        sys.exit(0)

if __name__ == "__main__":
    main()
