import subprocess
import os

files_to_get = [
    ("/docker/sfro-nightly/update_dashboard.py", "update_dashboard.py"),
    ("/docker/sfro-nightly/html_visualizer.py", "html_visualizer.py"),
    ("/docker/sfro-nightly/discord_extractor.py", "discord_extractor.py"),
    ("/docker/sfro-nightly/forecast_generator.py", "forecast_generator.py"),
]

scratch_dir = "/Users/gary/.gemini/antigravity/brain/0302a658-87e5-430e-a3d4-eae42db87825/scratch"
os.makedirs(scratch_dir, exist_ok=True)

for remote, local in files_to_get:
    local_path = os.path.join(scratch_dir, local)
    print(f"Fetching {remote} -> {local_path}")
    res = subprocess.run(["scp", f"Pi5-1:{remote}", local_path], capture_output=True, text=True)
    if res.returncode != 0:
        print(f"Error: {res.stderr}")
    else:
        print("Success")
