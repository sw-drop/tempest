#!/usr/bin/env bash
# Token Usage Report — runs via cron, output delivered verbatim to Telegram
# Silent between 00:00 and 08:59 UTC so Gary can sleep

# ── Quiet hours: 00:00 - 08:59 UTC ──
HOUR=$(date +%H)
if [ "$HOUR" -ge 0 ] && [ "$HOUR" -le 8 ]; then
    exit 0  # empty stdout = no message sent
fi

# ── Generate report ──
HERMES="/opt/hermes/.venv/bin/hermes"
REPORT=$($HERMES insights 2>&1)

if [ $? -ne 0 ]; then
    echo "⚠️  Token Usage Report — ERROR"
    echo ""
    echo "Failed to run hermes insights:"
    echo "$REPORT"
    exit 1
fi

echo "📊 Token Usage Report"
echo "Generated: $(date '+%Y-%m-%d %H:%M UTC')"
echo ""
echo "$REPORT"