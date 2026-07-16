# SFRO Nightly Dashboard - Maintenance Guide

## Overview
This application is a dockerized Python pipeline that periodically fetches data, generates forecasts, and renders an HTML dashboard. It consists of two containers orchestrated by `docker-compose.yml`:
1. **`sfro-log` (updater)**: Runs the Python scripts, fetching data and generating the static HTML.
2. **`SFRO-Nightly` (web)**: An Nginx web server that serves the generated HTML on port 5002.

## Configuration (.env File)
The application relies on environment variables for sensitive data and dynamic configuration. You must create a `.env` file in the same directory as `docker-compose.yml` (or define these variables in your Portainer stack) with the following structure:

```env
# REQUIRED
DISCORD_TOKEN="your_discord_bot_token_here"
SCOPES="FRA400:1247656689689890906,75Q:1247656711584420002"

# OPTIONAL (Defaults shown)
START_DATE="2025-12-10"
LAT="31.546944"
LON="-99.382222"
ALTITUDE="466"
TIMEZONE="America/Chicago"

# Dynamic API Endpoints (Prefix 'API_' + Scope Name)
API_75Q="http://100.100.218.98:8188/ts/v0/profiles/9f4f477e-c148-4672-a0dc-26411abb444b/preview"
API_FRA400="http://100.123.140.100:8188/ts/v0/profiles/ef60f4b0-5072-47e0-a2db-83ed16edf290/preview"
```

## Pipeline Architecture
The `update_dashboard.py` script runs on startup and then at 15 minutes past every hour. It executes the following stages sequentially in isolated `try/except` blocks:

1. **Discord Extractor** (`discord_extractor.py`): Connects to the Discord API using the `DISCORD_TOKEN`. It maps the `SCOPES` dictionary to fetch messages dynamically from each specified channel, and writes intermediate data to the `data/` directory.
2. **Forecast Generator** (`forecast_generator.py`): Iterates over the `SCOPES` list. Fetches weather forecasts and calculates celestial coordinates based on the configured coordinates.
3. **HTML Visualizer** (`html_visualizer.py`): Scans the local `data/` directory and dynamically renders timeline tracks for any found telescope scopes, maintaining original layout hierarchy.

Because the stages are isolated, if the Discord API rate limits the bot, the HTML visualizer will still run using the last known good data.

## Access Control
The `docker-compose.yml` file is configured with the label:
`io.portainer.accesscontrol.users=agent`
This ensures the containers are always visible to the `agent` user in Portainer. **Do not remove this label.**

## Troubleshooting

### Container fails to start or exits immediately
Check the logs of the `sfro-log` container:
```bash
docker logs sfro-log
```
If you see `ValueError: DISCORD_TOKEN environment variable not set.`, ensure your `.env` file is present and correctly formatted.

### Data is not updating on the dashboard
1. Ensure both containers are running.
2. Check the logs of the `sfro-log` container for specific stage errors.
   - If `discord_extractor` is failing, check if your `DISCORD_TOKEN` is still valid and that you aren't being permanently rate-limited.
   - If `forecast_generator` is failing, verify the API endpoints (`API_75Q`, `API_FRA400`) are reachable from within the container's network (`cloudflare-net`).

### UI modifications
If you wish to change the look of the dashboard, modify `html_visualizer.py`. The Nginx container simply serves the `index.html` file that this script outputs to the root directory.
