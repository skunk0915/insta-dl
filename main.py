from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import yt_dlp
import os
import uuid
import shutil
import time
import requests
import logging
import traceback
import sys
import io

# Setup logging to file
LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app.log")
logging.basicConfig(filename=LOG_FILE, level=logging.DEBUG, 
                    format='%(asctime)s %(levelname)s: %(message)s')

def log_info(msg):
    logging.info(msg)
    print(msg, file=sys.stderr) # Also to server error log

# Create FastAPI app
app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOAD_DIR = os.path.join(BASE_DIR, "downloads")
if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

# API Endpoints
@app.post("/api/info")
@app.post("/insta-dl/api/info")
async def get_info(request: Request):
    try:
        data = await request.json()
        url = data.get("url")
        log_info(f"--- Info Start: {url} ---")
        
        ydl_opts = {
            'format': 'best',
            'quiet': True,
            'no_warnings': True,
            'cachedir': False,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            thumb_url = info.get("thumbnail")
            thumb_id = str(uuid.uuid4())
            local_thumb_name = f"thumb_{thumb_id}.jpg"
            local_thumb_path = os.path.join(DOWNLOAD_DIR, local_thumb_name)
            
            if thumb_url:
                try:
                    r = requests.get(thumb_url, stream=True, timeout=10)
                    if r.status_code == 200:
                        with open(local_thumb_path, 'wb') as f:
                            shutil.copyfileobj(r.raw, f)
                except:
                    local_thumb_name = None

            log_info(f"Info Success: {info.get('title')}")
            return {
                "title": info.get("title", "Instagram Video"),
                "thumbnail": f"api/file/{local_thumb_name}" if local_thumb_name else thumb_url
            }
    except Exception as e:
        log_info(f"Info Error: {traceback.format_exc()}")
        return JSONResponse(status_code=500, content={"detail": str(e)})

@app.post("/api/download")
@app.post("/insta-dl/api/download")
async def download_video(request: Request):
    # 重複出力を防ぐために標準出力をキャプチャ
    original_stdout = sys.stdout
    sys.stdout = io.StringIO()
    
    try:
        data = await request.json()
        url = data.get("url")
        log_info(f"--- Download Start: {url} ---")
        
        file_id = str(uuid.uuid4())
        output_template = os.path.join(DOWNLOAD_DIR, f"{file_id}.%(ext)s")
        
        # Don't merge video/audio as ffmpeg is missing
        ydl_opts = {
            'format': 'best',
            'outtmpl': output_template,
            'quiet': True,
            'no_warnings': True,
            'cachedir': False,
            'noplaylist': True,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            log_info("Executing yt-dlp...")
            info = ydl.extract_info(url, download=True)
            log_info("yt-dlp execution completed.")
            
            # Find the file
            actual_filename = None
            found_files = []
            for f in os.listdir(DOWNLOAD_DIR):
                if f.startswith(file_id):
                    actual_filename = os.path.join(DOWNLOAD_DIR, f)
                    found_files.append(f)
            
            log_info(f"Found files: {found_files}")
            
            if not actual_filename:
                log_info("ERROR: No file found after download")
                return JSONResponse(status_code=500, content={"detail": "Downloaded file not found on server."})

            file_size = os.path.getsize(actual_filename)
            log_info(f"Success! File: {actual_filename} ({file_size} bytes)")
            
            resp_data = {
                "file_id": file_id,
                "filename": os.path.basename(actual_filename),
                "title": info.get("title", "video")
            }
            log_info(f"Returning JSON: {resp_data}")
            return resp_data

    except Exception as e:
        log_info(f"Download Error: {traceback.format_exc()}")
        return JSONResponse(status_code=500, content={"detail": str(e)})
    finally:
        # 元の標準出力に戻す
        sys.stdout = original_stdout

@app.get("/api/file/{file_id}")
@app.get("/insta-dl/api/file/{file_id}")
async def get_file(file_id: str):
    for f in os.listdir(DOWNLOAD_DIR):
        if f.startswith(file_id):
            return FileResponse(os.path.join(DOWNLOAD_DIR, f))
    raise HTTPException(status_code=404)

@app.get("/")
@app.get("/insta-dl")
@app.get("/insta-dl/")
async def read_index():
    index_path = os.path.join(BASE_DIR, "static", "index.html")
    return FileResponse(index_path)

app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static_files")
app.mount("/", StaticFiles(directory=os.path.join(BASE_DIR, "static"), html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
