import os
import shutil
import json

src_dir = "/Users/gary/syncdata/Sync/dev/sfro-dash/sfro-dash-v5/data"
dest_dir = "/Users/gary/syncdata/Sync/dev/sfro-dash/sfro-dash-v5/v5-test/data"

os.makedirs(dest_dir, exist_ok=True)

# 1. Copy the JPEG files
jpegs = ["NightA.jpg", "NightB.jpg"]
for jpeg in jpegs:
    src_path = os.path.join(src_dir, jpeg)
    dest_path = os.path.join(dest_dir, jpeg)
    print(f"Copying {jpeg}...")
    shutil.copy2(src_path, dest_path)

# 2. Copy the JSON files
json_files = [
    "skycam.json", "atmos.json", "fra400cap.json", 
    "q75cap.json", "forecast.json", "roof.json"
]
for jf in json_files:
    src_path = os.path.join(src_dir, jf)
    dest_path = os.path.join(dest_dir, jf)
    print(f"Copying {jf}...")
    shutil.copy2(src_path, dest_path)

# 3. Copy and update image JSON configurations (fra400.json, 75q.json)
# to point to v5-test/data/ path
image_jsons = {
    "fra400.json": "v5-test/data/NightA.jpg",
    "75q.json": "v5-test/data/NightB.jpg"
}

for filename, img_src in image_jsons.items():
    src_path = os.path.join(src_dir, filename)
    dest_path = os.path.join(dest_dir, filename)
    print(f"Copying and updating {filename}...")
    
    with open(src_path, 'r') as f:
        data = json.load(f)
        
    data['data']['src'] = img_src
    
    with open(dest_path, 'w') as f:
        json.dump(data, f, indent=2)

print("\nSetup of v5-test/data directory complete!")
