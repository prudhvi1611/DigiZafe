"""Groq client via httpx (free). Never required for core path."""
from __future__ import annotations

import httpx

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class GroqError(Exception):
    pass


async def groq_available() -> bool:
    settings = get_settings()
    if not settings.narrative_enabled or not settings.groq_api_key:
        return False
    return True


async def groq_chat(
    *,
    system: str,
    user: str,
    model: str | None = None,
) -> str:
    settings = get_settings()
    if not settings.groq_api_key:
        raise GroqError("No GROQ_API_KEY provided")
        
    model = model or settings.groq_model
    url = "https://api.groq.com/openai/v1/chat/completions"
    
    payload = {
        "model": model,
        "temperature": settings.narrative_temperature,
        "max_tokens": settings.narrative_max_tokens,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }
    
    headers = {
        "Authorization": f"Bearer {settings.groq_api_key}",
        "Content-Type": "application/json"
    }
    
    try:
        async with httpx.AsyncClient(timeout=settings.narrative_timeout_seconds) as client:
            r = await client.post(url, json=payload, headers=headers)
            if r.status_code != 200:
                raise GroqError(f"HTTP {r.status_code}: {r.text[:300]}")
            data = r.json()
            choices = data.get("choices", [])
            if not choices:
                raise GroqError("Empty Groq response")
                
            msg = choices[0].get("message", {}).get("content", "")
            if not msg.strip():
                raise GroqError("Empty message content")
            return msg.strip()
    except GroqError:
        raise
    except Exception as e:
        logger.warning("groq_chat_failed", error=str(e))
        raise GroqError(str(e)) from e
