# Starfront Dashboard V3 - JSON Data Formats

The dashboard reads three static JSON files from the `/data/` subdirectory to dynamically populate all layout widgets.

---

## 1. `observations.json`
* **Used by:** Weather & Roof status parameter list (bottom-left) and "ROOF OPEN/CLOSED" status header (top-right).
* **Update Interval:** Generated every 60 seconds by the Tempest weather station collector daemon.

### Structure & Example:
```json
{
  "station_id": 174867,
  "station_name": "Starfront Observatory",
  "last_fetched": 1783681451,
  "physical_roof_status": "Open", 
  "processed": {
    "sunrise": 1783662000,
    "sunset": 1783711200,
    "daytime_status": "nighttime",
    "night_forecast": [
      {
        "timestamp": 1783718400,
        "cloud": 10.0,
        "symbol_code": "clearsky_night",
        "temp_c": 22.4,
        "temp_f": 72.3
      }
    ],
    "metrics": {
      "temp_c": 21.5,
      "temp_f": 70.7,
      "dew_point_c": 11.2,
      "dew_point_f": 52.2,
      "dew_point_margin_c": 10.3,
      "dew_point_margin_f": 18.5,
      "humidity": 52,
      "wind_avg_mps": 2.4,
      "wind_avg_mph": 5.4,
      "wind_gust_mps": 4.1,
      "wind_gust_mph": 9.2,
      "wind_dir": 180,
      "pressure_hpa": 1012.4,
      "pressure_inhg": 29.89,
      "precip_mm": 0.0,
      "precip_in": 0.0,
      "lightning_count_1h": 0
    }
  },
  "roof_status": {
    "allowed": true,
    "reasons": [],
    "checks": {
      "wind": { "val": 5.4, "unit": "mph", "limit": "<= 28 mph", "ok": true },
      "humidity": { "val": 52, "unit": "%", "limit": "<= 98%", "ok": true },
      "temperature": { "val": 70.7, "unit": "°F", "limit": "28°F - 110°F", "ok": true },
      "wind_gust": { "val": 9.2, "unit": "mph", "limit": "<= 35 mph", "ok": true },
      "dew_point_margin": { "val": 18.5, "unit": "°F", "limit": ">= 3°F", "ok": true },
      "clouds": { "val": 10.0, "unit": "%", "limit": "<= 60%", "ok": true }
    }
  }
}
```

---

## 2. `reports.json`
* **Used by:** FRA400/75Q Capture status boxes (middle-right) and Roof Status detailed text card (bottom-right).
* **Update Interval:** Compiled every 5 minutes by querying Discord history and telescope logs.

### Parsing Logic:
The frontend splits the `capture` string on the `🏠` emoji:
* Everything **before** `🏠` is parsed, has target formatting/whitespace cleaned up, and renders inside the **FRA400 Capture** and **75Q Capture** boxes.
* Everything **after** `🏠` has formatting stripped and is rendered inside the **Roof Status** detail box.

### Structure & Example:
```json
{
  "capture": "🔭 **Nightly Capture & Operations Report - Thursday**\n\n📸 **Exposure Summary**\n  * FRA400:\n    * Target: NGC 7023 x 85 Images\n  * 75Q:\n    * Target: Sh2-119 x 80 Images\n\n🏠 All Roofs OPENING (at 20:20 Central)\n  • Nightly Plan: Roofs very likely OPEN all night — clear skies, no rain risk",
  "forecast": "🌌 **Tonight's Observatory Forecast Friday (2026-07-10)**\nRoof Open Likelihood: **HIGH**\n  * Window 1: 21:00 - 05:30 (Avg Cloud: 5.0%)"
}
```

---

## 3. `images.json`
* **Used by:** FRA400/75Q FITS image title, target name, and filename headers.
* **Update Interval:** Checked every 10 seconds. Regenerated only when a new `.fits` file is processed in the telescope folders.

### Structure & Example:
```json
{
  "fra400": {
    "target": "FRA400 - NGC 6871 Panel 4",
    "filename": "2026-07-09_Ha_-5.00_exp300.00s_hfr1.66_star4720_0077"
  },
  "75q": {
    "target": "75Q - IC 5146 Cocoon Nebula",
    "filename": "2026-07-09_-5.00_exp300.00s_hfr1.99_star18945_0072"
  }
}
```
