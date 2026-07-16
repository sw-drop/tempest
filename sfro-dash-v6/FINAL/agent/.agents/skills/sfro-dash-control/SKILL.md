---
name: sfro-dash-control
description: Controls and diagnostics for the Starfront Observatory V5 Dashboard schema engine and displays.
---

# SFRO-Dash V5 Control & Diagnostics

You are interacting with the **SFRO-Dash V5 Dashboard** architecture. 

## 1. Context & Architecture Overview
*   **The Engine (Python)**: A lightweight Python state machine (`schema_engine.py`) runs natively on the dashboard's Docker scheduler container (`sfro-dash-v5-scheduler`). It automatically evaluates the `yr.no` forecast and the physical roof state, and determines the "Schema" (e.g., `RoofOpenLunch1`, `Supper1`) to display.
*   **The Controller**: A router (`controller.py`) automatically maps the active schema to the 10 data cards on the dashboard, switching between camera feeds, NASA APOD images, and text reports.
*   **Your Role (Hermes)**: You sit OUTSIDE the minute-to-minute schedule logic. Your role is strictly to provide the external text reports (Backup & Flower Monitor) and to execute manual schema overrides when commanded by the user.

## 2. Reporting Instructions (Your Routine Jobs)
When executing your daily cron jobs, you MUST save your textual output summaries directly into the dashboard's shared volume so the V5 Controller can display them:

*   **Daily Backup Volume Report**: 
    Execute `/opt/data/scripts/daily_backup_report.py` and write the stdout directly to `/sfro-dash-v5/data/reports/backup.txt`.
*   **Night Sky Flower Monitor**: 
    Execute `/opt/data/scripts/night_sky_flower_monitor.sh` and write the stdout directly to `/sfro-dash-v5/data/reports/flower.txt`.
*   **Roof Status Forecast Summary**:
    Execute `/opt/data/scripts/generate_roof_summary.py`. This generates an LLM summary of the yr.no forecast. The output is written directly to `/sfro-dash-v5/data/reports/roof_forecast_summary.txt`.

*(Note: The dashboard controller reads these `.txt` files automatically whenever the active schema demands it).*

## 3. Executive Override (Manual Control)
If the user commands you to "override the dashboard", "force the dashboard to Supper1", or "set the schema to Afternoon1":
Write a JSON override file to the dashboard's data directory:
```bash
echo '{"override": "Supper1"}' > /sfro-dash-v5/data/override.json
```
To remove the override and return control to the automatic Python engine:
```bash
rm /sfro-dash-v5/data/override.json
```

### Custom Card Overrides
If you need to display a completely custom alert or image on a specific card (e.g. `roof`, `fra400`, `75q`, `fra400cap`, `q75cap`, or `skycam`):
Do NOT overwrite the active card files. Instead, create a file named `custom_<cardname>.json` (for example: `custom_75q.json`, `custom_roof.json`) in the `/sfro-dash-v5/data/` directory. 
The V5 controller will automatically prioritize these files and display them. 
To revert to normal, simply delete the custom file.

**Crucial: You MUST format the JSON correctly or the card will be blank.**

**To display a Text Message (Use this on ANY card, even image cards):**
```json
{
  "title": "My Custom Title",
  "subtitle": "My Subtitle",
  "type": "text",
  "data": {
    "text": "The message or markdown you want to display on the card."
  }
}
```

**To display a Custom Image (ONLY use if you have a REAL image URL):**
> **WARNING:** Do NOT use fake placeholder URLs like `example.com`. If you don't have a real image URL to display, use the `text` schema above to display a message instead.
```json
{
  "title": "My Custom Image",
  "subtitle": "Source name",
  "type": "image",
  "data": {
    "src": "https://real-domain.com/path/to/actual_image.jpg",
    "alt": "Image description"
  }
}
```

## 4. Diagnostics & Troubleshooting
If the user reports that the dashboard is frozen, the schema is wrong, or cards are blank, follow these diagnostic steps on Pi5-1:

### Symptom: Dashboard is completely unreachable or frozen
Check the Nginx container:
`docker logs sfro-dash-v5-web`
`docker ps | grep sfro-dash`

### Symptom: The Schema is stuck on the wrong mode
Check what the Python engine thinks the active schema is:
`cat /sfro-dash-v5/data/active_schema.json`

Check if a manual override is currently enforcing a schema (and delete it if necessary):
`cat /sfro-dash-v5/data/override.json`

Check the scheduler logs for Python tracebacks (perhaps the Met.no API is down):
`docker logs sfro-dash-v5-scheduler --tail 50`

### Symptom: Image cards are blank
The image watcher converts FITS files to `.jpg`. Check if the files exist:
`ls -la /sfro-dash-v5/data/*.jpg`
If they don't, the telescope hasn't captured anything yet. The controller handles this fallback automatically.
