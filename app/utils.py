import os
import re
import hashlib
from pathlib import Path
from fastapi import HTTPException, Header
from dotenv import load_dotenv

load_dotenv()

API_SECRET_KEY = os.getenv("API_SECRET_KEY", "")


def verify_api_key(x_api_key: str = Header(default="")):
    """Simple API key protection. Pass X-Api-Key header."""
    if API_SECRET_KEY and x_api_key != API_SECRET_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key.")


def clean_instagram_url(url: str) -> str:
    """Remove tracking params, normalize URL."""
    url = url.strip()
    # Remove query params (utm_source, igsh, etc.)
    url = re.sub(r"\?.*$", "", url)
    # Remove trailing slash
    url = url.rstrip("/")
    # Ensure https
    if url.startswith("http://"):
        url = "https://" + url[7:]
    return url


def get_file_size_mb(filepath: str) -> float:
    """Returns file size in MB."""
    size_bytes = Path(filepath).stat().st_size
    return round(size_bytes / (1024 * 1024), 2)