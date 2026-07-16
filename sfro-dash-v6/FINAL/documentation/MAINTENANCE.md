# V5 Dashboard Maintenance & Diagnostics Guide

This guide outlines how the V5 Schema Orchestration engine works and how to troubleshoot it when things go wrong.

## 1. How the Engine Works
The dashboard UI (the 12x12 grid) is entirely deterministic and stateless. The logic is driven by two Python scripts running inside the `sfro-dash-v5-scheduler` Docker container:

1.  **`schema_engine.py` (Runs every 15 minutes)**: 
    *   Reads the UTC time.
    *   Fetches the `yr.no` forecast and looks for a window of `>= 2 hours` of `< 20% clouds` between sunset and sunrise to determine if the roof is "Forecast to Open".
    *   Reads `roof.json` to see if the roof is physically open.
    *   Selects 1 of 12 schemas (e.g. `RoofOpenLunch1`, `Supper1`) and writes it to `data/active_schema.json`.

2.  **`controller.py` (Runs every 15 seconds)**:
    *   Reads `data/active_schema.json`.
    *   Recompiles the individual JSON payloads for the 10 data cards (e.g. `skycam.json`, `fra400.json`, `forecast.json`).
    *   It uses a hardcoded mapping to decide if a card should show an Image (e.g. telescope FITS, APOD) or Text (e.g. Backup Report).

## 2. Common Failure Modes & Troubleshooting

### A. The Dashboard is Stuck / Not Updating
**Diagnosis**: The scheduler loop (`runner.py`) may have crashed.
**Fix**: 
1. SSH into the host server (`Pi5-1`).
2. Run `docker logs sfro-dash-v5-scheduler --tail 50`. Look for Python stack traces.
3. Restart the container: `docker restart sfro-dash-v5-scheduler`.

### B. The Wrong Schema is Displayed (e.g. Night cards during the day)
**Diagnosis**: The Met.no API might be rate-limiting us, or an override is in place.
**Fix**:
1. Check if a manual override is active: `cat /docker/sfro-dash-v5/data/override.json`. Delete it if it exists.
2. Check the output of the schema engine: `cat /docker/sfro-dash-v5/data/active_schema.json`.
3. Check the logs: `docker logs sfro-dash-v5-scheduler | grep "Schema Engine"`. If you see API errors, Met.no may have temporarily blocked the IP. It will self-resolve.

### C. Text Reports (Backup/Flower) are Missing
**Diagnosis**: The Hermes Agent has not dropped the reports into the shared volume.
**Fix**:
1. The dashboard expects the reports at `/docker/sfro-dash-v5/data/reports/backup.txt` and `flower.txt`.
2. Check if the files exist. If not, trigger the Hermes Agent to run its backup and flower monitor skills.

### D. FITS Images are not Updating
**Diagnosis**: The `image_watcher.py` script converts FITS to JPEG. If the JPEG is not updating, either the telescope is not writing new FITS files, or the converter is failing.
**Fix**:
1. Check the logs: `docker logs sfro-dash-v5-scheduler | grep FITS`.
2. Ensure the telescope is actually writing to the networked `images/` directory.

## 3. How to Temporarily Bypass the Engine
If you need to force the dashboard into a specific mode for testing (e.g. testing the `Supper1` layout), you can bypass the time/weather logic by creating an override file on the host server:

```bash
echo '{"override": "Supper1"}' > /docker/sfro-dash-v5/data/override.json
```
The dashboard will switch to the `Supper1` schema within 15 seconds.
To revert to automatic logic:
```bash
rm /docker/sfro-dash-v5/data/override.json
```

## 4. Custom Single Card Overrides (Agent Alerts)
If an agent (like Hermes) needs to display a custom alert or image on a specific card without changing the entire schema, it can write a custom JSON file to the data directory (e.g. `custom_fra400.json`, `custom_75q.json`, or `custom_skycam.json`).

The controller automatically prioritizes these `custom_*` files and suspends its normal scheduling for that specific slot.
To revert the card back to normal schedule, simply delete the custom file.

## 5. How to Add a New Card or Schema
1. **Add a new Schema**: Open `dash-scripts/schema_engine.py` and add the time/weather logic. Then, open `dash-scripts/dashboard_controller/controller.py` and define what the 10 cards should display for that schema.
2. **Add a new Card**: You must update the HTML layout in `index.html`, add the ID mapping in `index.js`, and finally add the JSON payload generation for that new ID inside `controller.py`.
