import threading
import urllib.request
import json
import time
import logging
from datetime import datetime
from calendar import timegm

logger = logging.getLogger("tempest_collector")

class WeatherState:
    def __init__(self):
        self.lock = threading.Lock()
        self.data = None
        self.last_update = 0
        self.last_request_time = 0  # Tracks when a client last polled the API

    def update(self, data):
        with self.lock:
            self.data = data
            self.last_update = time.time()

    def get_data(self):
        with self.lock:
            return self.data, self.last_update

    def record_request(self):
        with self.lock:
            self.last_request_time = time.time()

    def get_last_request_time(self):
        with self.lock:
            return self.last_request_time

# Global weather state and trigger event
weather_state = WeatherState()
fetch_now_event = threading.Event()

class TempestCollector:
    def __init__(self, config, on_update_callbacks=None):
        self.config = config
        self.on_update_callbacks = on_update_callbacks or []
        self.running = False
        self.thread = None

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._loop, name="CollectorThread", daemon=True)
        self.thread.start()
        logger.info("Tempest Collector thread started in client-demand mode.")

    def stop(self):
        self.running = False
        fetch_now_event.set()  # Wake up thread to exit
        if self.thread:
            self.thread.join(timeout=5)
            logger.info("Tempest Collector thread stopped.")

    def _loop(self):
        obs_url = f"https://swd.weatherflow.com/swd/rest/observations/station/{self.config.TEMPEST_STATION_ID}?api_key={self.config.TEMPEST_API_KEY}"
        forecast_url = f"https://swd.weatherflow.com/swd/rest/better_forecast?station_id={self.config.TEMPEST_STATION_ID}&api_key={self.config.TEMPEST_API_KEY}"
        
        while self.running:
            current_time = time.time()
            last_req = weather_state.get_last_request_time()
            
            # Active if a client requested data in the last 120 seconds
            is_client_active = (current_time - last_req) < 120
            is_data_stale = (current_time - weather_state.last_update) >= self.config.POLL_INTERVAL_SECONDS
            
            if is_client_active and (is_data_stale or weather_state.data is None):
                logger.info("Active dashboard client detected. Fetching data...")
                try:
                    # 1. Fetch current observations from Tempest
                    req_obs = urllib.request.Request(obs_url, headers={"User-Agent": "Mozilla/5.0 (Tempest-Script-Host)"})
                    with urllib.request.urlopen(req_obs, timeout=10) as resp:
                        obs_raw = json.loads(resp.read().decode('utf-8'))
                    
                    # 2. Fetch forecast from Tempest to get sunrise/sunset
                    req_fore = urllib.request.Request(forecast_url, headers={"User-Agent": "Mozilla/5.0 (Tempest-Script-Host)"})
                    with urllib.request.urlopen(req_fore, timeout=10) as resp:
                        fore_raw = json.loads(resp.read().decode('utf-8'))
                    
                    # 3. Fetch MET Norway (yr.no) forecast using coordinates
                    met_raw = None
                    latitude = obs_raw.get("latitude")
                    longitude = obs_raw.get("longitude")
                    
                    if latitude is not None and longitude is not None:
                        # MET Norway API format (needs coordinates)
                        # We must supply a unique User-Agent to avoid blocks as per ToS
                        met_url = f"https://api.met.no/weatherapi/locationforecast/2.0/compact?lat={latitude:.4f}&lon={longitude:.4f}"
                        logger.info(f"Polling MET Norway from: {met_url}")
                        req_met = urllib.request.Request(
                            met_url, 
                            headers={
                                "User-Agent": "TempestScriptHost/1.0 gary@pillay.net"
                            }
                        )
                        try:
                            with urllib.request.urlopen(req_met, timeout=10) as resp:
                                met_raw = json.loads(resp.read().decode('utf-8'))
                        except Exception as met_err:
                            logger.error(f"Error fetching MET Norway cloud forecast: {met_err}")

                    # 4. Fetch Starfront Building 5 Roof Status
                    physical_roof_status = "Unknown"
                    try:
                        req_roof = urllib.request.Request(
                            "https://alpaca-api.tx.starfront.space/api/v1/roof/state",
                            headers={"User-Agent": "TempestScriptHost/1.0 gary@pillay.net"}
                        )
                        with urllib.request.urlopen(req_roof, timeout=10) as resp:
                            roof_state_raw = json.loads(resp.read().decode('utf-8'))
                            # Find Building 5
                            building_5 = next((b for b in roof_state_raw if b.get("device_number") == 5), None)
                            if building_5:
                                is_open = building_5.get("is_open")
                                if is_open is True:
                                    physical_roof_status = "Open"
                                elif is_open is False:
                                    physical_roof_status = "Closed"
                    except Exception as roof_err:
                        logger.error(f"Error fetching Starfront building roof state: {roof_err}")

                    if obs_raw.get("status", {}).get("status_code") == 0 and fore_raw.get("status", {}).get("status_code") == 0:
                        processed_data = self._process(obs_raw, fore_raw, met_raw, physical_roof_status)
                        weather_state.update(processed_data)
                        logger.info("Observations, forecast, MET Norway data, and roof state successfully updated.")
                        
                        # Trigger callbacks (e.g. MQTT publish)
                        for cb in self.on_update_callbacks:
                            try:
                                cb(processed_data)
                            except Exception as cb_err:
                                logger.error(f"Error in update callback: {cb_err}", exc_info=True)
                    else:
                        logger.error(f"API Error. Obs: {obs_raw.get('status')}, Forecast: {fore_raw.get('status')}")
                except Exception as e:
                    logger.error(f"Error fetching from Tempest API: {e}", exc_info=True)
            else:
                if not is_client_active and weather_state.data is not None:
                    logger.debug("Collector idle (no active clients). Skipping API pull.")
            
            # Sleep in short increments to remain highly responsive to API requests
            fetch_now_event.wait(timeout=2)
            fetch_now_event.clear()

    def _process(self, obs_raw, fore_raw, met_raw, physical_roof_status="Unknown"):
        obs_list = obs_raw.get("obs", [])
        if not obs_list:
            logger.warning("Observation array is empty.")
            return {"raw": obs_raw, "processed": {}, "roof_status": {"allowed": False, "reason": "No observations"}}

        obs = obs_list[0]
        current_time = time.time()
        
        # 1. Extract values in standard SI units
        temp_c = obs.get("air_temperature")
        dew_point_c = obs.get("dew_point")
        humidity = obs.get("relative_humidity")
        wind_avg_mps = obs.get("wind_avg")
        wind_gust_mps = obs.get("wind_gust")
        pressure_hpa = obs.get("barometric_pressure")
        solar_rad = obs.get("solar_radiation")
        uv = obs.get("uv")
        brightness = obs.get("brightness")
        precip_mm = obs.get("precip")
        lightning_count_1h = obs.get("lightning_strike_count_last_1hr")
        wind_dir = obs.get("wind_direction")

        # Extract sunrise and sunset from daily forecast
        daily_forecast = fore_raw.get("forecast", {}).get("daily", [])
        sunrise = 0
        sunset = 0
        sunrise_tomorrow = 0
        if daily_forecast:
            sunrise = daily_forecast[0].get("sunrise", 0)
            sunset = daily_forecast[0].get("sunset", 0)
        if len(daily_forecast) > 1:
            sunrise_tomorrow = daily_forecast[1].get("sunrise", 0)
        else:
            sunrise_tomorrow = sunrise + 86400 if sunrise > 0 else 0

        # Calculate day/night status (Daytime = 1 hour after sunrise to 1 hour before sunset)
        is_daytime = False
        if sunrise > 0 and sunset > 0:
            is_daytime = (sunrise + 3600) <= current_time <= (sunset - 3600)

        # 2. Extract MET Norway Cloud cover and hourly forecast
        current_cloud = None
        night_forecast = []
        
        if met_raw:
            timeseries = met_raw.get("properties", {}).get("timeseries", [])
            if timeseries:
                # First element represents current hour observations
                current_cloud = timeseries[0].get("data", {}).get("instant", {}).get("details", {}).get("cloud_area_fraction")
                
                # Filter for night forecast timeline
                # If early morning before today's sunrise + 1h: rest of last night
                # If daytime: coming night, from today's sunset - 1h to tomorrow's sunrise + 1h
                # If nighttime: current night, from today's sunset - 1h to tomorrow's sunrise + 1h
                if sunrise > 0 and sunset > 0:
                    if current_time < (sunrise + 3600):
                        filter_start = current_time
                        filter_end = sunrise + 3600
                    elif current_time < (sunset - 3600):
                        filter_start = sunset - 3600
                        filter_end = sunrise_tomorrow + 3600
                    else:
                        filter_start = sunset - 3600
                        filter_end = sunrise_tomorrow + 3600
                else:
                    filter_start = current_time
                    filter_end = current_time + 43200

                for entry in timeseries:
                    time_str = entry.get("time")
                    try:
                        dt = datetime.strptime(time_str, "%Y-%m-%dT%H:%M:%SZ")
                        ts = timegm(dt.utctimetuple())
                    except Exception:
                        continue
                    
                    if filter_start <= ts <= filter_end:
                        details = entry.get("data", {}).get("instant", {}).get("details", {})
                        symbol_code = entry.get("data", {}).get("next_1_hours", {}).get("summary", {}).get("symbol_code", "")
                        if not symbol_code:
                            symbol_code = entry.get("data", {}).get("next_6_hours", {}).get("summary", {}).get("symbol_code", "")
                            
                        temp = details.get("air_temperature")
                        cloud = details.get("cloud_area_fraction")
                        
                        night_forecast.append({
                            "timestamp": ts,
                            "cloud": cloud,
                            "symbol_code": symbol_code,
                            "temp_c": temp,
                            "temp_f": (temp * 9/5) + 32 if temp is not None else None
                        })
                        
                        if len(night_forecast) >= 24:
                            break

        # 3. Conversions
        temp_f = (temp_c * 9/5) + 32 if temp_c is not None else None
        dew_point_f = (dew_point_c * 9/5) + 32 if dew_point_c is not None else None
        dew_point_margin_f = (temp_f - dew_point_f) if (temp_f is not None and dew_point_f is not None) else None
        dew_point_margin_c = (temp_c - dew_point_c) if (temp_c is not None and dew_point_c is not None) else None
        
        wind_avg_mph = wind_avg_mps * 2.23694 if wind_avg_mps is not None else None
        wind_gust_mph = wind_gust_mps * 2.23694 if wind_gust_mps is not None else None
        pressure_inhg = pressure_hpa * 0.02953 if pressure_hpa is not None else None
        precip_in = precip_mm * 0.03937 if precip_mm is not None else None

        # 4. Evaluate Roof Thresholds (Starfront Observatory)
        checks = {}
        allowed = True
        reasons = []

        # Wind check: <= 28 mph
        if wind_avg_mph is not None:
            checks["wind"] = {
                "val": round(wind_avg_mph, 1),
                "unit": "mph",
                "limit": "<= 28 mph",
                "ok": wind_avg_mph <= 28.0
            }
            if not checks["wind"]["ok"]:
                allowed = False
                reasons.append("Wind exceeds 28 mph")
        else:
            checks["wind"] = {"ok": False, "reason": "No data"}
            allowed = False
            reasons.append("Wind data unavailable")

        # Humidity check: <= 98%
        if humidity is not None:
            checks["humidity"] = {
                "val": humidity,
                "unit": "%",
                "limit": "<= 98%",
                "ok": humidity <= 98.0
            }
            if not checks["humidity"]["ok"]:
                allowed = False
                reasons.append("Humidity exceeds 98%")
        else:
            checks["humidity"] = {"ok": False, "reason": "No data"}
            allowed = False
            reasons.append("Humidity data unavailable")

        # Temperature check: 28°F to 110°F
        if temp_f is not None:
            checks["temperature"] = {
                "val": round(temp_f, 1),
                "unit": "°F",
                "limit": "28°F - 110°F",
                "ok": 28.0 <= temp_f <= 110.0
            }
            if not checks["temperature"]["ok"]:
                allowed = False
                reasons.append(f"Temperature {round(temp_f, 1)}°F is outside 28°F - 110°F")
        else:
            checks["temperature"] = {"ok": False, "reason": "No data"}
            allowed = False
            reasons.append("Temperature data unavailable")

        # Emergency wind gust check: <= 35 mph
        if wind_gust_mph is not None:
            checks["wind_gust"] = {
                "val": round(wind_gust_mph, 1),
                "unit": "mph",
                "limit": "<= 35 mph",
                "ok": wind_gust_mph <= 35.0
            }
            if not checks["wind_gust"]["ok"]:
                allowed = False
                reasons.append("Wind gust exceeds 35 mph")
        else:
            checks["wind_gust"] = {"ok": False, "reason": "No data"}
            allowed = False
            reasons.append("Wind gust data unavailable")

        # Dew point margin check: >= 3°F
        if dew_point_margin_f is not None:
            checks["dew_point_margin"] = {
                "val": round(dew_point_margin_f, 1),
                "unit": "°F",
                "limit": ">= 3°F",
                "ok": dew_point_margin_f >= 3.0
            }
            if not checks["dew_point_margin"]["ok"]:
                allowed = False
                reasons.append("Dew point margin less than 3°F")
        else:
            checks["dew_point_margin"] = {"ok": False, "reason": "No data"}
            allowed = False
            reasons.append("Dew point margin unavailable")

        # Cloud check: populated from MET Norway API
        if current_cloud is not None:
            checks["clouds"] = {
                "val": round(current_cloud, 0),
                "unit": "%",
                "limit": "<= 60%",
                "ok": current_cloud <= 60.0
            }
            if not checks["clouds"]["ok"]:
                allowed = False
                reasons.append(f"Cloud cover {round(current_cloud, 0)}% exceeds 60%")
        else:
            # Fallback to N/A if API failed or no coordinate data, do not block the dome
            checks["clouds"] = {
                "val": "N/A",
                "unit": "",
                "limit": "<= 60%",
                "ok": True,
                "note": "MET Norway API unavailable"
            }

        # Formulate response
        processed = {
            "station_id": obs_raw.get("station_id"),
            "station_name": obs_raw.get("station_name"),
            "timestamp": obs.get("timestamp"),
            "sunrise": sunrise,
            "sunset": sunset,
            "daytime_status": "daytime" if is_daytime else "nighttime",
            "night_forecast": night_forecast,
            "units": {
                "temp": "°C",
                "wind": "m/s",
                "pressure": "hPa",
                "precip": "mm",
                "humidity": "%"
            },
            "metrics": {
                "temp_c": temp_c,
                "temp_f": round(temp_f, 1) if temp_f is not None else None,
                "dew_point_c": dew_point_c,
                "dew_point_f": round(dew_point_f, 1) if dew_point_f is not None else None,
                "dew_point_margin_c": round(dew_point_margin_c, 1) if dew_point_margin_c is not None else None,
                "dew_point_margin_f": round(dew_point_margin_f, 1) if dew_point_margin_f is not None else None,
                "humidity": humidity,
                "wind_avg_mps": wind_avg_mps,
                "wind_avg_mph": round(wind_avg_mph, 1) if wind_avg_mph is not None else None,
                "wind_gust_mps": wind_gust_mps,
                "wind_gust_mph": round(wind_gust_mph, 1) if wind_gust_mph is not None else None,
                "wind_dir": wind_dir,
                "pressure_hpa": pressure_hpa,
                "pressure_inhg": round(pressure_inhg, 2) if pressure_inhg is not None else None,
                "solar_radiation": solar_rad,
                "uv": uv,
                "brightness": brightness,
                "precip_mm": precip_mm,
                "precip_in": round(precip_in, 3) if precip_in is not None else None,
                "lightning_count_1h": lightning_count_1h
            }
        }

        return {
            "station_id": obs_raw.get("station_id"),
            "station_name": obs_raw.get("station_name"),
            "last_fetched": int(time.time()),
            "physical_roof_status": physical_roof_status,
            "processed": processed,
            "roof_status": {
                "allowed": allowed,
                "reasons": reasons,
                "checks": checks
            },
            "raw": obs_raw
        }
