#!/bin/bash
# restart_scheduler.sh - Safely restart the SFRO-Dash V5 scheduler container
# Usage: ./restart_scheduler.sh [context_name]
# Default context_name: eadu

set -e
CONTEXT="${1:-eadu}"
PROJECT_DIR="/opt/data/scripts/sfro-dash-v5/sfro-dash-v5-container"

echo "Restarting SFRO-Dash V5 scheduler on context '$CONTEXT'..."

# Pull latest images
docker --context "$CONTEXT" compose -f "$PROJECT_DIR/docker-compose.yml" pull

# Restart scheduler service only
docker --context "$CONTEXT" compose -f "$PROJECT_DIR/docker-compose.yml" up -d sfro-dash-v5-scheduler

# Verify
docker --context "$CONTEXT" compose -f "$PROJECT_DIR/docker-compose.yml" ps sfro-dash-v5-scheduler

echo "Scheduler restarted. Check logs with:"
echo "  docker --context $CONTEXT logs -f sfro-dash-v5-scheduler"