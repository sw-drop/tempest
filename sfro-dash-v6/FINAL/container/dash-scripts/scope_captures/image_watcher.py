#!/usr/bin/env python3
import sys
import os
import json
import argparse
import pathlib
import shutil
from datetime import datetime

# Import image processing libraries safely
try:
    from PIL import Image
    import numpy as np
    from astropy.io import fits
except ImportError as e:
    print(f"Error: Missing required library for FITS processing: {e}", file=sys.stderr)
    print("Please install requirements: pip install Pillow numpy astropy", file=sys.stderr)
    sys.exit(1)

def convert_fits_to_jpeg(fits_path, out_jpeg_path, max_width):
    try:
        with fits.open(fits_path) as hdul:
            data = hdul[0].data
            if data is None and len(hdul) > 1:
                data = hdul[1].data
            if data is None:
                print(f"Error: No FITS array data found in {fits_path}", file=sys.stderr)
                return False, "No data array"
                
            # Parse target from headers
            header = hdul[0].header
            target_name = header.get("OBJECT", "").strip()
            if not target_name:
                target_name = header.get("TARGET", "").strip()
                
            # Perform astronomical histogram stretch (percentile clipping)
            p_lo = np.percentile(data, 5)
            p_hi = np.percentile(data, 99.5)
            if p_hi == p_lo:
                p_hi = p_lo + 1
            data = np.clip(data, p_lo, p_hi)
            data = (data - p_lo) / (p_hi - p_lo)
            data = (data * 255).astype(np.uint8)
            
            # Format dim dimensions if color FITS
            if data.ndim == 3 and data.shape[0] == 3:
                data = np.moveaxis(data, 0, -1)
                
            img = Image.fromarray(data)
            
            # Downscale image to limit bandwidth (UHD/FHD adjustments)
            if img.width > max_width:
                ratio = max_width / img.width
                new_height = int(img.height * ratio)
                img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)
                
            # Write JPEG atomically
            temp_path = f"{out_jpeg_path}.tmp"
            img.save(temp_path, "JPEG", quality=80)
            os.replace(temp_path, out_jpeg_path)
            return True, target_name
    except Exception as e:
        print(f"Failed to process FITS {fits_path}: {e}", file=sys.stderr)
        return False, str(e)

def main():
    parser = argparse.ArgumentParser(description="Watch for new FITS files, convert to downscaled JPEGs, and generate image cards.")
    parser.add_argument("-o", "--out-dir", default="v5-test/data", help="Output directory for JSON and JPEGs")
    parser.add_argument("--images-dir", default="/app/images", help="Base directory containing telescope images")
    parser.add_argument("--max-width", type=int, default=3840, help="Maximum width for the output JPEGs (default 3840 for UHD)")
    args = parser.parse_args()
    
    os.makedirs(args.out_dir, exist_ok=True)
    
    scopes = {
        "fra400": {
            "folder_name": "FRA400",
            "out_json": "fra400_raw.json",
            "out_jpeg": "fra400.jpg",
            "title": "FRA400"
        },
        "75q": {
            "folder_name": "75Q",
            "out_json": "75q_raw.json",
            "out_jpeg": "75q.jpg",
            "title": "75Q"
        }
    }
    
    for safe_scope, config in scopes.items():
        # Determine watch directory
        watch_dir = os.path.join(args.images_dir, config["folder_name"])
        if not os.path.exists(watch_dir):
            # Fallback to local directories
            for fallback in [os.path.join("images", config["folder_name"]), os.path.join("v5-test", "images", config["folder_name"]), "."]:
                if os.path.exists(fallback) and fallback != ".":
                    watch_dir = fallback
                    break
            else:
                watch_dir = "."
                
        p = pathlib.Path(watch_dir)
        fits_files = list(p.rglob("*.fit*"))
        
        # Filter temp assets
        fits_files = [
            str(f) for f in fits_files
            if f.is_file() and not f.name.startswith('.') and not f.name.endswith('.tmp')
        ]
        
        # Special filter for local fallback scans
        if not fits_files and watch_dir == ".":
            fits_files = [
                str(f) for f in p.rglob(f"*{config['folder_name']}*.fit*")
                if f.is_file() and not f.name.startswith('.') and not f.name.endswith('.tmp')
            ]
            
        out_jpeg_path = os.path.join(args.out_dir, config["out_jpeg"])
        out_json_path = os.path.join(args.out_dir, config["out_json"])

        if not fits_files:
            # If no JSON exists, write a clean fallback text card to prevent frontend errors
            if not os.path.exists(out_json_path):
                card_payload = {
                    "title": config["title"],
                    "subtitle": "No Active Target",
                    "type": "text",
                    "data": {
                        "text": "Waiting for first exposure...\n(No FITS files detected in watch folder)"
                    }
                }
                try:
                    with open(out_json_path, "w", encoding="utf-8") as f:
                        json.dump(card_payload, f, indent=2)
                except Exception:
                    pass
            continue
            
        # Find latest FITS file by modified time
        latest_fits = max(fits_files, key=os.path.getmtime)
        
        # Check if we can skip compilation (stateless cache check)
        fits_mtime = os.path.getmtime(latest_fits)
        if os.path.exists(out_jpeg_path):
            jpeg_mtime = os.path.getmtime(out_jpeg_path)
            if jpeg_mtime >= fits_mtime:
                # Output JPEG is newer or equal to the FITS, skip compile
                continue
                
        print(f"New FITS detected for {config['title']}: {latest_fits}")
        success, target_name = convert_fits_to_jpeg(latest_fits, out_jpeg_path, args.max_width)
        
        if success:
            # Fallback to directory parsing if object header is missing
            if not target_name:
                try:
                    rel_path = pathlib.Path(latest_fits).relative_to(watch_dir)
                    parts = rel_path.parts
                    if len(parts) >= 3:
                        target_name = parts[1]
                except Exception:
                    pass
            if not target_name:
                target_name = "Active Target"
                
            # Create V5 card payload (using 'src' as expected by index.html)
            card_payload = {
                "title": config["title"],
                "subtitle": target_name,
                "type": "image",
                "data": {
                    "src": config["out_jpeg"]
                }
            }
            
            temp_json_path = f"{out_json_path}.tmp"
            try:
                with open(temp_json_path, "w", encoding="utf-8") as f:
                    json.dump(card_payload, f, indent=2)
                os.replace(temp_json_path, out_json_path)
                print(f"  [✓] Successfully updated image card config {out_json_path}")
            except Exception as e:
                print(f"  [!] Failed to write config {out_json_path}: {e}", file=sys.stderr)

if __name__ == "__main__":
    main()
