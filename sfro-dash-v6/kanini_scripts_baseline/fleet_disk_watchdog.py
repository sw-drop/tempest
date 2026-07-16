#!/usr/bin/env python3
"""
Dashboard Disk Watchdog — silent watchdog for the fleet dashboard.
Fetches https://dashboard-der.pages.dev/api/metrics and alerts when any
disk hits >=98% utilisation.
no_agent=True compatible: stays silent when healthy, only speaks when critical.
"""

import json
import os
import sys
import urllib.request
import urllib.error

API_URL = "https://dashboard-der.pages.dev/api/metrics"
THRESHOLD = 98  # alert when used_percent >= this

CACHE_FILE = os.path.expanduser("~/.hermes/disk_alerts_seen.json")


def load_seen():
    """Load previously reported critical disks so we don't re-alert."""
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE) as f:
            return json.load(f)
    return {}


def save_seen(data):
    os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
    with open(CACHE_FILE, "w") as f:
        json.dump(data, f, indent=2)


def fetch_metrics():
    req = urllib.request.Request(API_URL, headers={"User-Agent": "Hermes-Disk-Watchdog/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def format_bytes(b):
    """Human-readable size."""
    for unit in ("B", "KB", "MB", "GB", "TB", "PB"):
        if abs(b) < 1024:
            return f"{b:.1f} {unit}"
        b /= 1024
    return f"{b:.1f} PB"


def main():
    try:
        hosts = fetch_metrics()
    except Exception as e:
        print(f"⚠️ Dashboard unreachable: {e}", file=sys.stderr)
        sys.exit(1)

    seen = load_seen()
    new_critical = []
    all_high = []

    for host in hosts:
        hostname = host.get("hostname", "?")
        for disk in host.get("disks", []):
            pct = disk.get("used_percent", 0)
            if pct is None:
                continue
            pct = int(round(pct))
            mount = disk.get("mount", "?")
            free = disk.get("available_bytes", 0)
            total = disk.get("size_bytes", 0)
            device = disk.get("device", "")

            if pct >= THRESHOLD:
                # Unique key for this disk
                key = f"{hostname}:{mount}"
                if key not in seen:
                    new_critical.append({
                        "hostname": hostname,
                        "mount": mount,
                        "device": device,
                        "used": pct,
                        "free": free,
                        "total": total,
                    })
                seen[key] = {
                    "used": pct,
                    "free": free,
                    "total": total,
                    "reported_at": None  # will set below
                }
            elif pct >= 85:
                # Track high-but-not-critical for awareness
                all_high.append({
                    "hostname": hostname,
                    "mount": mount,
                    "used": pct,
                    "free": free,
                    "total": total,
                })

    # If no new critical disks, silently exit
    if not new_critical:
        save_seen(seen)
        sys.exit(0)

    # Mark them as reported
    for hit in new_critical:
        key = f"{hit['hostname']}:{hit['mount']}"
        seen[key]["reported_at"] = __import__("datetime").datetime.utcnow().isoformat() + "Z"
    save_seen(seen)

    # Build alert message
    lines = ["🟠 **Disk Alert — fleet dashboard**", ""]
    for hit in new_critical:
        free_str = format_bytes(hit["free"])
        total_str = format_bytes(hit["total"])
        lines.append(f"**{hit['hostname']}** — `{hit['mount']}`")
        lines.append(f"   {hit['used']}% full — {free_str} free of {total_str}")
        lines.append("")

    # Add context about approaching disks
    if all_high:
        lines.append("**Also approaching capacity:**")
        for d in sorted(all_high, key=lambda x: -x["used"]):
            free_str = format_bytes(d["free"])
            lines.append(f"• {d['hostname']} `{d['mount']}` — {d['used']}% ({free_str} free)")
        lines.append("")

    lines.append("🚀 Go to https://dashboard-der.pages.dev to investigate.")

    print("\n".join(lines))


if __name__ == "__main__":
    main()
