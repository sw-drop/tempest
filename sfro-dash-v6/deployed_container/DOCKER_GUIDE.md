# Docker Dev & Production Environment Guide

This guide details how to build and run the SFRO Dashboard V5 using Docker, matching the production environment running on the target server `Pi5-1`.

---

## Architecture Overview

We use a two-container Docker Compose setup:
1.  **`web` (`sfro-dash-v5-web`)**: An ultra-lightweight Nginx container that hosts the static frontend (`index.html`, `index.js`) and serves the compiled JSON and JPEG files from the `./app_data` folder (mounted internally as `/data`).
2.  **`scheduler` (`sfro-dash-v5-scheduler`)**: A Python 3.11 container running our master daemon loop (**`dash-scripts/daemon.py`**). It orchestrates:
    *   FITS watchdog (`image_watcher.py`) every 15 seconds.
    *   Active card controller (`controller.py`) every 15 seconds.
    *   Tempest weather observer (`update_weather.py`) every 1 minute.
    *   Roof status scraper (`fetch_roof.py`) every 1 minute.
    *   Schema engine state evaluation (`schema_engine.py`) every 15 minutes.
    *   Weather forecast compiler (`fetch_forecast.py`) every 2 hours.
    *   APOD astronomy picture fetcher (`fetch_apod.py`) every 12 hours.

---

## 1. Quick Start

### Step 1: Set Credentials
Make sure you have your Discord Bot token set in a `.env` file in the project root:
```env
DISCORD_TOKEN=your_token_here
```

### Step 2: Build and Launch
From the project root directory, run:
```bash
docker compose up --build -d
```
Once running, the dashboard is served locally at:
**`http://localhost:8025/index.html`**

---

## 2. Permissions Alignment (User 1000 / Pi)

To ensure that the scheduler container writes files that are immediately writable by the host user `pi` (and the Hermes agent), the scheduler service is configured with:
```yaml
user: "1000:1000"
```
This guarantees that all output files in `/docker/sfro-dash-v5/app_data/` and `/docker/sfro-dash-v5/data/` are created with `pi:pi` ownership, eliminating permission errors.

---

## 3. Dynamic Schema Control & Overrides

The scheduler's state evaluation is fully automated by the Python FSM engine (`schema_engine.py`) which evaluates Met.no forecast models and physical roof state to automatically route cards.

*   **Manual Schema Override**:
    To force a specific dashboard schema (e.g. `Supper1`), write the override JSON to your host data folder:
    ```bash
    echo '{"override": "Supper1"}' > /docker/sfro-dash-v5/data/override.json
    ```
*   **Removing Schema Override**:
    Simply delete the override file to restore automated state machine behavior:
    ```bash
    rm /docker/sfro-dash-v5/data/override.json
    ```
*   **Single Card Overrides (Custom Cards)**:
    Agents (like Hermes) can display custom text/markdown warnings or images on individual cards by writing a JSON payload to `custom_<cardname>.json` (e.g. `custom_roof.json` or `custom_skycam.json`). The controller will prioritize these overriding payloads instantly. Delete the file to return to standard rotation.

---

## 4. Logs & Debugging

To view the scheduler logs and compile activities in real-time:
```bash
docker logs -f sfro-dash-v5-scheduler
```

To force an immediate update of all dashboard cards (bypassing the scheduler wait intervals), simply restart the scheduler service, which runs all scripts immediately on boot:
```bash
docker restart sfro-dash-v5-scheduler
```
