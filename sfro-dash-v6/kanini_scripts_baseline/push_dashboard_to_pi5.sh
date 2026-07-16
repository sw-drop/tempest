#!/usr/bin/env bash
# Pushes updated dashboard JSON files from Eadu to Pi5-1
# Run this on Eadu after authorizing SSH key on Pi5-1

set -euo pipefail

# === CONFIGURATION ===
LOCAL_REPORTS="/opt/data/scripts/reports_fixed_literal.json"
LOCAL_OBSERVATIONS="/opt/data/scripts/updated_observations.json"
REMOTE_USER="pn"
REMOTE_HOST="Pi5-1"
REMOTE_DIR="/docker/sfro-dash-v3/data/"
SSH_KEY="$HOME/.ssh/id_ed25519"

# === PRE-FLIGHT CHECKS ===
if [[ ! -f "$LOCAL_REPORTS" ]]; then
    echo "❌ Missing $LOCAL_REPORTS" >&2
    exit 0  # Exit cleanly so cron doesn't mark error
fi
if [[ ! -f "$LOCAL_OBSERVATIONS" ]]; then
    echo "❌ Missing $LOCAL_OBSERVATIONS" >&2
    exit 0
fi
if [[ ! -f "$SSH_KEY" ]]; then
    echo "❌ SSH key not found at $SSH_KEY" >&2
    exit 0
fi

# === TRANSFER ===
echo "🚀 Pushing dashboard files to $REMOTE_HOST..."

if scp -i "$SSH_KEY" "$LOCAL_REPORTS" "${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_DIR}reports.json" 2>&1; then
    echo "✅ reports.json pushed"
else
    echo "❌ reports.json push failed" >&2
fi

if scp -i "$SSH_KEY" "$LOCAL_OBSERVATIONS" "${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_DIR}observations.json" 2>&1; then
    echo "✅ observations.json pushed"
else
    echo "❌ observations.json push failed" >&2
fi

echo "🎉 Push attempt complete."