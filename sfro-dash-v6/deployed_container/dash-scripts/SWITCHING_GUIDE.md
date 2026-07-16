# SFRO Dashboard V5 Unified Configuration Guide

This guide is the complete reference manual for configuring, toggling, and customizing the behavior of the SFRO Dashboard V5. The architecture uses a unified State $\rightarrow$ Reaction model.

---

## 1. The Unified State File: `dashboard_config.json`

All configuration parameters (refresh rates, active modes, weather locations) are stored in a single JSON file. The dashboard orchestrator monitors this file every 5 seconds.

**If you edit this file, the dashboard will react instantly without requiring any process or container restarts.**

### Environment Path Mapping Registry
Depending on your execution environment, this file is located at:

| Context | Config File Path | Data Directory Path |
| :--- | :--- | :--- |
| **Local Mac** | `sfro-dash-v5-container/dash-scripts/dashboard_config.json` | `sfro-dash-v5-container/data/` |
| **Host Server** | `/docker/sfro-dash-v5/dash-scripts/dashboard_config.json` | `/docker/sfro-dash-v5/data/` |
| **Remote Agent Container (Hermes)** | **`/sfro-dash-v5/dash-scripts/dashboard_config.json`** | **`/sfro-dash-v5/data/`** |

*Note: For remote agents running inside the container sandbox, any files or paths outside `/sfro-dash-v5/` or your local workspace will result in "does not exist" errors due to security sandboxing.*

---

## 2. Managing Dashboard Behavior

To change any setting on the dashboard, simply edit the keys inside `dashboard_config.json`.

```json
{
  "active_mode": "captures",
  "weather_location": {
    "lat": 31.546944,
    "lon": -99.382222,
    "subtitle": "Starfront (Texas)",
    "timezone": "America/Chicago"
  },
  "refresh_intervals_seconds": {
    "controller": 90,
    "weather": 7200,
    "roof": 300,
    "images": 60
  }
}
```

### Changing the Active Mode
To toggle the lower display cards (`fra400cap.json` and `q75cap.json`), change the `"active_mode"` value.
Valid values are:
* `"captures"` - Shows the latest exposure logs from Discord.
* `"rates"` - Shows live currency exchange rates.
* `"forecasts"` - Shows upcoming NINA target schedules.

### Changing the Weather Forecast Location
To redirect the hourly weather timeline (`forecast.json`) in the top right to a new location, update the `"weather_location"` dictionary with the target coordinates, subtitle, and timezone. The timeline will update immediately upon saving.

### Adjusting Refresh Rates
To speed up or slow down how often backend scripts run, adjust the values in `"refresh_intervals_seconds"`.
* `"controller"`: How often the active mode data is regenerated.
* `"weather"`: How often the yr.no API is polled.
* `"roof"`: How often the observatory roof status is scraped.
* `"images"`: How often the local disk is scanned for new FITS captures.

### Manual Overrides (Ad-Hoc Text Inputs)
If you want to manually overwrite an automated card (such as the `roof.json` observatory status, the `tempest.json` weather, or any telescope image) with custom, ad-hoc text, you can supply the raw JSON payload in the `"overrides"` object. 

The orchestrator will forcibly apply these payloads every 5 seconds, guaranteeing that your text takes precedence over any automated background scripts.

```json
  "overrides": {
    "roof.json": {
      "title": "MAINTENANCE",
      "subtitle": "System Offline",
      "type": "text",
      "data": {
        "text": "The roof is currently under manual control."
      }
    }
  }
```

### 🔁 Revert to Base (Reset Procedure)
If you have made custom overrides or manual edits to the data files and wish to **completely undo everything and restore the dashboard to its automated base state**, follow this exact checklist:

1. **Clear Overrides**: Open `dashboard_config.json` and completely empty the `"overrides"` dictionary so it looks like this: `"overrides": {}`
2. **Delete Stale Data (Optional)**: If you want an immediate visual reset without waiting for the background scripts to naturally run, SSH into the server and delete the tampered files from the data directory. For example: `rm /docker/sfro-dash-v5/data/skycam.json /docker/sfro-dash-v5/data/fra400.json`
3. **Wait 5 Seconds**: The orchestrator (`runner.py`) will automatically detect the missing files and the empty overrides on its next 5-second loop. It will instantly regenerate the default fallback cards and restore full automated control to the background scrapers.
*(Note: There is no need to restart the Docker container).*

---

## 3. Repurposing Image Cards

The **All-Sky Camera (`skycam.json`)**, **FRA400 (`fra400.json`)**, and **75Q (`75q.json`)** cards are designed to display live feeds/exposures, but can be switched to custom images or text blocks without editing the HTML.

**CRITICAL RULE:** Do NOT directly edit the JSON files in the `data/` directory to accomplish this. All modifications must be made via the `"overrides"` dictionary in `dashboard_config.json`.

### Option A: Switching to a Custom Image
To display a static or custom image feed, add the card's payload to the `"overrides"` object in `dashboard_config.json`:

```json
  "overrides": {
    "fra400.json": {
      "title": "Custom Title",
      "subtitle": "Optional Subtitle",
      "type": "image",
      "data": {
        "src": "image_filename.jpg",
        "alt": "Image Description"
      }
    }
  }
```
* **Local Images:** Place the image inside the `data/` directory (e.g. `data/image_filename.jpg`) and reference it directly in `"src"`.
* **Remote Images:** You can use a fully qualified URL: `"src": "https://example.com/skycam.jpg"`.

### Option B: Switching to Text
To turn any image card into a text log, add the text payload to the `"overrides"` object:

```json
{
  "title": "Alert / Status Log",
  "subtitle": "System Message",
  "type": "text",
  "data": {
    "text": "The FRA400 is undergoing sensor cleaning.\nEstimated return to operations: Tuesday."
  }
}
```

* **Text Format:** Standard text strings support newlines (`\n`).
* **HTML Support:** If the text contains HTML angle brackets (`<` or `>`), the renderer will parse it as HTML. You can use CSS inline styling for custom designs:
  ```json
  "text": "<div style='color: var(--orange); font-weight: bold;'>Attention:</div>Maintenance in progress."
  ```

---

## 4. Text Sizing & Volume Guidance

The dashboard frontend uses a self-healing font scaler (`fitText`). It dynamically decreases font size from a starting maximum down to `0.6rem` to prevent card content from overflowing or causing scrollbars.

| Card ID | Grid Size | Recommended Text Volume |
| :--- | :--- | :--- |
| `#skycam-card` | 4 cols × 7 rows (Large) | **High:** Up to 15–20 lines (150–250 words) |
| `#fra400img-card` | 4 cols × 6 rows (Large) | **Medium-High:** Up to 12–15 lines (120–180 words) |
| `#q75img-card` | 4 cols × 6 rows (Large) | **Medium-High:** Up to 12–15 lines (120–180 words) |
| `#fra400cap-card` | 2 cols × 3 rows (Small) | **Low:** Up to 3–5 lines (30–50 words) |
| `#q75cap-card` | 2 cols × 3 rows (Small) | **Low:** Up to 3–5 lines (30–50 words) |

### Best Practices:
1. **Maintain Legibility:** Supplying too much text forces font sizes down to `0.6rem`, making them hard to read. Try to keep font sizes above `1.0rem` by staying within the recommended volume.
2. **Scroll Overflow:** If the text exceeds the limit at minimum font size, the card will display a scrollbar (`overflow: auto`).

---

## 5. Deployment Information

When you update scripts or configurations on your Mac, push them using the deploy script to synchronize the live server:
```bash
./deploy.sh
```

**Because the architecture is fully state-driven via JSON files, there is no need to manually restart the Docker containers when configuration changes.**
