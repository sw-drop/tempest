import urllib.request
import json

url = "https://api.met.no/weatherapi/locationforecast/2.0/compact?lat=-29.7300&lon=31.0865"
req = urllib.request.Request(url, headers={"User-Agent": "Tempest-V5-Fetcher/1.0 gary@pillay.net"})
with urllib.request.urlopen(req, timeout=10) as resp:
    data = json.loads(resp.read().decode('utf-8'))
    
print(json.dumps(data["properties"]["timeseries"][0]["data"]["instant"]["details"], indent=2))
