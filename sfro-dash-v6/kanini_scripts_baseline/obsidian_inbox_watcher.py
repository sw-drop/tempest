#!/usr/bin/env python3
"""
Obsidian Inbox Watcher — Cron-safe, no_agent compatible.
Monitors the vault inbox for new .md files that have been idle for 45+ minutes.
Copies them to Docs/in/ for Antigravity to process (wiki + cross-references).

Exit codes:
  0 — nothing new (silent, no output)
  1 — new files found, copied to Docs/in/
"""

import os
import time
import sys
import shutil

# Config
# Container paths (Hermes sandbox): /opt/data/obsidian/New/ → vault inbox
# /opt/data/Docs/in/ → raw input for agent processing
# This script runs INSIDE the Hermes Docker container where /opt/data/ is available.
INBOX = "/opt/data/obsidian/New"     # Where Obsidian drops new notes (vault mount)
DEST = "/opt/data/Docs/in"           # Where agent processes them
STALE_SECONDS = 45 * 60              # 45 minutes idle before processing
MARKER_FILE = os.path.join(DEST, "__NEW_FILES.md")

def main():
    if not os.path.isdir(INBOX):
        # Inbox not mounted — nothing to do this tick
        return 0
    
    # Find stale files
    now = time.time()
    stale = []
    for fname in sorted(os.listdir(INBOX)):
        if not fname.endswith(".md"):
            continue
        fpath = os.path.join(INBOX, fname)
        try:
            mtime = os.path.getmtime(fpath)
        except OSError:
            continue
        
        age_seconds = now - mtime
        if age_seconds >= STALE_SECONDS:
            stale.append(fname)
    
    if not stale:
        # Nothing new — silent exit
        return 0
    
    # Copy stale files to Docs/in/
    copied = []
    for fname in stale:
        src = os.path.join(INBOX, fname)
        dst = os.path.join(DEST, fname)
        try:
            shutil.copy2(src, dst)
            copied.append(fname)
        except Exception as e:
            print(f"ERROR copying {fname}: {e}", file=sys.stderr)
    
    if not copied:
        return 0
    
    # Write marker file with list of new files
    with open(MARKER_FILE, "w") as fh:
        fh.write("# New Obsidian Files — Ready for Processing\n\n")
        fh.write(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        for fname in copied:
            fh.write(f"- {fname}\n")
    
    # Remove processed files from inbox
    for fname in copied:
        src = os.path.join(INBOX, fname)
        try:
            os.remove(src)
        except Exception as e:
            print(f"WARNING could not remove {fname}: {e}", file=sys.stderr)
    
    # Output for cron delivery
    names = "\n".join(f"  • {n}" for n in copied)
    print(f"📄 {len(copied)} new note(s) copied to Docs/in/:\n{names}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())