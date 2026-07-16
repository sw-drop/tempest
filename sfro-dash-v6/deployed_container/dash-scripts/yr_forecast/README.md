# Observatory Forecast Maintenance Guide (`yr_forecast`)

This directory contains the automated weather forecast compiler for the SFRO Dashboard V5. It queries MET Norway (yr.no) for hourly observations, localizes the timestamps, chronologically inserts sunrise/sunset events, and formats the output into a flat JSON card configuration.

---

## Directory Structure
*   `fetch_forecast.py` - Core Python script that executes the API fetch, timezone conversions, event insertions, and outputs the final JSON.
*   `README.md` - This operations and maintenance manual.

---

## 1. Forecast Script (`fetch_forecast.py`)

The script is a stateless parser designed to be run periodically (e.g. hourly) via cron. It generates a flat card payload at the configured output path.

### Command Line Arguments
| Argument | Default | Description |
| :--- | :--- | :--- |
| `--lat` | `51.45695971753735` | Latitude of the target location (Wandsworth default) |
| `--lon` | `-0.18686539472508437` | Longitude of the target location (Wandsworth default) |
| `-z`, `--timezone` | `Europe/London` | Target timezone name (e.g. `Europe/London` or `America/Chicago`) |
| `-n`, `--hours` | `8` | Number of columns to display on the dashboard (default: 8, max: 24) |
| `--sunset` | `None` | Optional static override for local sunset time (e.g. `17:15`). If omitted, sunset is fetched dynamically. |
| `--sunrise` | `None` | Optional static override for local sunrise time (e.g. `05:30`). If omitted, sunrise is fetched dynamically. |
| `-t`, `--title` | `Observatory Forecast` | Card Title displayed in the header |
| `-s`, `--subtitle` | `London/Wandsworth` | Card Subtitle displayed in the header |
| `-o`, `--out` | `v5-test/data/forecast.json` | Mapped output path for the web server |

### Example Command
To update the Wandsworth forecast with 8 columns, automatically fetching sunrise/sunset times:
```bash
python3 yr_forecast/fetch_forecast.py -n 8 -z Europe/London -o v5-test/data/forecast.json
```

---

## 2. Key Algorithms & Logic

### A. 45-Minute Boundary Transition
To ensure the dashboard remains relevant, the timeline automatically steps forward to the next hour when the target location's clock passes **45 minutes past the hour**:
*   **Time <= XX:44**: The forecast includes and starts at the current hour (`XX:00`).
*   **Time >= XX:45**: The current hour is deemed complete, and the forecast shifts to start at the next hour (`(XX+1):00`).

### B. Timezone & DST Handling
Using Python's standard `zoneinfo.ZoneInfo` library, the script converts yr.no's UTC timeseries into the location's local timezone. DST offsets are calculated automatically by the operating system's database.

### C. Sunrise/Sunset Insertion (Dynamic or Override)
1.  If `--sunset` or `--sunrise` are not explicitly passed, the script queries the free `sunrise-sunset.org` API using the latitude and longitude parameters to obtain the exact astronomical times for the target date.
2.  The times are converted and localized to the target timezone.
3.  During timeseries evaluation, the script checks if the event timestamp falls chronologically between two hourly forecast intervals.
4.  If so, the event is inserted at the exact chronological index (e.g., `17:15` is inserted between `17:00` and `18:00`).
5.  The final list is sliced to the exact `--hours` count, replacing the furthest hourly column with the event.

---

## 3. Frontend Rendering (`index.html`)

The frontend rendering in [index.html](file:///Users/gary/syncdata/Sync/dev/sfro-dash/sfro-dash-v5/index.html) handles the visual display of these columns:

### Weather Icons (jsDelivr CDN)
All weather symbols and cloud icons are delivered via the fast, edge-cached **jsDelivr CDN**:
`https://cdn.jsdelivr.net/gh/metno/weathericons@main/weather/svg/{symbol_code}.svg`

### Sunrise/Sunset (Option 8 Duotone SVGs)
Events are rendered inline using the selected **Geometric Rayburst (Option 8)** SVG designs:
*   **Color coding**: Sunrise text and arrows are green (`#10b981`); Sunset text, arrows, and rays are orange (`#ff9800`).
*   **Alignment spacer**: All weather values are replaced with non-breaking spaces (`&nbsp;`) to preserve standard font heights and keep all 8 columns aligned horizontally.

---

## 4. Production Scheduling

To deploy this in production, set up a cron job on the host server to run the compiler script every hour (usually at 1 minute past the hour to fetch the latest api release). Because sunset and sunrise times are now fetched dynamically, you do not need to specify them in the cron configuration:

```cron
1 * * * * cd /path/to/project && python3 yr_forecast/fetch_forecast.py -n 8 -z Europe/London -o sfro-dash-v5/data/forecast.json > /dev/null 2>&1
```
