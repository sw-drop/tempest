import os
import io
import time
import logging
import pathlib
import json
import shutil
from PIL import Image
import numpy as np
from astropy.io import fits

logger = logging.getLogger("tempest_image_watcher")

class ImageWatcher:
    def __init__(self, config):
        self.config = config
        self.running = False
        self.last_files = {
            "fra400": None,
            "75q": None
        }
        self.metadata = {
            "fra400": {"target": "FRA400", "filename": "Waiting for images..."},
            "75q": {"target": "75Q", "filename": "Waiting for images..."}
        }
        
    def start(self):
        self.running = True
        logger.info("Image Watcher initialized.")

    def run_once(self):
        """Scans for new FITS files and updates JPEGs + metadata.json."""
        scopes = {
            "fra400": "FRA400",
            "75q": "75Q"
        }
        metadata_changed = False
        
        for safe_scope, scope_dir in scopes.items():
            img_dir = f"/app/images/{scope_dir}"
            
            # Local fallback for testing outside container
            if not os.path.exists(img_dir):
                img_dir = f"./app/images/{scope_dir}"
                if not os.path.exists(img_dir):
                    img_dir = "."
                    
            p = pathlib.Path(img_dir)
            fits_files = list(p.rglob("*.fit*"))
            
            # Filter out temporary Syncthing assets
            fits_files = [
                str(f) for f in fits_files 
                if f.is_file() and not f.name.startswith('.syncthing') and not f.name.endswith('.tmp')
            ]
            
            # Special filter for local fallback testing
            if not fits_files and img_dir == ".":
                fits_files = [
                    str(f) for f in p.rglob(f"*{scope_dir}*.fit*") 
                    if f.is_file() and not f.name.startswith('.syncthing') and not f.name.endswith('.tmp')
                ]

            if not fits_files:
                # Copy baseline fallback JPEGs if present and not already copied
                fallback_src = f"/app/{scope_dir}.jpg" if os.path.exists(f"/app/{scope_dir}.jpg") else f"./{scope_dir}.jpg"
                fallback_dest = os.path.join(self.config.STATIC_DIR, f"{safe_scope}.jpg")
                if os.path.exists(fallback_src) and not os.path.exists(fallback_dest):
                    try:
                        shutil.copy(fallback_src, fallback_dest)
                        logger.info(f"Copied fallback image {fallback_src} to {fallback_dest}")
                        self.metadata[safe_scope] = {
                            "target": f"{scope_dir} - Target Name",
                            "filename": "No active images synced yet."
                        }
                        metadata_changed = True
                    except Exception as copy_err:
                        logger.error(f"Failed to copy fallback image: {copy_err}")
                continue

            # Find latest FITS file by mtime
            latest_file = max(fits_files, key=os.path.getmtime)
            
            # Process if the latest file is different
            if latest_file != self.last_files[safe_scope]:
                logger.info(f"New FITS detected for {safe_scope}: {latest_file}")
                
                success = self._convert_fits_to_jpeg_atomic(latest_file, safe_scope)
                if success:
                    self.last_files[safe_scope] = latest_file
                    
                    # Parse target name and base filename
                    filename = os.path.splitext(os.path.basename(latest_file))[0]
                    target_name = ""
                    try:
                        # Extract target from directories: .../images/<scope>/<profile>/<target>/<date>/<file>
                        rel_path = pathlib.Path(latest_file).relative_to(img_dir)
                        parts = rel_path.parts
                        if len(parts) >= 3:
                            target_name = parts[1]
                    except Exception as parse_err:
                        logger.error(f"Failed to parse target path: {parse_err}")
                        
                    self.metadata[safe_scope] = {
                        "target": f"{scope_dir} - {target_name}" if target_name else scope_dir,
                        "filename": filename
                    }
                    metadata_changed = True

        if metadata_changed:
            self._write_metadata_atomic()

    def _convert_fits_to_jpeg_atomic(self, fits_path, safe_scope):
        try:
            with fits.open(fits_path) as hdul:
                data = hdul[0].data
                if data is None and len(hdul) > 1:
                    data = hdul[1].data
                if data is None:
                    logger.error(f"No FITS array data in {fits_path}")
                    return False

                p_lo = np.percentile(data, 5)
                p_hi = np.percentile(data, 99.5)
                if p_hi == p_lo:
                    p_hi = p_lo + 1
                data = np.clip(data, p_lo, p_hi)
                data = (data - p_lo) / (p_hi - p_lo)
                data = (data * 255).astype(np.uint8)
                
                if data.ndim == 3 and data.shape[0] == 3: 
                    data = np.moveaxis(data, 0, -1)
                
                img = Image.fromarray(data)
                
                # Write atomically to file system
                temp_path = os.path.join(self.config.STATIC_DIR, f"{safe_scope}.jpg.tmp")
                final_path = os.path.join(self.config.STATIC_DIR, f"{safe_scope}.jpg")
                img.save(temp_path, 'JPEG', quality=85)
                os.replace(temp_path, final_path)
                logger.info(f"Successfully converted and wrote FITS to {final_path}")
                return True
        except Exception as e:
            logger.error(f"Failed FITS conversion for {fits_path}: {e}")
            return False

    def _write_metadata_atomic(self):
        temp_path = os.path.join(self.config.STATIC_DIR, "images.json.tmp")
        final_path = os.path.join(self.config.STATIC_DIR, "images.json")
        try:
            with open(temp_path, "w") as f:
                json.dump(self.metadata, f)
            os.replace(temp_path, final_path)
            logger.info(f"Successfully wrote images.json metadata to {final_path}")
        except Exception as e:
            logger.error(f"Failed to write images.json: {e}")
