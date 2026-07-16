#!/usr/bin/env python3
import sys
import urllib.request
import json
import os
import argparse
from datetime import datetime, timedelta

def fetch_json(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Tempest-V5-Fetcher/1.0 gary@pillay.net"})
        with urllib.request.urlopen(req, timeout=10) as response:
            return json.loads(response.read().decode('utf-8'))
    except Exception as e:
        print(f"Error fetching API {url}: {e}", file=sys.stderr)
        return None

def fetch_rates(out_dir="v5-test/data", base="GBP", left="ZAR", right="USD", title_left=None, title_right=None):
    os.makedirs(out_dir, exist_ok=True)
    
    base_curr = base.upper()
    left_curr = left.upper()
    right_curr = right.upper()
    
    # Calculate dates for 6-month historical window
    today_str = datetime.now().strftime("%Y-%m-%d")
    six_months_ago_str = (datetime.now() - timedelta(days=180)).strftime("%Y-%m-%d")
    
    # Query historical range from Frankfurter API
    url = f"https://api.frankfurter.app/{six_months_ago_str}..{today_str}?from={base_curr}&to={left_curr},{right_curr}"
    print(f"Fetching 6-month historical rates from {six_months_ago_str} to {today_str} ({base_curr} -> {left_curr}, {right_curr})...")
    data = fetch_json(url)
    
    if not data or "rates" not in data:
        print("Error: Could not retrieve exchange rates from API.", file=sys.stderr)
        sys.exit(1)
        
    rates_series = data["rates"]
    if not rates_series:
        print("Error: Historical exchange rates timeseries is empty.", file=sys.stderr)
        sys.exit(1)
        
    # Extract chronological dates
    sorted_dates = sorted(rates_series.keys())
    latest_date = sorted_dates[-1]
    
    # Extract latest rates
    latest_left = rates_series[latest_date].get(left_curr)
    latest_right = rates_series[latest_date].get(right_curr)
    
    if latest_left is None or latest_right is None:
        print(f"Error: Latest rates for {left_curr} or {right_curr} not found in timeseries.", file=sys.stderr)
        sys.exit(1)
        
    # Tally historical high/low values
    left_rates = [rates_series[d][left_curr] for d in sorted_dates if left_curr in rates_series[d]]
    right_rates = [rates_series[d][right_curr] for d in sorted_dates if right_curr in rates_series[d]]
    
    high_left = max(left_rates)
    low_left = min(left_rates)
    
    high_right = max(right_rates)
    low_right = min(right_rates)
    
    # Titles configuration
    t_left = title_left if title_left else f"{base_curr} to {left_curr}"
    t_right = title_right if title_right else f"{base_curr} to {right_curr}"
    
    # Format Left Output (fra400cap.json)
    left_text = (
        f"<div style='font-size: 2.6rem; font-weight: bold; margin-bottom: 0.6rem;'>{latest_left:.2f} {left_curr}</div>"
        f"<div style='font-size: 1.2rem; color: var(--muted); line-height: 1.3;'>"
        f"<div style='margin-bottom: 0.3rem;'>6M High: {high_left:.2f} {left_curr}</div>"
        f"<div>6M Low: {low_left:.2f} {left_curr}</div></div>"
    )
    left_card = {
        "title": t_left,
        "subtitle": f"As of {latest_date}",
        "type": "text",
        "data": {
            "text": left_text
        }
    }
    
    # Format Right Output (q75cap.json)
    right_text = (
        f"<div style='font-size: 2.6rem; font-weight: bold; margin-bottom: 0.6rem;'>{latest_right:.2f} {right_curr}</div>"
        f"<div style='font-size: 1.2rem; color: var(--muted); line-height: 1.3;'>"
        f"<div style='margin-bottom: 0.3rem;'>6M High: {high_right:.2f} {right_curr}</div>"
        f"<div>6M Low: {low_right:.2f} {right_curr}</div></div>"
    )
    right_card = {
        "title": t_right,
        "subtitle": f"As of {latest_date}",
        "type": "text",
        "data": {
            "text": right_text
        }
    }
    
    # Write Left card payload
    left_path = os.path.join(out_dir, "rates_left.json")
    temp_left_path = f"{left_path}.tmp"
    try:
        with open(temp_left_path, "w", encoding="utf-8") as f:
            json.dump(left_card, f, indent=2)
        os.replace(temp_left_path, left_path)
        print(f"  [✓] Successfully updated {left_curr} rate in {left_path}")
    except Exception as e:
        print(f"  [!] Failed to write {left_path}: {e}", file=sys.stderr)
        
    # Write Right card payload
    right_path = os.path.join(out_dir, "rates_right.json")
    temp_right_path = f"{right_path}.tmp"
    try:
        with open(temp_right_path, "w", encoding="utf-8") as f:
            json.dump(right_card, f, indent=2)
        os.replace(temp_right_path, right_path)
        print(f"  [✓] Successfully updated {right_curr} rate in {right_path}")
    except Exception as e:
        print(f"  [!] Failed to write {right_path}: {e}", file=sys.stderr)

def main():
    parser = argparse.ArgumentParser(description="Fetch historical and current exchange rates and generate text card JSONs.")
    parser.add_argument("-o", "--out-dir", default="v5-test/data", help="Output directory for JSON files")
    parser.add_argument("--base", default="GBP", help="Base currency (e.g. GBP, USD, EUR)")
    parser.add_argument("--left", default="ZAR", help="Target currency for the left card (fra400cap)")
    parser.add_argument("--right", default="USD", help="Target currency for the right card (q75cap)")
    parser.add_argument("--title-left", help="Custom card title for the left card (defaults to '{BASE} to {LEFT}')")
    parser.add_argument("--title-right", help="Custom card title for the right card (defaults to '{BASE} to {RIGHT}')")
    args = parser.parse_args()
    fetch_rates(args.out_dir, args.base, args.left, args.right, args.title_left, args.title_right)

if __name__ == "__main__":
    main()
