#!/bin/bash
# deploy_single_file.sh
# Safely deploys a single file from the local workspace to the Pi5-1 server.
# Run this script from the root of the sfro-dash-v5 workspace.

TARGET_USER="pi"
TARGET_HOST="Pi5-1"
TARGET_BASE_DIR="/docker/sfro-dash-v5"

if [ -z "$1" ]; then
    echo "Usage: $0 <relative/path/to/local/file>"
    echo "Example: $0 dash-scripts/dashboard_controller/controller.py"
    exit 1
fi

LOCAL_FILE="$1"

if [ ! -f "$LOCAL_FILE" ]; then
    echo "Error: Local file '$LOCAL_FILE' does not exist."
    exit 1
fi

# Extract the directory part of the path to ensure the remote structure exists
REMOTE_SUBDIR=$(dirname "$LOCAL_FILE")
REMOTE_FULL_DIR="${TARGET_BASE_DIR}/${REMOTE_SUBDIR}"
REMOTE_FULL_PATH="${TARGET_BASE_DIR}/${LOCAL_FILE}"

echo "========================================================"
echo " Deploying single file..."
echo " File:   $LOCAL_FILE"
echo " Target: ${TARGET_USER}@${TARGET_HOST}:${REMOTE_FULL_PATH}"
echo "========================================================"

# 1. Ensure the target subdirectory exists
ssh "${TARGET_USER}@${TARGET_HOST}" "mkdir -p '${REMOTE_FULL_DIR}'"

# 2. Securely copy the file
scp "$LOCAL_FILE" "${TARGET_USER}@${TARGET_HOST}:${REMOTE_FULL_PATH}"

if [ $? -eq 0 ]; then
    # 3. Align permissions to what the remote docker container (1000:1000) expects
    ssh "${TARGET_USER}@${TARGET_HOST}" "sudo chown 1000:1000 '${REMOTE_FULL_PATH}' && sudo chmod 775 '${REMOTE_FULL_PATH}'"
    echo "[✓] Successfully deployed and set permissions for $LOCAL_FILE"
else
    echo "[!] Deployment failed."
    exit 1
fi
