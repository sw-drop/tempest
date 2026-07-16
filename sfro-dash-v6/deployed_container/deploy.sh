#!/bin/bash
# deploy.sh - Synchronizes the self-contained docker_deploy directory with the remote server.
# Run this script from the local docker_deploy/ directory.

# --- CONFIGURATION ---
TARGET_USER="pi"
TARGET_HOST="Pi5-1"
TARGET_DIR="/docker/sfro-dash-v5"
# ---------------------

# Allow overriding configuration via command-line arguments
if [ -n "$1" ]; then
    TARGET_HOST="$1"
fi
if [ -n "$2" ]; then
    TARGET_DIR="$2"
fi

# Ensure we are in the directory containing the deploy script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "================================================================="
echo " Deploying SFRO Dashboard V5 Docker Environment"
echo "================================================================="
echo "Local source:  ${SCRIPT_DIR}"
echo "Remote target: ${TARGET_USER}@${TARGET_HOST}:${TARGET_DIR}"
echo "-----------------------------------------------------------------"

# Verify rsync is installed
if ! command -v rsync &> /dev/null; then
    echo "Error: rsync is not installed on this system." >&2
    exit 1
fi

# Run sync. We EXCLUDE active state databases and dynamic data folders to prevent
# wiping out live telescope telemetry or database files on the host server.
rsync -avz --progress \
    --exclude 'data/' \
    --exclude '.env' \
    --exclude '*.db' \
    --exclude '*.db-journal' \
    --exclude '__pycache__/' \
    --exclude '.DS_Store' \
    ./ "${TARGET_USER}@${TARGET_HOST}:${TARGET_DIR}/"

if [ $? -eq 0 ]; then
    echo "-----------------------------------------------------------------"
    echo "[✓] Deployment synchronization complete!"
    echo "-----------------------------------------------------------------"
    echo "To start/restart the docker services on the remote server, run:"
    echo "  ssh ${TARGET_USER}@${TARGET_HOST} 'cd ${TARGET_DIR} && docker-compose up --build -d'"
    echo "================================================================="
else
    echo "-----------------------------------------------------------------"
    echo "[!] Deployment failed. Please verify connection, SSH key, and path."
    echo "================================================================="
    exit 1
fi
