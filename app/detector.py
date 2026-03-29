import re

def detect_instagram_url_type(url: str) -> str:
    """
    Detects what type of Instagram content the URL points to.
    Returns: 'reel', 'post', 'story', 'tv', 'highlight', 'profile', or 'unknown'
    """
    url = url.strip().lower()

    patterns = {
        "reel":      r"instagram\.com/(reels?|reel)/[\w\-]+",
        "story":     r"instagram\.com/stories/[\w\.]+/\d+",
        "highlight": r"instagram\.com/stories/highlights/\d+",
        "tv":        r"instagram\.com/tv/[\w\-]+",
        "post":      r"instagram\.com/p/[\w\-]+",
        "profile":   r"instagram\.com/[\w\.]+/?$",
    }

    for content_type, pattern in patterns.items():
        if re.search(pattern, url):
            return content_type

    return "unknown"


def extract_shortcode(url: str):
    """Extract shortcode/ID from Instagram URLs like /p/ABC123/ or /reel/ABC123/"""
    match = re.search(r"instagram\.com/(?:p|reel|reels?|tv)/([\w\-]+)", url)
    return match.group(1) if match else None


def extract_story_info(url: str) -> dict | None:
    """Extract username and story ID from story URLs"""
    match = re.search(r"instagram\.com/stories/([\w\.]+)/(\d+)", url)
    if match:
        return {"username": match.group(1), "story_id": int(match.group(2))}
    return None


def extract_highlight_id(url: str) -> str | None:
    """Extract highlight ID"""
    match = re.search(r"instagram\.com/stories/highlights/(\d+)", url)
    return match.group(1) if match else None