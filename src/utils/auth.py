"""API key authentication for write endpoints."""
from fastapi import Header, HTTPException

from src.config import settings


def require_api_key(x_api_key: str = Header(default="", alias="X-API-Key")) -> str:
    """Validate API key. If no key configured on server, allow all requests."""
    if not settings.reelbot_api_key:
        return ""  # No key configured — allow (dev mode)
    if x_api_key != settings.reelbot_api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return x_api_key
