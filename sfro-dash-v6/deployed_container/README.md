# Starfront Observatory Dashboard (SFRO-Dash V5)

This repository contains the architecture, scripts, and deployment configuration for the **SFRO Dashboard V5**. 

---

## 1. System Architecture

The dashboard runs inside a two-container Docker stack deployed on **`Pi5-1`** (accessible locally at `http://192.168.1.51:8025/index.html`):

*   **`sfro-dash-v5-web` (Nginx)**: Serves the static page assets (`index.html`) and acts as the data API.
*   **`sfro-dash-v5-scheduler` (Python)**: Runs our master loop daemon (`runner.py`) as user `1000` (`pi`). It triggers background updates to compile JSON files served by the Nginx instance.

```text
sfro-dash-v5/ (Project Root)
├── Dockerfile
├── requirements.txt
├── docker-compose.yml
├── index.html
├── index.js
├── deploy_v5.py
└── dash-scripts/                <-- All python execution code lives here
    ├── runner.py                <-- Master loop runner
    ├── dashboard_config.json    <-- Unified state configuration file
    ├── Tempest/                 <-- Tempest & coordinates weather observer
    ├── currency_rates/          <-- Exchange rate compiler
    ├── dashboard_controller/    <-- active_mode controller
    ├── scope_captures/          <-- Discord logs and FITS image watchdog
    ├── scope_forecast/          <-- NINA target schedule compiler
    └── yr_forecast/             <-- MET Norway hourly weather timeline
```

---

## 2. Shared Directories & Mounts

*   **`data/`**: Shared directory bind-mounted between the scheduler and Nginx. This folder holds the compiled JSON configurations (e.g. `forecast.json`, `fra400.json`, `skycam.json`) and the downscaled telescope JPEGs.
*   **`images/`**: Mounted inside the scheduler container pointing to the raw telescope folders `/syncdata/75Q-Data/` and `/syncdata/FRA400-Data/` on the server host (read-only).
*   **Permissions**: All files created inside `data/` are automatically owned by user `1000:1000` (`pi:pi`), meaning they are immediately readable and writable by the host user and the Hermes agent.

---

## 3. Dynamic Card Toggling

To change the contents of the telescope dashboard cards, the Hermes agent edits the unified configuration file located at **`dash-scripts/dashboard_config.json`**:
```json
{
  "active_mode": "captures",
  "weather_location": { ... }
}
```
Supported modes are:
1.  `captures`: Displays actual overnight exposures logged in the telescope Discord channels.
2.  `forecasts`: Displays planned NINA target schedules for the coming night.
3.  `rates`: Displays active currency exchange rates.

---

## 4. Key References

*   For deployment and server execution steps, read: **[DOCKER_GUIDE.md](DOCKER_GUIDE.md)**.
*   For details on the layout grid and supported card JSON payloads, read: **[FRONTEND_GUIDE.md](FRONTEND_GUIDE.md)**.
*   For the kiosk display configuration on the observatory screen (Pi 3B+), read: **[Kiosk Solution.md](../Kiosk%20Solution.md)**.
