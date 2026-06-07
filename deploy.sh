#!/bin/bash
# Exit immediately if any command fails
set -e

# Use a default commit message if none is provided
COMMIT_MSG="${1:-Automated deployment update at $(date '+%Y-%m-%d %H:%M:%S')}"

echo "=================================================="
echo "Step 1: Staging and committing changes to Git..."
echo "=================================================="

# Stage all files (excluding files ignored by .gitignore)
git add .

# Check if there are changes to commit
if ! git diff-index --quiet HEAD --; then
  echo "Changes detected. Committing with message: '$COMMIT_MSG'..."
  git commit -m "$COMMIT_MSG"
else
  echo "No local changes detected."
fi

# Push changes to GitHub
echo "Pushing changes to origin/main on GitHub..."
git push origin main

echo ""
echo "=================================================="
echo "Step 2: Syncing and deploying to Eadu..."
echo "=================================================="

# Run the python deployment script
python3 deploy_tempest.py

echo ""
echo "=================================================="
echo "Deployment Pipeline Complete!"
echo "=================================================="
