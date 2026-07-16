#!/bin/bash
# deploy_fixes.sh

echo "Deploying updated SKILL.md to Hermes agent..."
scp /Users/gary/syncdata/Sync/dev/sfro-dash/.agents/skills/sfro-dash-control/SKILL.md Pi5-1:/docker/kanini/skills/sfro-dash-control/SKILL.md
ssh Pi5-1 "sudo chown 1000:1000 /docker/kanini/skills/sfro-dash-control/SKILL.md"

echo "Done."
