# html_visualizer.py v1.17.0

import os
import json
from datetime import datetime, timedelta
import pytz

# ==================== CONFIGURATION ====================
DATA_DIR = "data"
OUTPUT_HTML = "index.html"
DAYS_TO_PLOT = 0 

# Muted, Deep Sea System Colors
C_WAIT = "#ca8a04"       
C_WAIT_TEXT = "#ffffff"  
C_FLIP = "#475569"       
C_CLOSED = "#020617"     
C_OPEN = "#0369a1"       

# STRICT Deep Sea & Slate Palette for Targets
TARGET_COLORS = [
    "#1B3B5A", "#205375", "#112B3C", "#3282B8", "#0F4C75", 
    "#2C516C", "#1B262C", "#3B6978", "#2A475E", "#173042", 
    "#30475E", "#27496D", "#142850", "#00909E", "#2E4C6D", 
    "#395B64", "#2C3333", "#266691", "#1E5F74", "#132743"  
]
# =======================================================

def load_json(filepath):
    if not os.path.exists(filepath): return {}
    with open(filepath, 'r', encoding='utf-8') as f: return json.load(f)

def parse_time(ts_str):
    if not ts_str: return None
    return datetime.fromisoformat(ts_str)

def get_pct(target_time, t0, t1):
    return max(0, min(100, (target_time.timestamp() - t0) / (t1 - t0) * 100))

def get_roof_open_blocks(roof_data, dusk, dawn):
    opens = sorted([parse_time(t) for t in roof_data.get("open_events", [])])
    closes = sorted([parse_time(t) for t in roof_data.get("closed_events", [])])
    open_blocks = []
    events = [(o, 'open') for o in opens] + [(c, 'close') for c in closes]
    events.sort()
    
    current_state = 'closed'
    last_time = dusk
    if events and events[0][1] == 'close': open_blocks.append((dusk, events[0][0]))
        
    for dt, event_type in events:
        if event_type == 'open':
            last_time = dt
            current_state = 'open'
        elif event_type == 'close':
            if current_state == 'open': open_blocks.append((last_time, dt))
            current_state = 'closed'
            
    if current_state == 'open': open_blocks.append((last_time, dawn))
    return open_blocks

def process_scope_blocks(events, roof_closes, dawn, plot_end):
    targets, waits, flips = [], [], []
    id_counter = 1
    
    raw_targets = events.get("targets", [])
    for i, t in enumerate(raw_targets):
        start = parse_time(t["start"])
        if not start or start > plot_end: continue
        raw_end = parse_time(t["end"])
        next_target_start = parse_time(raw_targets[i+1]["start"]) if i + 1 < len(raw_targets) else None
        next_close = next((c for c in roof_closes if c > start), dawn)
        end = min([d for d in [raw_end, next_target_start, next_close, plot_end] if d is not None])
        if end > start:
            has_fade = (raw_end is None)
            targets.append({"id": id_counter, "name": t["name"], "start": start, "end": end, "color": TARGET_COLORS[(id_counter - 1) % len(TARGET_COLORS)], "fade": has_fade})
            id_counter += 1
            
    for w in events.get("target_waits", []):
        start = parse_time(w["start"])
        if not start or start > plot_end: continue
        raw_end = parse_time(w["end"])
        next_close = next((c for c in roof_closes if c > start), dawn)
        end = min(min(raw_end, next_close) if raw_end else next_close, plot_end)
        if end > start: 
            has_fade = (raw_end is None)
            waits.append({"start": start, "end": end, "fade": has_fade})
            
    for f in events.get("meridian_flips", []):
        start = parse_time(f["start"])
        if not start or start > plot_end: continue
        raw_end = parse_time(f["end"])
        next_close = next((c for c in roof_closes if c > start), dawn)
        end = min(min(raw_end, next_close) if raw_end else next_close, plot_end)
        if end > start: 
            has_fade = (raw_end is None)
            flips.append({"start": start, "end": end, "fade": has_fade})
            
    return targets, waits, flips

def generate_track_lines(dusk_pct, dawn_pct, opens_pct, closes_pct):
    lines = ""
    if 0 <= dusk_pct <= 100: lines += f"<div class='track-vline tv-dusk' style='left:{dusk_pct}%;'></div>"
    if 0 <= dawn_pct <= 100: lines += f"<div class='track-vline tv-dawn' style='left:{dawn_pct}%;'></div>"
    for o in opens_pct:
        if 0 <= o <= 100: lines += f"<div class='track-vline tv-open' style='left:{o}%;'></div>"
    for c in closes_pct:
        if 0 <= c <= 100: lines += f"<div class='track-vline tv-close' style='left:{c}%;'></div>"
    return lines

def render_html():
    scope_data = {}
    all_dates = set()
    
    if os.path.exists(DATA_DIR):
        for filename in os.listdir(DATA_DIR):
            if filename.endswith("_log.json"):
                scope_name = filename.replace("_log.json", "")
                data = load_json(os.path.join(DATA_DIR, filename))
                scope_data[scope_name] = data
                all_dates.update(data.keys())
    
    sorted_dates = sorted(list(all_dates), reverse=True) 
    if DAYS_TO_PLOT > 0: sorted_dates = sorted_dates[:DAYS_TO_PLOT]
    
    if not sorted_dates: return
    
    html = [
        "<!DOCTYPE html>",
        "<html>",
        "<head>",
        "<meta charset='UTF-8'>",
        "<title>SFRO Nightly</title>",
        "<link rel=\"icon\" type=\"image/png\" href=\"favicon.png\">",
        "<style>",
        "body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #020617; color: #cbd5e1; padding: 20px; }",
        "h1 { text-align: center; color: #f8fafc; margin-bottom: 30px; font-weight: 600; letter-spacing: 1px; }",
        
        ".night { background: #0f172a; margin-bottom: 40px; padding: 25px; border-radius: 8px; box-shadow: 0 4px 15px rgba(0,0,0,0.5); border: 1px solid #1e293b; }",
        ".night-title { font-size: 20px; font-weight: 600; border-bottom: 1px solid #1e293b; padding-bottom: 10px; margin-bottom: 25px; color: #f8fafc; }",
        
        ".night-forecast { border: 2px dashed #0d9488; background: #081223; }",
        ".night-forecast .night-title { color: #5eead4; border-bottom: 1px dashed #0d9488; }",
        
        ".timeline { position: relative; margin-left: 90px; }",
        ".track-label { position: absolute; left: -90px; width: 75px; text-align: right; font-weight: bold; font-size: 15px; color: #94a3b8; }",
        ".track-label-roof { font-size: 13px; color: #64748b; }",
        
        ".track { position: absolute; width: 100%; background: " + C_CLOSED + "; border-radius: 4px; box-shadow: inset 0 2px 6px rgba(0,0,0,0.8); border: 1px solid #1e293b; overflow: hidden; }",
        
        ".block { position: absolute; box-sizing: border-box; font-weight: bold; font-size: 13px; color: white; box-shadow: 0 2px 4px rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: flex-start; padding-left: 8px; overflow: hidden; border-radius: 4px; border: 1px solid rgba(255,255,255,0.1); z-index: 10; }",
        ".block-roof { justify-content: center; padding-left: 0; height: 16px; top: 3px; font-size: 10px; }",
        ".block-scope { height: 38px; top: 2px; }",
        
        ".block-fade {",
        "  mask-image: linear-gradient(to right, rgba(0,0,0,1) 60%, rgba(0,0,0,0) 100%);",
        "  -webkit-mask-image: linear-gradient(to right, rgba(0,0,0,1) 60%, rgba(0,0,0,0) 100%);",
        "  border-right: none;",
        "}",
        
        ".w-col { position: absolute; transform: translateX(-50%); top: -4px; display: flex; flex-direction: column; align-items: center; width: 40px; text-align: center; z-index: 20; }",
        ".w-icon { width: 22px; height: 22px; margin-bottom: 2px; filter: drop-shadow(0px 2px 3px rgba(0,0,0,0.8)); }",
        ".w-text { font-size: 10px; line-height: 1.15; font-weight: 600; text-shadow: 1px 1px 2px rgba(0,0,0,0.8); }",
        ".w-temp { color: #f8fafc; }",
        ".w-cloud { color: #94a3b8; font-size: 15px; font-weight: bold; margin: 2px 0; }",
        ".w-wind { color: #5eead4; }",

        ".block-wait { justify-content: center; padding-left: 0; background: " + C_WAIT + "; color: " + C_WAIT_TEXT + "; }",
        ".block-flip { justify-content: center; padding-left: 0; background: " + C_FLIP + "; color: #fff; }",
        ".block-open { background: " + C_OPEN + "; color: #f8fafc; }",
        ".block-target { color: #fff; text-shadow: 1px 1px 2px rgba(0,0,0,0.8); }",

        ".track-vline { position: absolute; top: 0; height: 100%; border-left: 2px solid; z-index: 1; opacity: 0.4; }",
        ".tv-dusk { border-color: #38bdf8; }",
        ".tv-dawn { border-color: #facc15; }",
        ".tv-open { border-color: #4ade80; }",
        ".tv-close { border-color: #f87171; }",
        
        ".scope-key { position: absolute; width: 100%; font-size: 13px; color: #94a3b8; display: flex; flex-wrap: wrap; gap: 10px; }",
        ".key-item { display: inline-flex; align-items: center; }",
        ".k-box { display: inline-block; width: 22px; height: 22px; text-align: center; line-height: 22px; color: white; border-radius: 3px; margin-right: 6px; font-size: 12px; font-weight: bold; border: 1px solid rgba(255,255,255,0.1); }",
        
        ".time-axis { position: absolute; top: 0; width: 100%; height: 25px; border-bottom: 2px solid #334155; }",
        ".tick { position: absolute; bottom: 5px; transform: translateX(-50%); font-size: 12px; color: #64748b; font-weight: 600; }",
        ".tick-mark { position: absolute; bottom: -2px; width: 2px; height: 6px; background: #334155; transform: translateX(-50%); }",
        ".marker-icon { position: absolute; top: -12px; transform: translateX(-50%); font-size: 13px; background: #0f172a; border-radius: 50%; width: 22px; height: 22px; display: flex; align-items: center; justify-content: center; box-shadow: 0 2px 4px rgba(0,0,0,0.5); z-index: 30; border: 1px solid #334155; }",

        "/* Section Divider for Forecast Track */",
        ".f-divider { position: absolute; left: -90px; width: calc(100% + 90px); border-top: 2px dashed rgba(13, 148, 136, 1.0); z-index: 5; pointer-events: none; }",

        ".legend-master { display: flex; flex-wrap: wrap; gap: 20px; background: #0f172a; padding: 20px; border-radius: 8px; box-shadow: 0 -4px 15px rgba(0,0,0,0.5); margin-top: 40px; align-items: center; justify-content: center; position: sticky; bottom: 20px; border: 1px solid #1e293b; z-index: 100; color: #cbd5e1; }",
        ".legend-item { display: flex; align-items: center; font-size: 14px; font-weight: 500; }",
        ".l-box { width: 20px; height: 20px; border-radius: 4px; margin-right: 8px; border: 1px solid rgba(255,255,255,0.1); text-align: center; line-height: 20px; font-size: 11px; font-weight: bold; color: #fff; }",
        ".l-icon { font-size: 18px; margin-right: 8px; text-align: center; }",
        "</style></head><body>",
        "<h1>SFRO Nightly</h1>"
    ]

    central = pytz.timezone('America/Chicago')
    obs_time = datetime.now(central).strftime("%H:%M")
    
    for i, date_key in enumerate(sorted_dates):
        is_forecast = date_key.endswith("_forecast")
        raw_date = date_key.replace("_forecast", "")
        
        date_obj = datetime.strptime(raw_date, "%Y-%m-%d")
        formatted_date = date_obj.strftime("%A, %d %B %Y")
        
        obs_time_html = f"<span style='float:right; color:#94a3b8;'>Observatory Time: {obs_time}</span>" if i == 0 else ""
        display_title = f"Forecast: {formatted_date}{obs_time_html}" if is_forecast else f"{formatted_date}{obs_time_html}"
        
        base_night = next((d.get(date_key) for d in scope_data.values() if date_key in d), None)
        if not base_night: continue
        dusk = parse_time(base_night["astral"]["nautical_dusk"])
        dawn = parse_time(base_night["astral"]["nautical_dawn"])
        roof_data = base_night.get("roof", {})
        
        opens = [parse_time(t) for t in roof_data.get("open_events", [])]
        closes = [parse_time(t) for t in roof_data.get("closed_events", [])]
        
        night_class = "night night-forecast" if is_forecast else "night"
        
        if not opens:
            html.append(f"<div class='{night_class}'>")
            html.append(f"<div class='night-title' style='margin-bottom:0; border-bottom:none;'>")
            html.append(f"  {display_title} <span style='margin-left:20px; color:#64748b; font-size:16px; font-weight:normal;'><span style='font-size:20px; margin-right:8px; opacity:0.7;'>🌙</span> Roof didn't open. No targets imaged.</span>")
            html.append("</div></div>")
            continue
            
        html.append(f"<div class='{night_class}'><div class='night-title'>{display_title}</div>")
        
        earliest_event = min(opens) if opens else dusk
        latest_event = max(closes) if closes else dawn
        plot_start = min(dusk, earliest_event)
        plot_end = max(dawn, latest_event)
        
        buffer = (plot_end - plot_start).total_seconds() * 0.02
        t0 = plot_start.timestamp() - buffer
        t1 = plot_end.timestamp() + buffer
        
        roof_closes_sorted = sorted(closes)
        dusk_pct = get_pct(dusk, t0, t1)
        dawn_pct = get_pct(dawn, t0, t1)
        opens_pct = [get_pct(o, t0, t1) for o in opens]
        closes_pct = [get_pct(c, t0, t1) for c in closes]
        bg_lines_html = generate_track_lines(dusk_pct, dawn_pct, opens_pct, closes_pct)
        base_height = 440 if is_forecast else 340
        if len(scope_data) > 2:
            base_height += (len(scope_data) - 2) * 100
        
        html.append(f"<div class='timeline' style='height:{base_height}px;'>")
        
        html.append("<div class='time-axis'>")
        current_hour = plot_start.replace(minute=0, second=0, microsecond=0)
        if current_hour < plot_start: current_hour += timedelta(hours=1)
        while current_hour <= plot_end:
            pct = get_pct(current_hour, t0, t1)
            time_str = current_hour.strftime("%H:%M")
            html.append(f"<div class='tick-mark' style='left:{pct}%;'></div>")
            html.append(f"<div class='tick' style='left:{pct}%;'>{time_str}</div>")
            current_hour += timedelta(hours=1)
            
        if 0 <= dusk_pct <= 100: html.append(f"<div class='marker-icon' style='left:{dusk_pct}%;' title='Nautical Dusk'>🌙</div>")
        if 0 <= dawn_pct <= 100: html.append(f"<div class='marker-icon' style='left:{dawn_pct}%;' title='Nautical Dawn'>☀️</div>")
        for o in opens_pct:
            if 0 <= o <= 100: html.append(f"<div class='marker-icon' style='left:{o}%;' title='Roof Open'>🟢</div>")
        for c in closes_pct:
            if 0 <= c <= 100: html.append(f"<div class='marker-icon' style='left:{c}%;' title='Roof Close'>🔴</div>")
        html.append("</div>")

        current_top = 35
        scopes_rendered = 0
        
        scope_order = []
        try:
            from dotenv import load_dotenv
            load_dotenv()
            scopes_env = os.environ.get("SCOPES", "")
            for p in scopes_env.split(","):
                if ":" in p:
                    scope_order.append(p.split(":")[0].strip())
        except Exception:
            pass
            
        def scope_sort_key(item):
            name = item[0]
            try:
                return scope_order.index(name)
            except ValueError:
                return 999

        for scope_name, data in sorted(scope_data.items(), key=scope_sort_key):
            scope_events = data.get(date_key, {}).get("events", {})
            
            html.append(f"<div class='track-label' style='top:{current_top + 11}px;'>{scope_name}</div>")
            html.append(f"<div class='track' style='top:{current_top}px; height:44px;'>")
            html.append(bg_lines_html) 
            
            targets, waits, flips = process_scope_blocks(scope_events, roof_closes_sorted, dawn, plot_end)
            for t in targets:
                left = get_pct(t["start"], t0, t1)
                width = get_pct(t["end"], t0, t1) - left
                fade_cls = " block-fade" if (t.get("fade") or is_forecast) else ""
                html.append(f"<div class='block block-scope block-target{fade_cls}' style='left:{left}%; width:{width}%; background:{t['color']};' title='{t['name']}'>{t['id']}</div>")
            for w in waits:
                left = get_pct(w["start"], t0, t1)
                width = get_pct(w["end"], t0, t1) - left
                fade_cls = " block-fade" if (w.get("fade") or is_forecast) else ""
                html.append(f"<div class='block block-scope block-wait{fade_cls}' style='left:{left}%; width:{width}%;' title='Wait'>W</div>")
            for f in flips:
                left = get_pct(f["start"], t0, t1)
                width = get_pct(f["end"], t0, t1) - left
                fade_cls = " block-fade" if (f.get("fade") or is_forecast) else ""
                html.append(f"<div class='block block-scope block-flip{fade_cls}' style='left:{left}%; width:{width}%;' title='Meridian Flip'>F</div>")
            html.append("</div>")
            
            html.append(f"<div class='scope-key' style='top:{current_top + 50}px;'>")
            if targets:
                for t in targets: html.append(f"<span class='key-item'><span class='k-box' style='background:{t['color']};'>{t['id']}</span> {t['name']}</span>")
            else:
                empty_msg = "No Target Scheduler forecast data." if is_forecast else "No targets imaged."
                html.append(f"<span class='key-item' style='color:#64748b; font-style:italic;'>{empty_msg}</span>")
            html.append("</div>")
            
            scopes_rendered += 1

            if scopes_rendered == 1:
                if is_forecast:
                    html.append(f"<div class='f-divider' style='top:{current_top + 80}px;'></div>")
                    
                    html.append(f"<div class='track-label track-label-roof' style='top:{current_top + 108}px; color: #5eead4;'>Weather</div>")
                    html.append(f"<div class='track' style='top:{current_top + 95}px; height:60px; background:transparent; border:none; box-shadow:none; overflow:visible;'>")
                    html.append(bg_lines_html)
                    
                    if base_night.get("weather"):
                        for w in base_night["weather"]:
                            w_time = parse_time(w["time"])
                            if not w_time or w_time < plot_start or w_time > plot_end: continue
                            pct = get_pct(w_time, t0, t1)
                            icon_url = f"https://raw.githubusercontent.com/metno/weathericons/main/weather/svg/{w['symbol']}.svg"
                            
                            html.append(f"<div class='w-col' style='left:{pct}%;'>")
                            html.append(f"  <img src='{icon_url}' class='w-icon' title='{w['symbol']}'>")
                            html.append(f"  <div class='w-text w-temp' title='Temperature'>{round(w['temp'])}&#176;</div>")
                            html.append(f"  <div class='w-text w-cloud' title='Cloud Cover'>{round(w['cloud'])}%</div>")
                            html.append(f"  <div class='w-text w-wind' title='Wind Speed (m/s)'>{round(w['wind'])}</div>")
                            html.append("</div>")
                    else:
                        html.append("<div style='position: absolute; width: 100%; top: 20px; text-align: center; color: #64748b; font-style: italic; font-size: 13px;'>No weather data available</div>")
                    html.append("</div>")

                    html.append(f"<div class='f-divider' style='top:{current_top + 160}px;'></div>")

                    if base_night.get("moon"):
                        moon = base_night["moon"]
                        html.append(f"<div class='track-label track-label-roof' style='top:{current_top + 188}px; color: #facc15; left: -100px; width: 60px; text-align: right;'>Moon</div>")
                        
                        html.append(f"<div class='track' style='top:{current_top + 175}px; height:100px; background:transparent; border:none; box-shadow:none; overflow:visible;'>")
                        html.append(bg_lines_html)
                        
                        points = moon.get("path", [])
                        if points:
                            max_alt = max([p["alt"] for p in points])
                            y_max = max_alt + 5 if max_alt > 0 else 20
                            
                            for tick in range(0, int(y_max) + 10, 10):
                                if tick > y_max: break
                                y_pct = 100 - (tick / y_max * 100)
                                html.append(f"<div style='position:absolute; top:{y_pct}%; left:0; width:100%; border-top:1px dashed rgba(148, 163, 184, 0.2); z-index:1;'></div>")
                                html.append(f"<div style='position:absolute; top:{y_pct}%; left:-28px; transform:translateY(-50%); color:#64748b; font-size:11px; font-weight:bold; z-index:2;'>{tick}&#176;</div>")
                            
                            svg_pts = []
                            for p in points:
                                pt_time = parse_time(p["time"])
                                if not pt_time or pt_time < plot_start or pt_time > plot_end: continue
                                x_pct = get_pct(pt_time, t0, t1)
                                y_pct = 100 - (p["alt"] / y_max * 100)
                                svg_pts.append((round(x_pct, 2), round(y_pct, 2)))
                            
                            if svg_pts:
                                pts_str = " ".join([f"{x} {y}" for x, y in svg_pts])
                                fill_pts = f"{svg_pts[0][0]},100 {pts_str} {svg_pts[-1][0]},100"
                                
                                html.append(f"<svg width='100%' height='100%' viewBox='0 0 100 100' preserveAspectRatio='none' style='position:absolute; top:0; left:0; overflow:hidden; z-index:5;'>")
                                html.append(f"<polygon points='{fill_pts}' fill='rgba(240, 230, 140, 0.05)' stroke='none' />")
                                html.append(f"<polyline points='{pts_str}' fill='none' stroke='#f0e68c' stroke-width='1.5' vector-effect='non-scaling-stroke' />")
                                html.append("</svg>")
                                
                        events_str = moon.get("events_string", f"Sunset: {moon.get('sunset', '')} &nbsp;&bull;&nbsp; Sunrise: {moon.get('sunrise', '')}")
                        moon_str = f"{moon['phase']} &nbsp;&bull;&nbsp; Age: {moon['age']} days &nbsp;&bull;&nbsp; Illuminated: {moon['illum']} &nbsp;&bull;&nbsp; Peak Elevation: {moon['peak']}&#176; &nbsp;&bull;&nbsp; {events_str}"
                        html.append(f"<div style='position:absolute; bottom:-25px; left:0; width:100%; text-align:center; font-size:13px; color:#94a3b8; display:flex; justify-content:center; align-items:center;'>{moon_str}</div>")
                        html.append("</div>")

                    if len(scope_data) > 1:
                        html.append(f"<div class='f-divider' style='top:{current_top + 305}px;'></div>")
                        
                    current_top = 350
                else:
                    html.append(f"<div class='track-label track-label-roof' style='top:{current_top + 108}px;'>Roof</div>")
                    html.append(f"<div class='track' style='top:{current_top + 105}px; height:22px;'>")
                    html.append(bg_lines_html) 
                    for r_start, r_end in get_roof_open_blocks(roof_data, dusk, dawn):
                        if r_start >= plot_end: continue
                        left = get_pct(r_start, t0, t1)
                        width = get_pct(r_end, t0, t1) - left
                        html.append(f"<div class='block block-roof block-open' style='left:{left}%; width:{width}%;' title='Roof Open'>OPEN</div>")
                    html.append("</div>")
                    
                    current_top = 223
            else:
                current_top += 100

        html.append("</div></div>") 

    html.append("<div class='legend-master'>")
    html.append("<div style='display: flex; flex-wrap: wrap; gap: 20px; justify-content: center; flex: 1;'>")
    html.append(f"<div class='legend-item'><div class='l-box' style='background:{C_CLOSED}; border: 1px solid #334155;'></div> Roof Closed</div>")
    html.append(f"<div class='legend-item'><div class='l-box' style='background:{C_OPEN}; color:#f8fafc;'></div> Roof Open</div>")
    html.append(f"<div class='legend-item'><div class='l-box' style='background:{C_WAIT}; color:{C_WAIT_TEXT};'>W</div> Target Wait</div>")
    html.append(f"<div class='legend-item'><div class='l-box' style='background:{C_FLIP}; color:#fff;'>F</div> Meridian Flip</div>")
    html.append(f"<div class='legend-item'><div class='l-icon'>🌙</div> Nautical Dusk</div>")
    html.append(f"<div class='legend-item'><div class='l-icon'>☀️</div> Nautical Dawn</div>")
    html.append(f"<div class='legend-item'><div class='l-icon'>🟢</div> Roof Opened</div>")
    html.append(f"<div class='legend-item'><div class='l-icon'>🔴</div> Roof Closed</div>")
    html.append("</div>")
    
    # Use standard ISO format for the JS to parse reliably
    utc_str = datetime.utcnow().isoformat() + "Z"
    html.append(f"<div class='legend-item' style='color: #64748b; font-size: 12px; margin-left: auto; border-left: 1px solid #334155; padding-left: 20px;' id='last-updated' data-utc='{utc_str}'>Last Updated: Loading...</div>")
    
    # Inject script to convert UTC to local time in the exact requested format
    js_script = """
    <script>
        document.addEventListener("DOMContentLoaded", function() {
            var el = document.getElementById('last-updated');
            if (el && el.dataset.utc) {
                var d = new Date(el.dataset.utc);
                var day = String(d.getDate()).padStart(2, '0');
                var month = d.toLocaleString('default', { month: 'short' });
                var year = d.getFullYear();
                var hours = String(d.getHours()).padStart(2, '0');
                var minutes = String(d.getMinutes()).padStart(2, '0');
                el.innerText = 'Last Updated: ' + day + ' ' + month + ' ' + year + ' ' + hours + ':' + minutes;
            }
        });
    </script>
    """
    html.append(js_script)
    
    html.append("</div></body></html>")

    with open(OUTPUT_HTML, "w", encoding="utf-8") as f: f.write("\n".join(html))
    print(f"[✓] Dashboard generated successfully: {OUTPUT_HTML}")

if __name__ == "__main__":
    render_html()
