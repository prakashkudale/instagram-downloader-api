import logging
import os
import httpx
import yt_dlp
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, field_validator
from dotenv import load_dotenv

from app.detector import detect_instagram_url_type
from app.downloader import download_reel_or_post, download_story, download_highlight
from app.utils import verify_api_key, clean_instagram_url, get_file_size_mb

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Instagram Media Downloader API",
    description="Download Reels, Posts, Stories, Highlights in HD quality.",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class DownloadRequest(BaseModel):
    url: str

    @field_validator("url")
    @classmethod
    def must_be_instagram(cls, v):
        if "instagram.com" not in v:
            raise ValueError("URL must be from instagram.com")
        return v


class DownloadResponse(BaseModel):
    success: bool
    url_type: str
    files: list[str]
    file_sizes_mb: list[float]
    message: str


@app.get("/", tags=["Health"])
def root():
    return {"status": "Instagram Downloader API is running!"}


@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok", "version": "2.0.0"}


@app.post("/download", tags=["Download"], dependencies=[Depends(verify_api_key)])
async def download_media(request: DownloadRequest):
    """
    Downloads media and saves locally.
    Returns file paths.
    """
    url = clean_instagram_url(request.url)
    url_type = detect_instagram_url_type(url)
    logger.info(f"Download request | type={url_type} | url={url}")

    try:
        if url_type in ("reel", "post", "tv"):
            result = download_reel_or_post(url)
        elif url_type == "story":
            result = download_story(url)
        elif url_type == "highlight":
            result = download_highlight(url)
        elif url_type == "unknown":
            raise HTTPException(
                status_code=400,
                detail="Could not detect URL type. Supported: Reel, Post, Story, Highlight, IGTV."
            )
        else:
            raise HTTPException(
                status_code=400,
                detail=f"URL type '{url_type}' is not supported."
            )

        file_sizes = []
        for f in result["files"]:
            try:
                file_sizes.append(get_file_size_mb(f))
            except Exception:
                file_sizes.append(0.0)

        return {
            "success": True,
            "url_type": result["type"],
            "files": result["files"],
            "file_sizes_mb": file_sizes,
            "message": result["message"]
        }

    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except RuntimeError as e:
        logger.error(f"Download error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred.")


@app.post("/stream", tags=["Stream"], dependencies=[Depends(verify_api_key)])
async def stream_media(request: DownloadRequest):
    """
    Gets direct streaming URL without saving to disk.
    Best for production/cloud deployment.
    """
    url = clean_instagram_url(request.url)
    url_type = detect_instagram_url_type(url)
    logger.info(f"Stream request | type={url_type} | url={url}")

    try:
        if url_type not in ("reel", "post", "tv"):
            raise HTTPException(
                status_code=400,
                detail="Streaming only supports Reels, Posts, and IGTV."
            )

        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "format": "best",
            "skip_download": True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            direct_url = info.get("url")
            ext = info.get("ext", "mp4")
            title = info.get("title", "instagram_video")

            if not direct_url:
                raise HTTPException(status_code=500, detail="Could not extract direct media URL.")

            return {
                "success": True,
                "url_type": url_type,
                "direct_url": direct_url,
                "filename": f"{title}.{ext}",
                "message": "Use direct_url to stream or download the media."
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Stream error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/file", tags=["Files"], dependencies=[Depends(verify_api_key)])
def serve_file(path: str):
    """Serve a locally downloaded file."""
    from pathlib import Path
    file = Path(path)
    if not file.exists():
        raise HTTPException(status_code=404, detail="File not found.")
    if not str(file.resolve()).startswith(str(Path("./downloads").resolve())):
        raise HTTPException(status_code=403, detail="Access denied.")
    from fastapi.responses import FileResponse
    return FileResponse(
        path=str(file),
        media_type="application/octet-stream",
        filename=file.name
    )