#!/bin/bash
# Script to push Python script changes to Pi5-1 for SFRO Dash V6

REMOTE_USER="gary"
REMOTE_HOST="Pi5-1"
# We're updating the scripts for sfro-dash-v5 since it's the live directory
# (or v6 if it gets updated later). The user said: "The deployment of the dashboard is currently at /docker/sfro-dash-v5. As part of this project, we may change that to /docker/sfro-dash-v6"
REMOTE_PATH="/docker/sfro-dash-v5/"
LOCAL_PATH="./deployed_container/"
REMOTE_HOST="Pi5-1"

echo "Pushing full V6 update to ${REMOTE_HOST}:${REMOTE_PATH}..."

# We use rsync to sync the entire container context and omit caches/git
rsync -avz --exclude="*.pyc" --exclude="__pycache__" --exclude=".git" "$LOCAL_PATH" "${REMOTE_HOST}:${REMOTE_PATH}"

echo "Done! To apply these changes on the server, you will need to rebuild the container:"
echo "  docker compose up --build -d"
