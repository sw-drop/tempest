import urllib.request
import json
import sys

def test_station(station_id):
    url = f"https://swd.weatherflow.com/swd/rest/observations/station/{station_id}?api_key=6bff2f89-84ab-463c-886e-fc0f443da4cf"
    print(f"Testing station {station_id} at {url}...")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            print(f"SUCCESS: Station {station_id} is accessible!")
            print(f"Station Name: {data.get('station_name')}")
    except Exception as e:
        print(f"FAILED for {station_id}: {e}")

test_station("15285")
test_station("41927")
