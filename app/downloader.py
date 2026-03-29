def get_direct_download_url(url: str) -> dict:
    """
    Gets direct media URL without saving to disk.
    Used for streaming directly to user.
    """
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "format": "bestvideo+bestaudio/best",
        "skip_download": True,  # Don't download, just get URL
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        return {
            "url": info.get("url") or info["requested_formats"][0]["url"],
            "ext": info.get("ext", "mp4"),
            "title": info.get("title", "video"),
        }