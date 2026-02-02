from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import yt_dlp
import os
import uuid
import shutil
import time
from threading import Thread

app = FastAPI()

# Background cleanup thread
def cleanup_old_files():
    while True:
        try:
            now = time.time()
            for f in os.listdir(DOWNLOAD_DIR):
                path = os.path.join(DOWNLOAD_DIR, f)
                # Remove files older than 1 hour
                if os.path.getmtime(path) < now - 3600:
                    if os.path.isfile(path):
                        os.remove(path)
        except Exception:
            pass
        time.sleep(600) # Run every 10 mins

Thread(target=cleanup_old_files, daemon=True).start()

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DOWNLOAD_DIR = "downloads"
if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

import requests

@app.post("/api/info")
async def get_info(request: Request):
    data = await request.json()
    url = data.get("url")
    if not url:
        raise HTTPException(status_code=400, detail="URL is required")

    ydl_opts = {
        'format': 'best',
        'quiet': True,
        'no_warnings': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            thumb_url = info.get("thumbnail")
            thumb_id = str(uuid.uuid4())
            local_thumb_name = f"thumb_{thumb_id}.jpg"
            local_thumb_path = os.path.join(DOWNLOAD_DIR, local_thumb_name)
            
            # Download thumbnail locally
            if thumb_url:
                try:
                    r = requests.get(thumb_url, stream=True, timeout=10)
                    if r.status_code == 200:
                        with open(local_thumb_path, 'wb') as f:
                            shutil.copyfileobj(r.raw, f)
                    else:
                        local_thumb_name = None
                except Exception:
                    local_thumb_name = None

            return {
                "title": info.get("title", "Instagram Video"),
                "thumbnail": f"/api/file/{local_thumb_name}" if local_thumb_name else thumb_url,
                "duration": info.get("duration"),
                "url": info.get("url"),
                "ext": info.get("ext", "mp4")
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/download")
async def download_video(request: Request):
    data = await request.json()
    url = data.get("url")
    if not url:
        raise HTTPException(status_code=400, detail="URL is required")

    file_id = str(uuid.uuid4())
    output_template = os.path.join(DOWNLOAD_DIR, f"{file_id}.%(ext)s")

    ydl_opts = {
        'format': 'best',
        'outtmpl': output_template,
        'quiet': True,
        'no_warnings': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            # Find the actual file (yt-dlp might change extension)
            actual_filename = None
            for f in os.listdir(DOWNLOAD_DIR):
                if f.startswith(file_id):
                    actual_filename = os.path.join(DOWNLOAD_DIR, f)
                    break
            
            if not actual_filename:
                raise HTTPException(status_code=500, detail="Failed to download file")

            return JSONResponse({
                "file_id": file_id,
                "filename": os.path.basename(actual_filename),
                "title": info.get("title", "video")
            })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/file/{file_id}")
async def get_file(file_id: str):
    actual_filename = None
    for f in os.listdir(DOWNLOAD_DIR):
        if f.startswith(file_id):
            actual_filename = os.path.join(DOWNLOAD_DIR, f)
            break
    
    if not actual_filename:
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(actual_filename, media_type='application/octet-stream', filename=os.path.basename(actual_filename))

# Serve frontend static files
app.mount("/", StaticFiles(directory="static", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
