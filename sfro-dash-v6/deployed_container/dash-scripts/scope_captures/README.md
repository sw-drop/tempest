# Telescope Capture Monitor (`scope_captures`)

This directory contains the telescope capture logs compiler for the SFRO Dashboard V5. It queries Discord logs for the two telescope channels (FRA400 and 75Q), compiles target exposure tallies, and formats them into a flat JSON card configuration.

---

## Directory Structure
*   `fetch_captures.py` - Core Python script that executes the Discord API fetch, aggregates exposure counts for active targets, and outputs the final JSON files.
*   `fetch_roof.py` - Core Python script that queries the Discord announcements channel, parses latest roof open/closed logs and nightly plan weather extracts, and writes to `roof.json`.
*   `discord_extractor.py` - Legacy sqlite database extractor daemon.
*   `README.md` - This operations and maintenance guide.

---

## 1. Operations Guide (`fetch_captures.py`)

The script is a stateless parser designed to be run periodically (e.g., every 15 minutes) via a scheduler or cron job. It generates flat card payloads at the configured output directory path.

### Command Line Arguments
| Argument | Default | Description |
| :--- | :--- | :--- |
| `-o`, `--out-dir` | `v5-test/data` | Mapped output path for the JSON files |
| `--title-fra` | `FRA400 Captured` | Custom card header title for the FRA400 card |
| `--title-q75` | `75Q Captured` | Custom card header title for the 75Q card |

### Credentials Configuration
The script requires a Discord Bot Token to authenticate and scrape channel history. It looks for the `DISCORD_TOKEN` environment variable in the following locations in order:
1.  System environment variables (`os.getenv("DISCORD_TOKEN")`)
2.  `.env` file in the execution directory
3.  `../.env` file in the parent directory
4.  `scope_captures/.env` file in the subdirectory

### Command Example
To execute the compiler and output files to `v5-test/data` with standard titles:
```bash
python3 scope_captures/fetch_captures.py -o v5-test/data
```

---

## 2. Key Algorithms & Logic

### A. 18-Hour Filtering Cutoff
To compile a representative summary of active nightly operations, the script establishes an **18-hour sliding window** relative to the current time:
*   Only messages sent within the last 18 hours are evaluated.
*   Messages older than 18 hours are discarded to keep the dashboard focused on current/recent targets.

### B. Exposure Log Parsing
1.  The script connects to the Discord API channel for each telescope:
    *   **FRA400 Channel ID**: `1407795208200126516`
    *   **75Q Channel ID**: `1440079351516237864`
2.  It filters messages for the term `_exps_` in their content (which marks a successful sub-exposure log in the Discord logging schema).
3.  It extracts the value from the `"Target"` embed field.
4.  It tallies up the target name occurrences and generates a list (e.g., `Target: Sadr Region x 67 Images`).
5.  If no exposures are registered within the 18-hour window, it outputs a fallback string: `"No exposures recorded in the last 18 hours."`

---

## 3. JSON Outputs

The script writes two JSON files: `fra400cap.json` and `q75cap.json` in the target directory. They follow the `"type": "text"` schema defined in the [FRONTEND_GUIDE.md](../FRONTEND_GUIDE.md):

```json
{
  "title": "FRA400 Captured",
  "subtitle": "",
  "type": "text",
  "data": {
    "text": "Target: Sadr Region x 67 Images"
  }
}
```

---

To deploy this in production, schedule the script to run every 15 minutes. Add the following to your system `cron` configuration:

```cron
*/15 * * * * cd /path/to/project && python3 scope_captures/fetch_captures.py -o sfro-dash-v5/data > /dev/null 2>&1
```

---

## 5. Operations Guide (`fetch_roof.py`)

This script queries the Discord announcements channel for the latest roof open/closed status changes and nightly plans, formatting them directly into `roof.json`.

### Arguments
| Argument | Default | Description |
| :--- | :--- | :--- |
| `-o`, `--out-dir` | `v5-test/data` | Mapped output path for the `roof.json` file |

### JSON Output Schema
```json
{
  "title": "OBSERVATORY ROOF OPEN",
  "title_color": "var(--green)",
  "subtitle": "",
  "type": "status",
  "data": {
    "status": "",
    "details": "Nightly Plan – 11 July 2026\nRoofs very likely OPEN all night!..."
  }
}
```

To schedule the roof status updates, add the following to your `cron` config:
```cron
*/15 * * * * cd /path/to/project && python3 scope_captures/fetch_roof.py -o sfro-dash-v5/data > /dev/null 2>&1
```
