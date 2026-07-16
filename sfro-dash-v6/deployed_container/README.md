# Starfront Observatory Dashboard (SFRO-Dash V6)

This repository contains the architecture, scripts, and deployment configuration for the **SFRO Dashboard V6**. 

---

## 1. System Architecture

The dashboard runs inside a two-container Docker stack deployed on **`Pi5-1`** (accessible locally at `http://192.168.1.51:8025/index.html`):

*   **`sfro-dash-v5-web` (Nginx)**: Serves the static page assets (`index.html`) and serves the finalized JSON card files from `./app_data` (mapped internally to `/usr/share/nginx/html/data`).
*   **`sfro-dash-v5-scheduler` (Python)**: Runs our unified master loop scheduler (`daemon.py`) as user `1000` (`pi`). It orchestrates background scraping tasks and evaluates the active schema automatically via the FSM engine (`schema_engine.py`).

```text
sfro-dash-v6/ (Project Root)
├── Dockerfile
├── requirements.txt
├── docker-compose.yml
├── index.html
├── index.js
├── deploy.sh
└── dash-scripts/                <-- All python execution code lives here
    ├── daemon.py                <-- Master loop scheduler
    ├── schema_engine.py         <-- FSM schema decision engine
    ├── Tempest/                 <-- Tempest & coordinates weather observer
    ├── currency_rates/          <-- Exchange rate compiler
    ├── dashboard_controller/    <-- active_schema routing controller
    ├── scope_captures/          <-- Discord logs and FITS image watchdog
    ├── scope_forecast/          <-- NINA target schedule compiler
    └── yr_forecast/             <-- MET Norway hourly weather timeline
```

---

## 2. Shared Directories & Safety Isolation

To prevent remote agents (like Hermes) from accidentally overwriting system files, we split the directories:

*   **`app_data/` (System Output)**: Protected directory where the Python scheduler writes compiled JSON configurations (e.g. `forecast.json`, `fra400.json`, `skycam.json`) and the downscaled telescope JPEGs. Mapped to Nginx.
*   **`data/` (Agent Inbox)**: Directory where the remote agent writes custom card overrides (`custom_*.json`, `override.json`) and text reports (`reports/*.txt`).
*   **Permissions**: Both directories are owned by user `1000:1000` (`pi:pi`) on the host.

---

## 3. Dynamic Card Overrides (Agent Interface)

The dashboard routing is fully automated. If a manual override is needed, write a JSON file to the **`data/`** directory. The controller will instantly prioritize it:

1.  **Global Layout Override (`override.json`)**:
    Force a specific schema layout (e.g. `Supper1`):
    ```json
    {"override": "Supper1"}
    ```
2.  **Custom Card Override (`custom_<cardname>.json`)**:
    Override a specific card slot (e.g., `custom_roof.json` or `custom_75q.json`):
    ```json
    {
      "title": "Alert / Status Log",
      "subtitle": "System Message",
      "type": "text",
      "data": {
        "text": "Maintenance in progress."
      }
    }
    ```
    Delete the override JSON file to revert back to automated background rotations.

---

## 4. Key References

*   For deployment and server execution steps, read: **[DOCKER_GUIDE.md](DOCKER_GUIDE.md)**.
*   For details on the layout grid and supported card JSON payloads, read: **[FRONTEND_GUIDE.md](FRONTEND_GUIDE.md)**.
*   For the kiosk display configuration on the observatory screen (Pi 3B+), read: **[Kiosk Solution.md](../Kiosk%20Solution.md)**.
