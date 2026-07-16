#!/usr/bin/env python3
"""
NASA APOD Image & Text Fetcher
Fetches the NASA Astronomy Picture of the Day (APOD) for a given date,
scales and crops the image to 1920x1280 (3:2 ratio), and optionally saves
the accompanying text explanation to a matching .txt file.
The target date is automatically appended to the output filenames.
"""

import os
import sys
import argparse
from datetime import datetime
from io import BytesIO
import requests
from PIL import Image

# Default configuration
DEFAULT_TARGET_WIDTH = 1920
DEFAULT_TARGET_HEIGHT = 1280  # 3:2 Ratio (1920 / (3/2) = 1280)
DEFAULT_OUTPUT_PATH = "/app/images/apod.jpg"

def validate_date(date_str):
    """Validates that the provided date string matches YYYY-MM-DD format."""
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return date_str
    except ValueError:
        raise argparse.ArgumentTypeError(f"Invalid date format: '{date_str}'. Must be YYYY-MM-DD.")

def fetch_apod_data(date=None):
    """Fetches APOD metadata and downloads the image from NASA's API.
    
    Returns:
        tuple: (PIL.Image, str, str, str) containing the image, title, explanation text, and date,
               or (None, None, None, None) on failure.
    """
    from datetime import timedelta
    api_key = os.environ.get("NASA_API_KEY", "DEMO_KEY")
    
    current_dt = None
    if date:
        try:
            current_dt = datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            pass

    attempts = 0
    while attempts < 10:
        url = f"https://api.nasa.gov/planetary/apod?api_key={api_key}"
        
        if current_dt:
            query_date = current_dt.strftime("%Y-%m-%d")
            url += f"&date={query_date}"
            print(f"Fetching metadata for date: {query_date}...")
        else:
            print("Fetching today's APOD metadata...")

        try:
            response = requests.get(url, timeout=15)
            response.raise_for_status()
            data = response.json()
        except Exception as e:
            print(f"[!] Error connecting to NASA API: {e}", file=sys.stderr)
            return None, None, None, None

        media_type = data.get("media_type")
        title = data.get("title", "Unknown Title")
        explanation = data.get("explanation", "")
        date_str = data.get("date", "")
        
        if media_type == "image":
            img_url = data.get("hdurl") or data.get("url")
            if img_url:
                print(f"Downloading image: {title} ({img_url})")
                try:
                    img_response = requests.get(img_url, timeout=30)
                    img_response.raise_for_status()
                    img = Image.open(BytesIO(img_response.content))
                    return img, title, explanation, date_str
                except Exception as e:
                    print(f"[!] Failed to download image: {e}", file=sys.stderr)
        
        print(f"[!] APOD for {date_str} is not a valid image (Type: {media_type}).", file=sys.stderr)
        
        # Fallback: go back 1 year from the actual date string we just checked
        try:
            base_dt = datetime.strptime(date_str, "%Y-%m-%d")
        except:
            base_dt = datetime.utcnow()
            
        current_dt = base_dt - timedelta(days=365) + timedelta(days=attempts)
        attempts += 1
        print(f"[*] Falling back to {current_dt.strftime('%Y-%m-%d')}...")

    print("[!] Exceeded max retry attempts.", file=sys.stderr)
    return None, None, None, None

def process_and_save(image, output_path, target_w=DEFAULT_TARGET_WIDTH, target_h=DEFAULT_TARGET_HEIGHT):
    """Resizes and center-crops the image to the target width and height, then saves it as JPEG."""
    try:
        original_width, original_height = image.size
        print(f"Original resolution: {original_width}x{original_height}")

        # Determine scaling factor to fill the target canvas
        ratio_w = target_w / original_width
        ratio_h = target_h / original_height
        scale_factor = max(ratio_w, ratio_h)

        # Scale image to match the largest required dimension
        new_width = int(original_width * scale_factor)
        new_height = int(original_height * scale_factor)
        
        print(f"Scaling to: {new_width}x{new_height}")
        resized_img = image.resize((new_width, new_height), Image.Resampling.LANCZOS)

        # Center-crop the image to exactly target_w x target_h
        left = (new_width - target_w) / 2
        top = (new_height - target_h) / 2
        right = (new_width + target_w) / 2
        bottom = (new_height + target_h) / 2

        print(f"Cropping region: left={left:.1f}, top={top:.1f}, right={right:.1f}, bottom={bottom:.1f}")
        cropped_img = resized_img.crop((left, top, right, bottom))

        # Convert to RGB mode if necessary and save
        if cropped_img.mode in ("RGBA", "P"):
            cropped_img = cropped_img.convert("RGB")

        # Create output directory if it doesn't exist
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            print(f"Creating output directory: {output_dir}")
            os.makedirs(output_dir, exist_ok=True)

        cropped_img.save(output_path, "JPEG", quality=90)
        print(f"[✓] Successfully saved APOD image to: {output_path} ({target_w}x{target_h} 3:2 aspect ratio)")
        return True
    except Exception as e:
        print(f"[!] Error processing or saving image: {e}", file=sys.stderr)
        return False

def main():
    import time
    json_path = os.path.join(os.path.dirname(__file__), "apod.json")
    if os.path.exists(json_path):
        mtime = os.path.getmtime(json_path)
        # Avoid redundant fetching if apod.json was updated within the last 12 hours
        if time.time() - mtime < 43200:
            print("APOD was successfully fetched within the last 12 hours. Skipping to conserve API limits.")
            sys.exit(0)
            
    parser = argparse.ArgumentParser(description="Fetch and crop NASA APOD image and explanation text.")
    parser.add_argument(
        "-d", "--date",
        type=validate_date,
        help="Specific date to fetch (format YYYY-MM-DD). Defaults to today."
    )
    parser.add_argument(
        "-o", "--output",
        default=DEFAULT_OUTPUT_PATH,
        help=f"Base path to save output image. The date will be appended to the filename. Defaults to {DEFAULT_OUTPUT_PATH}."
    )
    parser.add_argument(
        "-t", "--save-text",
        action="store_true",
        help="Also save the APOD text explanation to a matching .txt file."
    )
    
    args = parser.parse_args()

    raw_image, title, explanation, date_str = fetch_apod_data(args.date)
    if not raw_image or not date_str:
        sys.exit(1)

    # Append date to filename before saving
    base, ext = os.path.splitext(args.output)
    date_suffix = f"_{date_str}"
    if not base.endswith(date_suffix):
        output_image_path = f"{base}{date_suffix}{ext}"
    else:
        output_image_path = args.output

    print(f"Resolving output image path: {output_image_path}")

    # Process and save image
    success = process_and_save(raw_image, output_image_path)
    if not success:
        sys.exit(1)

    # Optionally save explanation text
    if args.save_text:
        if not explanation:
            print("[!] No explanation text available in metadata.", file=sys.stderr)
        else:
            txt_path = os.path.splitext(output_image_path)[0] + ".txt"
            try:
                # Ensure same directory exists (already handled by image save, but safe)
                txt_dir = os.path.dirname(txt_path)
                if txt_dir and not os.path.exists(txt_dir):
                    os.makedirs(txt_dir, exist_ok=True)
                
                with open(txt_path, "w", encoding="utf-8") as f:
                    f.write(explanation.strip() + "\n")
                print(f"[✓] Successfully saved APOD explanation to: {txt_path}")
            except Exception as e:
                print(f"[!] Error saving explanation text: {e}", file=sys.stderr)
                sys.exit(1)

    # Output a JSON summary file for the dashboard controller
    # We output this to the same directory as the script (or args.output's directory)
    try:
        import json
        json_path = os.path.join(os.path.dirname(__file__), "apod.json")
        # Extract relative filename (e.g. "apod_2026-07-15.jpg")
        img_filename = os.path.basename(output_image_path)
        payload = {
            "title": title,
            "url": f"./images/{img_filename}",
            "date": date_str
        }
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        print(f"[✓] Successfully saved apod.json summary to: {json_path}")
    except Exception as e:
        print(f"[!] Error saving apod.json: {e}", file=sys.stderr)

if __name__ == "__main__":
    main()
