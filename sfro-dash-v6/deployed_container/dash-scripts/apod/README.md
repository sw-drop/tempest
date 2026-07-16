# NASA APOD Fetcher

This utility script connects to NASA's Astronomy Picture of the Day (APOD) API, downloads the daily astronomical image (or an image from a specific date), scales and center-crops it to exactly `1920x1280` pixels (a standard crop-sensor 3:2 aspect ratio), and saves it as a JPEG file. It can also save the accompanying explanation text.

By default, the target date of the APOD (formatted as `_YYYY-MM-DD`) is automatically appended to the output filenames.

## Features
- Fetches metadata from NASA's official APOD API.
- Supports NASA's `DEMO_KEY` out-of-the-box, or respects the custom `NASA_API_KEY` environment variable.
- Center-crops and resizes the image to exactly `1920x1280` pixels (using `LANCZOS` interpolation).
- Saves the APOD text explanation to a matching `.txt` file when using the `-t` / `--save-text` flag.
- Appends the target date to the filenames (e.g. `apod_2025-07-14.jpg` and `apod_2025-07-14.txt`).
- Supports fetching images/text for a specific date using the `--date` command line argument.
- Configurable output path via the `--output` argument.

---

## Installation & Requirements

The script is written in Python 3 and requires the following libraries (which are installed via the container's `requirements.txt`):
*   `requests`
*   `Pillow` (PIL)

---

## Usage

### Running inside the Container (Recommended)

To run the script inside the running scheduler container:

```bash
# Fetch today's APOD image (saves to /app/images/apod_YYYY-MM-DD.jpg by default)
docker exec sfro-dash-v5-scheduler python3 dash-scripts/apod/fetch_apod.py

# Fetch today's image AND explanation text (saves to /app/images/apod_YYYY-MM-DD.jpg and /app/images/apod_YYYY-MM-DD.txt)
docker exec sfro-dash-v5-scheduler python3 dash-scripts/apod/fetch_apod.py -t

# Fetch APOD image & text for a specific date (e.g. 2025-07-14, saves to apod_2025-07-14.jpg and apod_2025-07-14.txt)
docker exec sfro-dash-v5-scheduler python3 dash-scripts/apod/fetch_apod.py --date 2025-07-14 -t

# Save the image & text to a custom output path (e.g. /app/images/nasa_today_2025-07-14.jpg and /app/images/nasa_today_2025-07-14.txt)
docker exec sfro-dash-v5-scheduler python3 dash-scripts/apod/fetch_apod.py --output /app/images/nasa_today.jpg -t
```

### Running Locally (Mac / Dev Machine)

You can run the script locally from the `sfro-dash-v5/` directory:

```bash
# Set up output folder locally
mkdir -p images

# Fetch today's image & text
python3 docker_deploy/dash-scripts/apod/fetch_apod.py -o ./images/apod.jpg -t

# Fetch image & text from a specific date
python3 docker_deploy/dash-scripts/apod/fetch_apod.py --date 2025-07-14 -o ./images/apod.jpg -t
```

---

## Arguments

*   `-d`, `--date`: The date of the APOD to fetch in `YYYY-MM-DD` format (e.g., `2025-07-14`). If omitted, the script fetches today's APOD.
*   `-o`, `--output`: Absolute or relative path where the final cropped image should be saved. The target date (from NASA metadata) is automatically appended to the filename. Defaults to `/app/images/apod.jpg` (resolves to `/app/images/apod_YYYY-MM-DD.jpg`) when running in the container.
*   `-t`, `--save-text`: Also save the text description to a matching `.txt` file (with the same base name, date suffix, and path as the image).

---

## Environment Variables

*   `NASA_API_KEY`: You can optionally set this environment variable in the `.env` file (or docker host environment) to override NASA's default rate-limited `DEMO_KEY`.
