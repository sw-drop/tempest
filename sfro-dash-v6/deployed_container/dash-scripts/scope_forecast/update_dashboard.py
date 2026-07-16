# update_dashboard.py v2.0.0 (Dockerized Scheduler)
import schedule
import time
import sys
import discord_extractor
import forecast_generator
import html_visualizer

def run_pipeline():
    print(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] Starting Scheduled Dashboard Update...")
    try:
        discord_extractor.main()
    except Exception as e:
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] ERROR during discord_extractor execution: {e}")
        
    try:
        # Trigger forecast updates directly 
        forecast_generator.main()
    except Exception as e:
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] ERROR during forecast_generator execution: {e}")
        
    try:
        html_visualizer.render_html()
    except Exception as e:
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] ERROR during html_visualizer execution: {e}")
        
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Update Complete. Sleeping until next run.")

# Run once immediately on startup
run_pipeline()

# Schedule to run every 15 minutes
schedule.every(15).minutes.do(run_pipeline)

print("Scheduler initialized. Waiting for next interval...")
while True:
    schedule.run_pending()
    time.sleep(1)
