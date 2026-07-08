import sys
import glob

try:
    from astropy.io import fits
    from PIL import Image
    import numpy as np
except ImportError:
    print("Required modules not found. Need astropy, Pillow, and numpy.")
    sys.exit(1)

def convert(fits_path, out_path):
    print(f"Converting {fits_path} to {out_path}...")
    try:
        with fits.open(fits_path) as hdul:
            data = hdul[0].data
            if data is None and len(hdul) > 1:
                data = hdul[1].data
            
            if data is None:
                print(f"No image data found in {fits_path}")
                return

            # Basic auto-stretch (percentile) to make nebulas/stars visible
            p_lo = np.percentile(data, 5)
            p_hi = np.percentile(data, 99.5)
            # Avoid division by zero
            if p_hi == p_lo:
                p_hi = p_lo + 1
                
            data = np.clip(data, p_lo, p_hi)
            data = (data - p_lo) / (p_hi - p_lo)
            data = (data * 255).astype(np.uint8)
            
            # Handle potential 3D arrays
            if data.ndim == 3:
                if data.shape[0] == 3: 
                    data = np.moveaxis(data, 0, -1) # convert (C,H,W) to (H,W,C)
            
            img = Image.fromarray(data)
            img.save(out_path)
            print(f"Successfully saved {out_path}")
    except Exception as e:
        print(f"Failed to convert {fits_path}: {e}")

# Find the files (using glob in case of weird spacing)
q75_files = glob.glob("75Q*.fits")
fra_files = glob.glob("FRA400*.fits")

if q75_files:
    convert(q75_files[0], "75Q.jpg")
else:
    print("75Q fits file not found.")

if fra_files:
    convert(fra_files[0], "FRA400.jpg")
else:
    print("FRA400 fits file not found.")
