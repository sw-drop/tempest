# Hermes Scripting and Sandbox Execution Guidelines

This document outlines the prescriptive rules, architecture, and standards for writing, testing, and executing scripts within the Hermes sandbox environment. The Hermes agent **must** read and adhere to these guidelines to ensure scripts execute successfully, respect the container security model, and deliver messages correctly.

---

## 1. Environment Architecture

To write scripts correctly, you must understand the separation between the **Main Container** and the **Sandbox Container**:

1. **Main Container (Hermes Gateway):**
   * This is where the core Hermes agent process, API clients, SQLite database (`state.db`), and the **Cron Scheduler** run.
   * It has full access to the project root directory (`/opt/data`), including environmental secrets (`/opt/data/.env`).
   * Background cron jobs are executed within this container context, meaning they have native access to all environment variables.

2. **Sandbox Container (Execution Sandbox):**
   * When you run terminal command tools, Hermes executes them inside an isolated, restricted sandbox container (e.g., `nikolaik/python-nodejs`).
   * **Mounts:** The sandbox mounts the `/workspace` directory and bind-mounts `/opt/data/scripts/` (read/write).
   * **Secrets Isolation:** The sandbox **does not** mount the parent `/opt/data` directory, meaning it cannot read the root `.env` file or `state.db`. 
   * **Credential Starvation:** Provider credentials (such as `OPENROUTER_API_KEY` or `TELEGRAM_BOT_TOKEN`) are deliberately stripped out and **not** passed into the sandbox environment.

---

## 2. Rules for Constructing Scripts

### Rule 1: Shebang and Executable Permissions
Every script must begin with a valid shebang and be marked executable.
* **Bash shebang:** `#!/usr/bin/env bash`
* **Python shebang:** `#!/usr/bin/env python3`
* **Command to run after creation:** `chmod +x /opt/data/scripts/your_script_name.sh`

### Rule 2: Output is the Message (stdout Capture)
If a cron job is configured with `"deliver": "telegram"` in `jobs.json`, the Cron engine automatically captures the standard output (`stdout`) of the script and sends it directly to the user's Telegram channel.
* **Do not pollute stdout:** Never print debugging messages, progress counters (e.g., `echo "Connecting..."`), or success confirmations. If printed, they will be sent to the user as part of the alert.
* **Silent Mode is default:** If a script evaluates a condition and determines that no alert needs to be sent, it must exit without printing anything to `stdout`. An empty output prevents the scheduler from sending empty messages.
* **Format with Markdown:** Print output in standard GitHub-style Markdown (using emojis, bold text, and line breaks) to format the Telegram notification nicely.

### Rule 3: No Manual Telegram API Calls
Never perform manual API requests to `api.telegram.org` or try to read `TELEGRAM_BOT_TOKEN` in your scripts. The system handles delivery natively.
* **Bad:** `curl -s -X POST "https://api.telegram.org/bot$TOKEN/sendMessage"...`
* **Good:** `echo "🚨 Alert: Threshold exceeded!"` (and let `"deliver": "telegram"` handle the routing).

### Rule 4: Graceful Credential Handling in Sandbox Tests
Because the sandbox environment has no access to the `.env` file or environment credentials, your scripts will run without API keys during testing.
* **Always handle missing keys gracefully:** Scripts must check if required keys (like `OPENROUTER_API_KEY`) are present. If a key is missing, print a warning to `stdout` and exit with code `0`.
* **Do not crash:** A script that crashes on a missing key cannot be verified by your terminal commands.

---

## 3. Script Testing & Deployment Workflow

When creating a new cron script:

1. **Write the Script:** Create the script file under the `/opt/data/scripts/` directory using your file write/edit tools.
2. **Set Permissions:** Run `chmod +x /opt/data/scripts/your_script.sh` in the terminal.
3. **Sandbox Test:** Execute the script from the terminal to verify its execution. Ensure it handles the lack of credentials gracefully:
   ```bash
   /opt/data/scripts/your_script.sh
   ```
4. **Deploy to jobs.json:** Register the script in the Cron Scheduler configuration (`/opt/data/cron/jobs.json`).
5. **Verify System Health:** Run the health check script `/opt/data/scripts/check_cron_status.py` in the terminal to verify that the scheduler loads the job successfully, has no permission issues, and is ticking normally.
6. **Path Constraint:** The Cron Scheduler enforces strict path traversal blocks. Your script **must** reside inside `/opt/data/scripts/` or `/opt/data/skills/`. Scripts configured outside these folders (e.g., in `/workspace/`) will be blocked from execution.

---

## 4. Reference Templates

### A. Bash Script Template
Use this template for network requests and simple diagnostic alerts:

```bash
#!/usr/bin/env bash
# Description: Checks a service endpoint and alerts natively if down.

set -euo pipefail

# 1. Graceful Credential Check (Required for sandbox testing)
API_KEY="${SERVICE_API_KEY:-}"
if [[ -z "$API_KEY" ]]; then
    # Print a warning and exit cleanly so the sandbox run doesn't fail
    echo "Warning: SERVICE_API_KEY is not defined. Exiting gracefully for test run."
    exit 0
fi

# 2. Silently perform check (suppress progress output)
STATUS_CODE=$(curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer $API_KEY" "https://api.service.com/health")

# 3. Output only on alert state
if [[ "$STATUS_CODE" -ne 200 ]]; then
    echo "⚠️ **Service Alert**"
    echo "The health check failed with status code: **$STATUS_CODE**."
fi
```

### B. Python Script Template
Use this template for complex parsing and state-based cron tasks:

```python
#!/usr/bin/env python3
# Description: Evaluates usage metrics and alerts if threshold is exceeded.

import os
import sys
import json
import urllib.request

def main():
    # 1. Graceful Credential Check (Required for sandbox testing)
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        print("Warning: OPENROUTER_API_KEY is not defined. Exiting gracefully for test run.")
        sys.exit(0)

    # 2. Silently fetch data
    url = "https://openrouter.ai/api/v1/auth/key"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {api_key}"})
    
    try:
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            usage = float(data.get("data", {}).get("usage", 0))
            limit = float(data.get("data", {}).get("limit", 0))
            
            # 3. Output alert if condition is met
            if usage > (limit * 0.9):
                print("🚨 **OpenRouter Credits Warning**")
                print(f"Usage has reached **${usage:.2f}** of your **${limit:.2f}** limit.")
    except Exception as e:
        # Gracefully log check errors
        print(f"Error checking usage: {e}")

if __name__ == "__main__":
    main()
```
