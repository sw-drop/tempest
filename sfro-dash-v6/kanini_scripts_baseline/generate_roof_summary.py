#!/usr/bin/env python3
# Description: Generates a natural language roof opening forecast using OpenRouter and yr.no data.
# Integrates NINA advanced sequencer API to detect scope wait states.

import os
import sys
import json
import urllib.request
from datetime import datetime, timedelta

def fetch_weather():
    # Starfront Texas Coordinates
    lat = "31.546944"
    lon = "-99.382222"
    url = f"https://api.met.no/weatherapi/locationforecast/2.0/compact?lat={lat}&lon={lon}"
    headers = {"User-Agent": "Hermes-Agent/1.0 (test@pillay.uk)"}
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            return json.loads(response.read().decode())
    except Exception as e:
        print(f"Failed to fetch yr.no data: {e}")
        return None

def fetch_nina_wait_states():
    # Scopes: FRA400 and 75Q
    apis = [
        "http://100.123.140.100:8188/ts/v0/profiles/ef60f4b0-5072-47e0-a2db-83ed16edf290/preview", # FRA400
        "http://100.100.218.98:8188/ts/v0/profiles/9f4f477e-c148-4672-a0dc-26411abb444b/preview"  # 75Q
    ]
    
    for api_url in apis:
        try:
            req = urllib.request.Request(api_url)
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode())
                # Check if any block has WaitPeriod = True
                for block in data:
                    if block.get("WaitPeriod") == True:
                        return True
        except Exception as e:
            print(f"Failed to fetch NINA schedule from {api_url}: {e}")
            
    return False

def generate_summary(weather_data, has_wait_states, api_key):
    # Extract the next 15 hours of cloud data
    timeseries = weather_data.get("properties", {}).get("timeseries", [])
    forecast_text = "Forecast for the next 15 hours:\n"
    
    for entry in timeseries[:15]:
        time_str = entry["time"]
        dt = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
        clouds = entry["data"]["instant"]["details"].get("cloud_area_fraction", "unknown")
        precip = 0.0
        if "next_1_hours" in entry["data"]:
            precip = entry["data"]["next_1_hours"]["details"].get("precipitation_amount", 0.0)
            
        forecast_text += f"- {dt.strftime('%H:%M UTC')}: Clouds {clouds}%, Precip {precip}mm\n"
        
    wait_state_context = ""
    if has_wait_states:
        wait_state_context = "CRITICAL ALERT: At least one telescope has a WAIT STATE forecast for the coming night! You MUST explicitly alert the user about this in your summary, regardless of the roof opening forecast."
    else:
        wait_state_context = "No telescope wait states are scheduled. No need to mention wait states."
        
    prompt = (
        "You are the Starfront Observatory weather forecaster. "
        "Analyze the following hourly forecast data for Starfront (Texas). "
        "The observatory roof can ONLY open if there is a consecutive window of at least 2 hours where cloud cover is strictly LESS than 20% and precipitation is 0mm. "
        f"{wait_state_context}\n"
        "Write a 2-3 sentence summary intended for the dashboard. "
        "Focus on the likelihood of clear sky conditions and the prospect of the roof opening based on the rules. "
        "Do NOT use markdown, just plain text. Keep it extremely concise.\n\n"
        f"{forecast_text}"
    )

    req_data = json.dumps({
        "model": "openrouter/free",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2
    }).encode("utf-8")
    
    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=req_data,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    )
    
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            result = json.loads(response.read().decode())
            return result["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"Failed to generate summary with OpenRouter: {e}")
        return None

def main():
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        env_path = "/opt/data/.env"
        if os.path.exists(env_path):
            with open(env_path, "r") as f:
                for line in f:
                    if line.strip().startswith("OPENROUTER_API_KEY="):
                        api_key = line.split("=", 1)[1].strip().strip('"').strip("'")
                        break

    if not api_key:
        print("Warning: OPENROUTER_API_KEY is not defined. Exiting gracefully for test run.")
        sys.exit(0)

    weather_data = fetch_weather()
    if not weather_data:
        sys.exit(1)
        
    has_wait_states = fetch_nina_wait_states()

    summary = generate_summary(weather_data, has_wait_states, api_key)
    if not summary:
        sys.exit(1)

    # OUTPUT TARGET: 
    # Because Hermes has a volume mount to the dashboard directory, we write directly to the reports folder.
    output_path = "/opt/data/v5-dash/data/reports/roof_forecast_summary.txt"
    try:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(summary + "\n")
        print(f"Successfully generated and wrote roof summary to {output_path}")
    except Exception as e:
        print(f"Failed to write to {output_path}: {e}")

if __name__ == "__main__":
    main()
