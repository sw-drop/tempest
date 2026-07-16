#!/usr/bin/env bash
# Push observatory dashboard reports from Eadu to Pi5-1
# Runs on host (not sandbox), uses host SSH keys
set -euo pipefail

REMOTE_USER="pn"
REMOTE_HOST="Pi5-1"
REMOTE_DIR="/docker/sfro-dash-v3/data/"

# Ensure remote directory exists
ssh -o StrictHostKeyChecking=no "$REMOTE_USER@$REMOTE_HOST" "mkdir -p $REMOTE_DIR"

echo "🚀 Pushing reports to $REMOTE_HOST..."

# Push reports.json (renamed from reports_fixed_literal)
scp /opt/data/scripts/reports_fixed_literal.json "$REMOTE_USER@$REMOTE_HOST:${REMOTE_DIR}reports.json"
echo "✅ reports.json pushed"

# Push observations.json (renamed from updated_observations)
scp /opt/data/scripts/updated_observations.json "$REMOTE_USER@$REMOTE_HOST:${REMOTE_DIR}observations.json"
echo "✅ observations.json pushed"

echo "🎉 Push complete."
