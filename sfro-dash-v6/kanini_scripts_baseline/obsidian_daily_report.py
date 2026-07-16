#!/usr/bin/env python3
"""
Daily report: counts docs processed from New/ to _Notes/ in the last 24h.
Runs as a no_agent Hermes cron job — prints summary or stays silent if nothing new.
"""

import os
import time

NOTES = "/opt/data/obsidian/_Notes"
INBOX = "/opt/data/obsidian/New"

now = time.time()
day_ago = now - 86400

# Count files moved to _Notes/ in the last 24h
new_today = 0
total = 0

if os.path.isdir(NOTES):
    for fname in os.listdir(NOTES):
        if not fname.endswith(".md"):
            continue
        fpath = os.path.join(NOTES, fname)
        try:
            mtime = os.path.getmtime(fpath)
            total += 1
            if mtime >= day_ago:
                new_today += 1
        except OSError:
            continue

# Count whats waiting in inbox
inbox_count = 0
if os.path.isdir(INBOX):
    inbox_count = len([f for f in os.listdir(INBOX) if f.endswith(".md")])

# Output
lines = []
lines.append("📋 **Obsidian Vault — Daily Report**")
lines.append(f"  • Processed yesterday: **{new_today}** new doc(s)")
lines.append(f"  • Total in _Notes_: **{total}** docs")
lines.append(f"  • Awaiting in New/: **{inbox_count}** doc(s)")

print("\n".join(lines))