# Weather Compiler Management & Operations Guide

This directory contains the modular weather compiling system for the SFRO Dashboard (V5).

---

## 1. Directory Structure

*   `locations.json`: Configuration registry of all monitored locations.
*   `update_weather.py`: Master runner script that parses the registry, polls the appropriate weather APIs, and compiles the outcomes.
*   `fetch_tempest.py`: Single-station Tempest CLI utility (deprecated in favor of `update_weather.py`).
*   `fetch_yr.py`: Single-coordinate yr.no CLI utility (deprecated in favor of `update_weather.py`).

---

## 2. Managing Locations (`locations.json`)

To add, edit, or remove locations, edit the [locations.json](locations.json) file.

### Adding a Tempest Station
If the location has a physical WeatherFlow Tempest station:
```json
{
  "id": "starfront",
  "title": "Starfront",
  "source": "tempest",
  "station_id": "174867",
  "out": "v5-test/data/atmos_left.json"
}
```
*   `source` must be set to `"tempest"`.
*   `station_id` must be the Tempest station identifier.

### Adding a Coordinates-only Location (yr.no)
If no Tempest station is available, use geographic coordinates:
```json
{
  "id": "umhlanga",
  "title": "Umhlanga",
  "source": "coordinates",
  "latitude": -29.730028,
  "longitude": 31.086496,
  "out": "v5-test/data/atmos_right.json"
}
```
*   `source` must be set to `"coordinates"`.
*   `latitude` and `longitude` must be decimal numbers.

### Controlling Dashboard Slots
The dashboard reads its data from specific slots (e.g. `v5-test/data/atmos_left.json` and `v5-test/data/atmos_right.json`). 
To change which location is shown:
1.  Assign the target slot path to the `"out"` parameter of the desired location in `locations.json`.
2.  Assign a generic name (e.g. `v5-test/data/atmos_cape_town.json`) to the location being replaced so its data is still logged.

---

## 3. Running the Update

To trigger updates for all locations, run the master script:

```bash
python3 sfro-dash-v5/Tempest/update_weather.py
```

### Automation (Cron Schedule)
To run the updates automatically in the background every minute, add this entry to the server cron tab (`crontab -e`):

```cron
* * * * * cd /Users/gary/syncdata/Sync/dev/sfro-dash && python3 sfro-dash-v5/Tempest/update_weather.py > /dev/null 2>&1
```

---

## 4. Technical Details & Calculations

### Consolidated Metrics
To fit the locked grid layout of the dashboard cards, certain parameters are grouped together:
*   **Wind/Gust**: Combines average wind speed and maximum gust speed into a single row (`{wind} / {gust} mph`).
*   **Dew Pt/Margin**: Combines the dew point temperature and the calculated dew point margin (current temperature minus dew point temperature) into a single row (`{dew_pt} / {margin} °C`).

### Dew Point Approximation (Magnus-Tetens)
For coordinates-only stations, the MET Norway compact API does not supply the dew point. The script automatically calculates it using the Magnus-Tetens formula:

$$\gamma(T, RH) = \ln(RH/100) + \frac{17.625 \cdot T}{243.04 + T}$$

$$T_{dp} = \frac{243.04 \cdot \gamma}{17.625 - \gamma}$$

Where:
*   $T$ is the air temperature in Celsius.
*   $RH$ is the relative humidity in %.

### Focus Safety Limits
The script evaluates observation values against the following astronomy-safety thresholds. If a limit is exceeded, the item color is set to `"var(--red)"` to alert operators:
*   **Cloud cover**: $\le 60\%$ (otherwise warning)
*   **Wind speed**: $\le 28.0 \text{ mph}$
*   **Wind gust**: $\le 35.0 \text{ mph}$
*   **Humidity**: $\le 98.0\%$
*   **Temperature**: Between $28.0\text{°F}$ and $110.0\text{°F}$
*   **Dew Point Margin**: $\ge 3.0\text{°F}$ ($1.67\text{°C}$)
