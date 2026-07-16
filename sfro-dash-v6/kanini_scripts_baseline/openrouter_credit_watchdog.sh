#!/usr/bin/env bash
# Ensure script is executable

# OpenRouter Credit Check — silent watchdog
# Alerts via Telegram when remaining credits drop below threshold
# Runs from cron with no_agent=true (empty stdout = no delivery)

set -euo pipefail

THRESHOLD="${1:-0.10}"

# Prioritize environment variable (env_passthrough), then check fallback locations
if [ -n "${OPENROUTER_API_KEY:-}" ]; then
    API_KEY="$OPENROUTER_API_KEY"
else
    ENV_FILES=("/workspace/.env" "/opt/data/.env" "./.env" "${HERMES_HOME:-/opt/data}/.env")
    API_KEY=""
    for f in "${ENV_FILES[@]}"; do
        if [ -f "$f" ]; then
            API_KEY=$(grep '^OPENROUTER_API_KEY=' "$f" 2>/dev/null | head -1 | cut -d= -f2-)
            if [ -n "$API_KEY" ]; then break; fi
        fi
    done
fi

if [ -z "$API_KEY" ]; then
    echo "⚠️  OpenRouter Credit Check — ERROR"
    echo "Could not find OPENROUTER_API_KEY in environment or .env files"
    exit 1
fi

# Query OpenRouter API
RESPONSE=$(curl -s --retry 3 --retry-delay 5 -H "Authorization: Bearer $API_KEY" https://openrouter.ai/api/v1/auth/key)
REMAINING=$(echo "$RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('data',{}).get('limit_remaining',0))" 2>/dev/null || echo "0")
USAGE=$(echo "$RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('data',{}).get('usage',0))" 2>/dev/null || echo "0")

# Compare (using python3 for float comparison)
IS_LOW=$(python3 -c "print('1' if float('$REMAINING') < float('$THRESHOLD') else '0')" 2>/dev/null || echo "0")
if [ "$IS_LOW" = "1" ]; then
    echo "⚠️  OpenRouter Credits Running Low"
    echo ""
    echo "Remaining:  ${REMAINING}"
    echo "Total used: ${USAGE}"
    echo "Threshold:  ${THRESHOLD}"
    echo ""
    echo "Time to top up at https://openrouter.ai/credits"
fi
# else: silent exit — no message delivered
