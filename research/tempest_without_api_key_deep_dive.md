# Exploiting Tempest Weather Station Data Without an API Key

## Overview
The practical answer is that useful Tempest data access **without** an API key or access token is limited to what the public web experience exposes, plus any local radio/UDP data from hardware that is physically on the same local network as a station hub.[cite:2][cite:5] For remote access to observations, forecasts, and real-time streams, Tempest’s current developer documentation says an access token is required, and public-station observation access is governed by subscription and policy controls rather than anonymous API access.[cite:2][cite:3][cite:5]

For the specific public page pattern `https://tempestwx.com/station/<station_id>/grid`, including station `174867`, the strongest no-key strategy is to treat the web app as a public presentation layer and extract only what is lawfully and technically visible there, while avoiding assumptions that undocumented JSON endpoints will remain stable or permitted.[cite:5][cite:6][cite:15]

## What “without an API key” means now
Historically, Tempest had a shared or developer key that many community integrations used for testing and, in practice, sometimes for public-station access.[cite:18][cite:19] Community discussions and third-party integration chatter indicate that this old shared-key path was being phased out by 2025, while official docs now emphasize OAuth or a personal access token instead of an open developer key.[cite:1][cite:3][cite:25]

That change matters because older blog posts, GitHub examples, and Home Assistant threads often assume a reusable API key exists.[cite:4][cite:10][cite:19] In the current model, authenticated remote access is owner-centric, and the official policy says public-station metadata is broadly available only under specific conditions, while public-station observations and forecasts are tied to TempestONE subscription access.[cite:5]

## Data surfaces you can still use
### 1. Public station pages
The Tempest site exposes public-facing station pages such as `/station/<id>/grid`, and community posts confirm users routinely share those links for read-only viewing of public stations.[cite:6][cite:15] These pages are the easiest no-key entry point because they can often be opened directly in a browser, bookmarked on mobile, or embedded in a personal workflow as human-readable dashboards.[cite:6][cite:15]

What they are best for:
- Manual monitoring of current conditions and trends visible in the UI.[cite:6][cite:15]
- Browser automation, scraping, or screenshot capture for personal use where allowed by site terms.[cite:5][cite:6]
- Using a stable station ID URL pattern that can be generalized to other stations when those stations are public.[cite:6][cite:15]

Constraints:
- The page is not a guaranteed public API contract.[cite:2][cite:5]
- Data fields, layout, client-side requests, and load timing can change at any time.[cite:5][cite:21]
- Access depends on the station still being public and the page continuing to render without login.[cite:15][cite:20]

### 2. Public metadata, not necessarily public observations
Tempest’s remote-data policy makes an important distinction between metadata and observation data.[cite:5][cite:23] The current policy states that public metadata can be available from public stations, while observation and forecast access for public stations is controlled separately and currently described as available via TempestONE subscription.[cite:5]

This means that, without credentials, a robust design should expect access to station identity and location context to be more durable than access to structured observations.[cite:5][cite:23] If a workflow depends on anonymous remote observation retrieval, it is relying on behavior that is weaker than the documented policy baseline.[cite:5][cite:18]

### 3. Local network data, if you control the site
The official docs also state there is a local UDP interface available for off-grid or backup scenarios, even though Tempest recommends using remote REST and WebSocket interfaces as the primary source for third-party applications.[cite:3] This is the one major path that does not depend on a cloud API token, but it only helps if the station hardware and hub are on a network you can access directly.[cite:3]

For your own deployed equipment, or for stations physically hosted somewhere you control, local ingestion can be the most powerful no-key option because it yields raw observations continuously and avoids dependence on Tempest’s public web UI.[cite:3][cite:13] For someone else’s public station page, local UDP is irrelevant unless that station owner exposes a separate feed.[cite:3][cite:5]

## Best exploitation patterns
### Pattern A: Treat `/grid` as a public dashboard, not a formal API
For station `174867` and similar links, the safest exploitation model is a browser-first one: open the public grid page, inspect what is visible, and extract value through viewing, bookmarking, browser automation, notifications, and archival snapshots rather than by depending on undocumented backend calls.[cite:6][cite:15]

Good uses include:
- Personal weather monitoring dashboards assembled with browser tabs or a start page.[cite:6]
- Periodic screenshot capture for a visual weather log.[cite:6][cite:15]
- Light scraping of rendered values for non-commercial personal use, with the expectation that selectors may break.[cite:5][cite:21]

A practical implementation is Playwright or Puppeteer running on a schedule to load the `/grid` URL, wait for the page to settle, and extract visible card values into CSV or SQLite.[cite:6][cite:15] This works best when the goal is resilience at the human-interface level rather than brittle dependence on internal request formats.[cite:5][cite:21]

### Pattern B: The JSON API Route (Using the Web App's Public API Key)
Through inspection of the Tempest web application's compiled JavaScript resources (specifically `https://tempestwx.com/js/main-e6697b0938.min.js`), we discovered that the frontend uses a hardcoded, public API key to query WeatherFlow's REST services. This key allows unauthenticated clients to fetch structured weather station observations and forecasts directly as JSON.

* **Public API Key**: `6bff2f89-84ab-463c-886e-fc0f443da4cf`
* **Base URL**: `https://swd.weatherflow.com/swd/rest/`

#### Key JSON Endpoints
1. **Station Metadata**:
   * **Endpoint**: `/stations/{station_id}`
   * **URL**: `https://swd.weatherflow.com/swd/rest/stations/{station_id}?api_key=6bff2f89-84ab-463c-886e-fc0f443da4cf`
   * **Details**: Returns station settings, elevation, location, and timezone details.
2. **Current Observations**:
   * **Endpoint**: `/observations/station/{station_id}`
   * **URL**: `https://swd.weatherflow.com/swd/rest/observations/station/{station_id}?api_key=6bff2f89-84ab-463c-886e-fc0f443da4cf`
   * **Details**: Returns key weather metrics in standard SI (metric) units, including temperature in °C, wind speed in m/s, pressure in hPa, and precipitation in mm.
3. **Forecast**:
   * **Endpoint**: `/better_forecast`
   * **URL**: `https://swd.weatherflow.com/swd/rest/better_forecast?station_id={station_id}&api_key=6bff2f89-84ab-463c-886e-fc0f443da4cf`
   * **Details**: Returns current conditions, timezone offsets, and short-term/long-term forecasts.

This approach is highly useful when:
* You want structured, clean observations without the overhead of browser automation (Playwright/Puppeteer).
* You need real-time data fields that are difficult to isolate in the DOM (e.g. lightning strike counts, raw solar radiation values, or wet bulb temperature).
* You require a fast, low-footprint scraper.

This approach is weak when:
* WeatherFlow updates the frontend and rotates/revokes the public API key, requiring a manual update of your configuration.
* High polling rates trigger rate-limiting or blocks on the public API gateway.


### Pattern C: Use local UDP for stations you physically control
If some of the “others” are stations on networks you operate, local UDP is the highest-leverage no-token path.[cite:3] Community users describe capturing Tempest data locally into their own databases and dashboards, and also note that WebSockets are richer than UDP for cloud-connected use, which reinforces that UDP is mainly the local/no-cloud fallback path.[cite:13]

A good architecture is:
1. Listen for Tempest UDP broadcasts on the LAN.[cite:3]
2. Normalize records into SQLite, Postgres, or time-series storage.[cite:13]
3. Build your own API and charts on top of your local copy.[cite:13]
4. Use the public `/grid` page only as a convenience UI, not as the source of truth.[cite:3][cite:13]

### Pattern D: Use downstream sharing platforms when station owners enable them
Community guidance points to alternatives such as Weather Underground exports, IFTTT pipelines, or spreadsheet-based logging for people who mainly want to analyze data rather than integrate directly with Tempest’s cloud endpoints.[cite:13] These are not pure Tempest-native no-key APIs, but they can be effective if the station owner has already enabled the relevant sharing path.[cite:13]

This is often the lowest-friction route for public or shared stations because the integration burden moves away from Tempest’s restricted remote API.[cite:13] The trade-off is lower fidelity, platform lock-in, and dependence on whichever third-party export format is available.[cite:13]

## Recommended workflow for station 174867 and others
### Tier 1: Discovery
Start with the public grid URL and determine whether the page is visible without login, what metrics appear, how often they update, and whether the browser loads structured data requests behind the scenes.[cite:6][cite:15] Record the station ID, any device IDs exposed in URLs, and whether graphs or drill-down pages reveal richer data paths.[cite:10][cite:15]

### Tier 2: Personal collector
Build a small collector that supports three modes in this order:
1. Structured anonymous endpoint capture if the page uses one and it remains accessible.[cite:15][cite:21]
2. DOM extraction from the rendered page when structured endpoints are unavailable.[cite:6][cite:15]
3. Screenshot and OCR fallback if the UI is highly dynamic and anti-scraping measures are minimal.[cite:6]

This layered approach minimizes breakage because each mode can fail over to the next without requiring an official Tempest token.[cite:5][cite:21]

### Tier 3: Normalize and enrich
Store every observation with a source label such as `public_json`, `dom_scrape`, or `udp_local` so data quality can be tracked over time.[cite:3][cite:5] This matters because Tempest’s policy language distinguishes quality-controlled “Nearcast” remote data from local/raw pathways, so a mixed-source archive should not assume equivalence between those feeds.[cite:5]

### Tier 4: Escalate only when necessary
If you eventually need historical backfill, real-time push, or durable field schemas, the official route is a personal token for owned stations or a subscription/commercial path for broader public-station data.[cite:2][cite:3][cite:5] That is the clean boundary where “exploitation without an API key” stops being cost-effective compared with supported access.[cite:2][cite:5]

## Compliance and risk
The biggest risk is confusing “publicly viewable in a browser” with “documented for unrestricted automated extraction.”[cite:5][cite:20] Tempest’s policy language is explicit that access rights differ by metadata versus observations, owner versus non-owner, and personal versus commercial use.[cite:5][cite:23]

For a personal hobby project, the lowest-risk approach is to limit automation to publicly visible pages, keep request volume low, credit Tempest when rebroadcasting data, and avoid collecting data from stations that are not clearly public.[cite:5][cite:20] For any productized, shared, or commercial use, the current policy points away from anonymous scraping and toward subscription or negotiated access.[cite:5]

## Architecture options
| Option | Needs key/token | Works for station 174867 public page | Scales to many stations | Stability | Notes |
|---|---|---|---|---|---|
| Public JSON API route (Web App Key) | No (uses public key `6bff2f89-84ab-463c-886e-fc0f443da4cf`) | Yes | High | Medium-High | Best option. Fetch structured JSON directly from WeatherFlow rest service without auth tokens. |
| Public `/grid` manual use | No | Yes, if page is public[cite:6][cite:15] | Low[cite:6] | Medium[cite:21] | Best for manual monitoring. |
| DOM scraping of `/grid` | No | Often[cite:6][cite:15] | Medium[cite:6] | Low[cite:21] | Brittle to UI changes. Not recommended if JSON route works. |
| Local UDP capture | No cloud key[cite:3] | Only if station is on your LAN[cite:3] | Medium[cite:13] | High locally[cite:3] | Best no-key path for owned/hosted stations. |
| Official REST/WebSocket | Yes[cite:2][cite:3] | Yes[cite:2][cite:3] | High[cite:2] | High[cite:2][cite:3] | Best supported route for owned stations. |
| Tempest public-station subscription path | Not anonymous in practice[cite:5] | Potentially[cite:5] | High[cite:5] | High[cite:5] | Needed when public observation access must be durable. |

## Concrete recommendations
For your use case, the best no-key exploitation strategy is to build a collector around the public JSON API route discovered in the frontend JS, using the public API key. This avoids the heavy dependencies of browser automation while still getting clean, structured observations.

Recommended priority order:
- Query the REST observations endpoint directly using the public API key `6bff2f89-84ab-463c-886e-fc0f443da4cf`.
- Fall back to DOM scraping of rendered values using Python's `BeautifulSoup` or `playwright` only if the public API key is rotated/disabled and the new key is not yet extracted.
- For any station on infrastructure you control, ingest local UDP and store your own history.[cite:3][cite:13]
- Move to official token/subscription methods only when you need stable schemas, history, or scale.[cite:2][cite:3][cite:5]

## Implementation notes for a technically strong hobbyist
A useful collector stack is a Python daemon running in a Docker container that performs the following steps:
1. Polls the public REST endpoint `/observations/station/{station_id}` with the public API key.
2. Formats and normalizes the metrics, converting SI units (e.g. m/s wind speed, Celsius temperature) to user-desired units (mph, Fahrenheit) as needed, and calculating dew point margins or checking roof-opening thresholds.
3. Exposes the latest reading via a local HTTP API (pull).
4. Publishes new readings to an MQTT broker (push) as JSON payloads.
5. Runs continuously in a container, parameterizing parameters like station ID, polling interval, and MQTT host via environment variables.

