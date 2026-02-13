#!/usr/bin/env python3
import os
import time
import sys

# Change directory to the script's directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))

DOWNLOAD_DIR = "downloads"

def cleanup_old_files():
    if not os.path.exists(DOWNLOAD_DIR):
        print("Download directory does not exist.")
        return

    now = time.time()
    count = 0
    try:
        for f in os.listdir(DOWNLOAD_DIR):
            path = os.path.join(DOWNLOAD_DIR, f)
            # Remove files older than 1 hour (3600 seconds)
            if os.path.getmtime(path) < now - 3600:
                if os.path.isfile(path):
                    try:
                        os.remove(path)
                        count += 1
                        print(f"Removed: {f}")
                    except Exception as e:
                        print(f"Failed to remove {f}: {e}")
    except Exception as e:
        print(f"Error during cleanup: {e}")
    
    if count > 0:
        print(f"Cleanup complete. Removed {count} files.")
    else:
        print("No old files found for cleanup.")

if __name__ == "__main__":
    cleanup_old_files()
