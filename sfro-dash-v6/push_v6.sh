#!/bin/bash
# Script to push Python script changes to Pi5-1 for SFRO Dash V6

REMOTE_USER="gary"
REMOTE_HOST="Pi5-1"
# We're updating the scripts for sfro-dash-v5 since it's the live directory
# (or v6 if it gets updated later). The user said: "The deployment of the dashboard is currently at /docker/sfro-dash-v5. As part of this project, we may change that to /docker/sfro-dash-v6"
REMOTE_PATH="/docker/sfro-dash-v5/dash-scripts/"
LOCAL_PATH="./deployed_container/dash-scripts/"

echo "Pushing Python script updates to ${REMOTE_HOST}:${REMOTE_PATH}..."

# We use rsync to sync only the python files and omit caches
rsync -avz --exclude="*.pyc" --exclude="__pycache__" --exclude=".env" "$LOCAL_PATH" "${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_PATH}"

echo "Done! Make sure to restart the daemon on the remote server."
