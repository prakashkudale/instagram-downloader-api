import os
import logging
import yt_dlp
import requests
from pathlib import Path

from app.auth import get_client, reset_client
from app.detector import extract_shortcode, extract_story_info, extract_highlight_id

logger = logging.getLogger(__name__)
DOWNLOAD_DIR = Path(os.getenv("DOWNLOAD_DIR", "./downloads"))
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)


def _yt_dlp_download(url: str, output_path: Path) -> Path:
    ydl_opts = {
        "outtmpl": str(output_path / "%(id)s.%(ext)s"),
        "format": "mp4",  # ⚡ faster, avoids merging
        "cookiefile": "/home/Delta/cookies.txt",  # ✅ IMPORTANT
        "quiet": True,
        "no_warnings": True,
        "ignoreerrors": False,
        "http_headers": {
            "User-Agent": (
                "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
                "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
            )
        },
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
        if not filename.endswith(".mp4"):
        filename = filename.rsplit(".", 1)[0] + ".mp4"
        return Path(filename)


def _download_file_from_url(media_url: str, dest_path: Path) -> Path:
    headers = {"User-Agent": "Instagram 219.0.0.12.117 Android"}
    response = requests.get(media_url, headers=headers, stream=True, timeout=30)
    response.raise_for_status()
    with open(dest_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    return dest_path


def download_reel_or_post(url: str) -> dict:
    shortcode = extract_shortcode(url)
    save_dir = DOWNLOAD_DIR / (shortcode or "post")
    save_dir.mkdir(parents=True, exist_ok=True)
    try:
        file_path = _yt_dlp_download(url, save_dir)
        return {
            "success": True,
            "type": "reel_or_post",
            "files": [str(file_path)],
            "message": "Downloaded successfully"
        }
    except yt_dlp.utils.DownloadError as e:
        error_msg = str(e)
        if "Private" in error_msg or "Login" in error_msg:
            raise ValueError("This account is private.")
        raise RuntimeError(f"yt-dlp download failed: {error_msg}")


def download_story(url: str) -> dict:
    info = extract_story_info(url)
    if not info:
        raise ValueError("Could not parse story URL.")

    username = info["username"]
    story_id = info["story_id"]

    try:
        cl = get_client()
        user_id = cl.user_id_from_username(username)
        stories = cl.user_stories(user_id)
        target_story = next((s for s in stories if s.pk == story_id), None)

        if not target_story:
            raise ValueError(f"Story ID {story_id} not found or expired.")

        save_dir = DOWNLOAD_DIR / f"story_{story_id}"
        save_dir.mkdir(parents=True, exist_ok=True)

        if target_story.media_type == 1:
            ext = "jpg"
            media_url = str(target_story.thumbnail_url)
        else:
            ext = "mp4"
            media_url = str(target_story.video_url)

        dest = save_dir / f"{story_id}.{ext}"
        _download_file_from_url(media_url, dest)

        return {
            "success": True,
            "type": "story",
            "files": [str(dest)],
            "message": "Story downloaded successfully"
        }

    except Exception as e:
        reset_client()
        raise RuntimeError(f"Story download failed: {e}")


def download_highlight(url: str) -> dict:
    highlight_id = extract_highlight_id(url)
    if not highlight_id:
        raise ValueError("Could not parse highlight URL.")

    try:
        cl = get_client()
        highlights = cl.highlight_info(highlight_id)
        items = highlights.items

        if not items:
            raise ValueError("Highlight is empty or private.")

        save_dir = DOWNLOAD_DIR / f"highlight_{highlight_id}"
        save_dir.mkdir(parents=True, exist_ok=True)

        saved_files = []
        for item in items:
            if item.media_type == 1:
                ext = "jpg"
                media_url = str(item.thumbnail_url)
            else:
                ext = "mp4"
                media_url = str(item.video_url)

            dest = save_dir / f"{item.pk}.{ext}"
            _download_file_from_url(media_url, dest)
            saved_files.append(str(dest))

        return {
            "success": True,
            "type": "highlight",
            "files": saved_files,
            "count": len(saved_files),
            "message": f"Downloaded {len(saved_files)} highlight items"
        }

    except Exception as e:
        reset_client()
        raise RuntimeError(f"Highlight download failed: {e}")