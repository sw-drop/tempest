#!/bin/bash
set -e

COMMIT_MSG="${1:-Automated deployment of sfro-dash-v3 at $(date '+%Y-%m-%d %H:%M:%S')}"

echo "=================================================="
echo "Step 1: Staging and committing changes to Git..."
echo "=================================================="

git add .

if ! git diff-index --quiet HEAD --; then
  echo "Changes detected. Committing with message: '$COMMIT_MSG'..."
  git commit -m "$COMMIT_MSG"
else
  echo "No local changes detected."
fi

echo "Pushing changes to origin/main on GitHub..."
git push origin main

echo ""
echo "=================================================="
echo "Step 2: Syncing and deploying to Pi5-1..."
echo "=================================================="

python3 deploy_tempest.py

echo ""
echo "=================================================="
echo "Deployment Pipeline Complete!"
echo "=================================================="
