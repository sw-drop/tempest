#!/bin/bash
# embed_json.sh - Inject dashboard JSON into index.html as JavaScript constants
# Usage: ./embed_json.sh [output_dir]
# Default output_dir: sfro-dash-v5-container/data

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")/sfro-dash-v5/sfro-dash-v5-container"

DATA_DIR="${1:-$PROJECT_DIR/data}"

# Function to generate embedded JSON block
generate_block() {
    local file="$1"
    local var_name="$2"
    if [[ -f "$file" ]]; then
        cat "$file" | python3 -c "import json,sys; d=json.loads(sys.stdin.read()); print(f'const {var_name} = {json.dumps(d, indent=2)};')"
    else
        echo "// $var_name not found"
    fi
}

# Backup original index.html
cp "$PROJECT_DIR/index.html" "$PROJECT_DIR/index.html.bak"

# Extract JavaScript block markers
HEAD=$(sed -n '1,/<script>/p' "$PROJECT_DIR/index.html" | head -n -1)
TAIL=$(sed -n '/<\/script>/,$p' "$PROJECT_DIR/index.html" | tail -n +2)

# Build new script block
{
    echo "$HEAD"
    echo "<script>"
    generate_block "$DATA_DIR/observations.json" "OBS"
    echo ""
    generate_block "$DATA_DIR/forecast.json" "FORECAST"
    echo ""
    # Add other JSON files as needed
    echo "$TAIL"
} > "$PROJECT_DIR/index.html.new"

# Atomic move
mv "$PROJECT_DIR/index.html.new" "$PROJECT_DIR/index.html"

echo "Embedded JSON into index.html from $DATA_DIR"