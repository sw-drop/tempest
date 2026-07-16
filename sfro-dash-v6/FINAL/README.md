# SFRO Dashboard V5 - Clean Project Release

This directory contains **every single element** required to continue development, deployment, maintenance, and diagnostics of the Starfront Observatory V5 Dashboard project.

---

## Folder Directory Structure

### 1. `/container`
This folder is the **direct root of the Docker runtime container**. It contains exactly what needs to be deployed to recreate the production multi-container environment on a new Docker server:
*   `docker-compose.yml` - Multi-container setup (Nginx serving client assets on port `8025` and Python scheduler container running the daemon).
*   `Dockerfile` - Build specification for the scheduler daemon environment.
*   `requirements.txt` - Python package dependencies.
*   `.env.example` - Example file containing empty environment variables (like `DISCORD_TOKEN`).
*   `index.html` & `index.js` - Pristine dashboard frontend with built-in responsive styling, SVG weather icons, and title restoration properties.
*   `data/` & `images/` - Empty volume mounts for dashboard FITS captures and compiled card JSON configurations.
*   `dash-scripts/` - Python engine source scripts including the FSM `schema_engine.py` scheduler, mapping routes router (`controller.py`), and metric collectors.

### 2. `/agent`
Contains the **customization settings and instruction guides for the remote Hermes/Kanini Agent**:
*   `.agents/skills/sfro-dash-control/SKILL.md` - Cleaned skill prompts warning Hermes against using fake image placeholders and defining text overrides.

### 3. `/deployment-scripts`
Standalone script utilities to deploy the codebase or targeted hotfixes:
*   `deploy_v5.py` - Master deployment orchestration pipeline (uses local-to-host `rsync` to mirror changes and start Docker compositions).
*   `deploy_fixes.sh` - Lightweight targeted deployment script for single-file syncs to the server.

### 4. `/diagnostic-tools`
A collection of Python scripts developed during testing to isolate and diagnose API issues locally:
*   `test_yr_api.py` - Tests standard YR.no weather API endpoints and extracts raw forecast payloads.
*   `test_sunrise_sunset.py` - Verifies solar position algorithms for daytime schemas.
*   `test_forecast_waits.py` - Checks weather thresholds for telescope operating windows.
*   `test_station_api.py` - Validates communication with the physical Tempest weather station.

### 5. `/documentation`
System manuals, FSM state mapping charts, and operational architectures:
*   `MAINTENANCE.md` - Troubleshooting guide for scheduler loops, Met.no blocks, and image conversions.
*   `DOCKER_GUIDE.md` - Local and production build details, volumes, permissions alignment, and schema engine loops.
*   `FRONTEND_GUIDE.md` - In-depth manual covering HTML classes, JS grid mappings, and `renderCard` components.
*   `README.md` - The original root readme overviewing features and installation commands.

---

## Recreating the Dashboard on a New Server

To replicate this environment on any clean Docker-enabled server:

1. Copy the contents of the `/container` folder to your target path on the host system (e.g. `/docker/sfro-dash-v5`).
2. Create a `.env` file containing the valid `DISCORD_TOKEN` in the folder root.
3. Make sure permissions for `data/` and `images/` are aligned so the scheduler container can write to them:
   ```bash
   sudo chown -R 1000:1000 data images
   ```
4. Build and boot up the composition:
   ```bash
   docker compose up --build -d
   ```
