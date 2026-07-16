#!/usr/bin/env python3
import subprocess
import sys

# Trigger the generic run_nas_backup.py script with warm parameters
def main():
    cmd = [
        "python3",
        "/opt/data/scripts/run_nas_backup.py",
        "warm",
        "/volume1/automation/warm.bat"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    # Print output so cron captures and forwards it to Telegram if there's a failure
    print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
        
    sys.exit(result.returncode)

if __name__ == "__main__":
    main()
