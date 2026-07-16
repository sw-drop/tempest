#!/usr/bin/env python3
"""
OpenRouter Daily Spend Tracker
Fetches current usage, compares with yesterday's total, and reports the delta.
"""

import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

# Configuration
HERMES_HOME = os.environ.get("HERMES_HOME", "/opt/data")
LEDGER_FILE = Path(HERMES_HOME) / ".hermes" / "openrouter_spend.json"
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_HOME_CHANNEL", "1461012131")

def get_api_key():
    """Read OPENROUTER_API_KEY from env or .env file."""
    if "OPENROUTER_API_KEY" in os.environ:
        return os.environ["OPENROUTER_API_KEY"]
    hermes_home = os.environ.get("HERMES_HOME", "/opt/data")
    for p in ["/workspace/.env", "/opt/data/.env", "./.env", f"{hermes_home}/.env", "/mnt/ssd/docker/hermes/.env", "/opt/hermes/.env"]:
        if Path(p).exists():
            with open(p) as f:
                for line in f:
                    if line.startswith("OPENROUTER_API_KEY="):
                        return line.strip().split("=", 1)[1]
    return None

def fetch_current_usage(api_key):
    """Fetch current usage from OpenRouter API."""
    import urllib.request
    import urllib.error
    
    url = "https://openrouter.ai/api/v1/auth/key"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {api_key}"})
    try:
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            return float(data.get("data", {}).get("usage", 0))
    except (urllib.error.URLError, json.JSONDecodeError, KeyError) as e:
        print(f"ERROR: Could not fetch usage from OpenRouter: {e}", file=sys.stderr)
        sys.exit(1)

def load_ledger():
    """Load the ledger of daily totals."""
    if LEDGER_FILE.exists():
        with open(LEDGER_FILE) as f:
            return json.load(f)
    return {}

def save_ledger(ledger):
    """Save the ledger."""
    LEDGER_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LEDGER_FILE, "w") as f:
        json.dump(ledger, f, indent=2)

def main():
    api_key = get_api_key()
    if not api_key:
        print("ERROR: Could not find OPENROUTER_API_KEY")
        return

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    ledger = load_ledger()

    # Find the most recent previous date (strictly before today)
    prev_date = None
    for d in sorted(ledger.keys(), reverse=True):
        if d < today:
            prev_date = d
            break

    current_usage = fetch_current_usage(api_key)

    if prev_date and prev_date in ledger:
        yesterday = ledger[prev_date]
        daily_spend = current_usage - yesterday
        telegram_message = f"OpenRouter Spend ({prev_date}): ${daily_spend:.2f}\nTotal Used: ${current_usage:.2f}"
    else:
        telegram_message = f"OpenRouter Tracker started. Total: ${current_usage:.2f}"

    # Record today's total
    ledger[today] = current_usage
    save_ledger(ledger)

    # Send alert
    print(telegram_message)

if __name__ == "__main__":
    main()