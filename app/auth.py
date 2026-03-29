import os
import json
import logging
from pathlib import Path
from instagrapi import Client
from instagrapi.exceptions import LoginRequired, TwoFactorRequired, BadPassword

logger = logging.getLogger(__name__)

SESSION_FILE = "session.json"
from typing import Optional
_client: Optional[Client] = None


def get_client():
    """Returns authenticated instagrapi Client. Reuses session if possible."""
    global _client

    if _client is not None:
        return _client

    username = os.getenv("IG_USERNAME")
    password = os.getenv("IG_PASSWORD")

    if not username or not password:
        raise ValueError("IG_USERNAME and IG_PASSWORD must be set in .env")

    cl = Client()
    cl.delay_range = [1, 3]  # human-like delays to avoid bans

    # Try to reuse existing session
    if Path(SESSION_FILE).exists():
        try:
            cl.load_settings(SESSION_FILE)
            cl.login(username, password)
            logger.info("✅ Logged in using saved session")
            _client = cl
            return _client
        except (LoginRequired, Exception) as e:
            logger.warning(f"Session expired, re-logging: {e}")
            Path(SESSION_FILE).unlink(missing_ok=True)

    # Fresh login
    try:
        cl.login(username, password)
        cl.dump_settings(SESSION_FILE)
        logger.info("✅ Fresh login successful, session saved")
        _client = cl
        return _client

    except TwoFactorRequired:
        raise RuntimeError(
            "2FA is enabled on your spare account. Disable it or handle 2FA manually."
        )
    except BadPassword:
        raise RuntimeError("Wrong Instagram password. Check your .env file.")
    except Exception as e:
        raise RuntimeError(f"Instagram login failed: {e}")


def reset_client():
    """Force re-login on next request"""
    global _client
    _client = None