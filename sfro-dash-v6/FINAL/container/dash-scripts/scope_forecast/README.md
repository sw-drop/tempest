# Telescope Forecast Monitor (`scope_forecast`)

This directory contains the telescope schedule monitor compiler for the SFRO Dashboard V5. It queries the NINA active schedule logs to extract planned target schedules for tonight.

---

## Directory Structure
*   `fetch_forecasts.py` - Core Python script that executes API fetches, parses NINA scheduled target events, and outputs the final JSON configs.
*   `README.md` - This operations and maintenance guide.

---

## 1. Operations Guide (`fetch_forecasts.py`)

The script compiles tonight's scheduled imaging targets and outputs them as standard text cards.

### Command Line Arguments
| Argument | Default | Description |
| :--- | :--- | :--- |
| `-o`, `--out-dir` | `v5-test/data` | Output directory where the JSON files are stored |
| `--host` | `http://192.168.1.51:5002` | Remote dashboard host log API base URL |
| `--local-dir` | `None` | Optional local directory to read log files from directly instead of API |
| `--title-fra` | `FRA400 Forecast` | Custom card header title for the FRA400 card |
| `--title-q75` | `75Q Forecast` | Custom card header title for the 75Q card |

### Command Examples

1.  **Standard defaults (fetching from NINA API)**:
    ```bash
    python3 scope_forecast/fetch_forecasts.py -o v5-test/data
    ```

2.  **Using a local log directory** (for local testing):
    ```bash
    python3 scope_forecast/fetch_forecasts.py -o v5-test/data --local-dir data/
    ```

---

## 2. Dynamic Content Toggling (Scope vs Currency)

Because the dashboard frontend acts as a "dumb" client and dynamically renders card content based on whatever payload resides inside `fra400cap.json` and `q75cap.json`, you can **swap between scope forecast logs and exchange rates on the fly** simply by calling the respective compiler:

*   **To display Scope Forecasts**: Run the scope log compiler:
    ```bash
    python3 scope_forecast/fetch_forecasts.py -o v5-test/data
    ```
*   **To display Scope Captures**: Run the actual captures compiler:
    ```bash
    python3 scope_captures/fetch_captures.py -o v5-test/data
    ```
*   **To display Exchange Rates**: Run the currency compiler:
    ```bash
    python3 currency_rates/fetch_rates.py -o v5-test/data
    ```

---

## 3. JSON Outputs

The script writes two JSON files: `fra400cap.json` (left card) and `q75cap.json` (right card), adhering to the standard `"type": "text"` schema:

```json
{
  "title": "FRA400 Forecast",
  "subtitle": "Tonight (2026-07-12)",
  "type": "text",
  "data": {
    "text": "• Crescent Nebula\n• NGC 6871"
  }
}
```

---

## 4. Production Scheduling

This script is automatically executed by the master `controller.py` router (`dashboard_controller/controller.py`) based on the active schema mode. 
**Do not** schedule this script manually via system `cron`.
