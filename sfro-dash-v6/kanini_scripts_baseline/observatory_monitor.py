#!/opt/hermes/.venv/bin/python3
import sys, re, requests

URL = "https://uptime.pillay.uk/status/pillay"

def fetch_page():
    r = requests.get(URL, timeout=15)
    r.raise_for_status()
    return r.text

def get_roof_percent(html: str) -> int:
    """Return the Observatory Roof Open percentage (0 = closed)."""
    m = re.search(r"_Observatory Roof Open_.*?(\d+)%", html, re.IGNORECASE | re.DOTALL)
    if not m:
        return 0
    return int(m.group(1))

def main():
    html = fetch_page()
    pct = get_roof_percent(html)
    if pct > 0:
        print(f"⚠️ Observatory roof is OPEN (status {pct}%)")
    # If closed, stay silent (no output)

if __name__ == "__main__":
    main()