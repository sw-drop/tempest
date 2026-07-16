# Dashboard State Controller (`dashboard_controller`)

This directory contains the central dashboard state controller for the SFRO Dashboard V5. It acts as an orchestrator that checks a single configuration file (`active_mode.json`) and executes the correct background compiler script for your cards.

This allows external agents or automation scripts to instantly toggle what the dashboard displays simply by editing a text file, instead of messing with system schedules.

---

## Directory Structure
*   `controller.py` - Master Python script that parses the config mode and runs the corresponding sub-script.
*   `active_mode.json` - Configuration state file holding the active display mode.
*   `README.md` - This operations manual.

---

## 1. How It Works

Instead of scheduling `fetch_rates.py`, `fetch_forecasts.py`, or `fetch_captures.py` separately inside system `cron`, **only this controller script is scheduled in production**.

### Cron Configuration
```cron
*/15 * * * * cd /path/to/project && python3 dashboard_controller/controller.py -o sfro-dash-v5/data > /dev/null 2>&1
```

Every 15 minutes, the controller runs, reads `active_mode.json`, and updates the cards according to your selected view.

---

## 2. Supported Modes

The `active_mode.json` config supports three modes:

| Mode Value | Script Triggered | Card Titles Generated |
| :--- | :--- | :--- |
| `"captures"` | `scope_captures/fetch_captures.py` | `"FRA400 Captured"` / `"75Q Captured"` |
| `"forecasts"` | `scope_forecast/fetch_forecasts.py` | `"FRA400 Forecast"` / `"75Q Forecast"` |
| `"rates"` | `currency_rates/fetch_rates.py` | `"GBP to ZAR"` / `"GBP to USD"` (default pairs) |

---

## 3. How to Toggle Views (For Agents/Scripts)

To change the active dashboard view, overwrite the content of [active_mode.json](active_mode.json):

### Display Telescope Exposures (Captures)
```json
{
  "mode": "captures"
}
```

### Display Telescope Schedules (Forecasts)
```json
{
  "mode": "forecasts"
}
```

### Display Exchange Rates (Currency)
```json
{
  "mode": "rates"
}
```

Once modified, the next automated cron run will compile the corresponding data, and the dashboard browser interface will update on its next 30-second refresh.

To trigger an **immediate** update after changing the JSON configuration, run:
```bash
python3 dashboard_controller/controller.py -o v5-test/data
```
