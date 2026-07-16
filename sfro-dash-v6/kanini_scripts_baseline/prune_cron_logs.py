#!/usr/bin/env python3
import os
import glob

HERMES_HOME = os.environ.get("HERMES_HOME", "/opt/data")
CRON_OUTPUT_DIR = os.path.join(HERMES_HOME, "cron", "output")

def prune_job_logs(job_dir):
    # Find all .md files in this job's output directory
    log_files = glob.glob(os.path.join(job_dir, "*.md"))
    
    # Filter out archive files just in case
    log_files = [f for f in log_files if not os.path.basename(f).startswith("archive_")]
    
    if not log_files:
        return
        
    # Sort files by name (which contains timestamp)
    log_files.sort()
    
    # Keep the most recent file always
    latest_file = log_files[-1]
    older_files = log_files[:-1]
    
    error_archive = os.path.join(job_dir, "archive_errors.md")
    
    for file_path in older_files:
        try:
            with open(file_path, "r") as f:
                content = f.read()
                
            if "**Status:** silent (empty output)" in content:
                # It's a healthy empty run, safe to delete
                os.remove(file_path)
            else:
                # It has errors or output. Append to archive and then delete
                with open(error_archive, "a") as af:
                    af.write(f"\n\n{'='*40}\n")
                    af.write(f"Archived from: {os.path.basename(file_path)}\n")
                    af.write(f"{'='*40}\n")
                    af.write(content)
                os.remove(file_path)
        except Exception as e:
            print(f"Error processing {file_path}: {e}")

if __name__ == "__main__":
    if not os.path.exists(CRON_OUTPUT_DIR):
        print(f"Directory {CRON_OUTPUT_DIR} does not exist. Exiting.")
        exit(0)
        
    for job_id in os.listdir(CRON_OUTPUT_DIR):
        job_dir = os.path.join(CRON_OUTPUT_DIR, job_id)
        if os.path.isdir(job_dir):
            prune_job_logs(job_dir)
            
    print("Cron log pruning completed.")
