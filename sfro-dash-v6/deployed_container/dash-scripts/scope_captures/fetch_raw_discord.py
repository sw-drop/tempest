import os, requests, json
from datetime import datetime, timedelta

TOKEN = "your_token"
with open('.env', 'r') as f:
    for line in f:
        if line.startswith("DISCORD_TOKEN="):
            TOKEN = line.split("=", 1)[1].strip().strip('"').strip("'")

HEADERS = {"Authorization": f"Bot {TOKEN}", "User-Agent": "Test/1.0"}

def fetch(channel_id):
    url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
    params = {"limit": 100}
    try:
        resp = requests.get(url, headers=HEADERS, params=params)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        return []

print("Fetching 75Q...")
msgs = fetch(1440079351516237864) # 75Q channel ID
for m in msgs[:20]:
    content = m.get("content", "")
    embeds = m.get("embeds", [])
    embed_text = " ".join([e.get("title", "") + " " + e.get("description", "") for e in embeds])
    ts = m.get("timestamp")
    print(f"[{ts}] {content} | {embed_text}")

