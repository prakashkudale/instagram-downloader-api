import logging
import os
from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, field_validator
from dotenv import load_dotenv

from app.detector import detect_instagram_url_type
from app.downloader import download_reel_or_post, download_story, download_highlight
from app.utils import verify_api_key, clean_instagram_url, get_file_size_mb

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(
    title="📸 Instagram Media Downloader API",
    description="Download Reels, Posts, Stories, Highlights in HD quality.",
    version="1.0.0"
)


# ─────────────────────────────────────────
# REQUEST / RESPONSE MODELS
# ─────────────────────────────────────────

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


# ─────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────

@app.get("/", tags=["Health"])
def root():
    return {"status": "✅ Instagram Downloader API is running!"}


@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok", "version": "1.0.0"}


@app.post("/download", response_model=DownloadResponse, tags=["Download"],
          dependencies=[Depends(verify_api_key)])
async def download_media(request: DownloadRequest):
    """
    Main endpoint. Send any Instagram URL and get the downloaded file paths.
    
    Supports:
    - Reels: instagram.com/reels/ABC123/
    - Posts: instagram.com/p/ABC123/
    - Stories: instagram.com/stories/username/123456/
    - Highlights: instagram.com/stories/highlights/123456/
    - IGTV: instagram.com/tv/ABC123/
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
                detail=(
                    "Could not detect URL type. Supported types: "
                    "Reel, Post, Story, Highlight, IGTV. "
                    "Make sure you paste the full Instagram URL."
                )
            )
        else:
            raise HTTPException(
                status_code=400,
                detail=f"URL type '{url_type}' is not supported for download."
            )

        file_sizes = [get_file_size_mb(f) for f in result["files"]]

        return DownloadResponse(
            success=True,
            url_type=result["type"],
            files=result["files"],
            file_sizes_mb=file_sizes,
            message=result["message"]
        )

    except ValueError as e:
        # Known user errors (private account, wrong URL, expired story)
        raise HTTPException(status_code=422, detail=str(e))

    except RuntimeError as e:
        # Download engine errors
        logger.error(f"Download error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred.")


@app.get("/file", tags=["Download"], dependencies=[Depends(verify_api_key)])
def serve_file(path: str):
    """
    Serve a downloaded file directly for preview/download.
    Pass the file path from /download response.
    """
    from pathlib import Path
    file = Path(path)
    if not file.exists():
        raise HTTPException(status_code=404, detail="File not found.")
    if not str(file.resolve()).startswith(str(Path("./downloads").resolve())):
        raise HTTPException(status_code=403, detail="Access denied.")

    return FileResponse(
        path=str(file),
        media_type="application/octet-stream",
        filename=file.name
    )