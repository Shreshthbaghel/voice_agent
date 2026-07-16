"""Emit MetricAI dashboard events for LiveKit STT/TTS.

LiveKit job processes do not inherit the worker MetricAI client. Always
init in-process before track(). Voice stays on direct Deepgram/Sarvam when
the staging proxy is broken; metering uses client-side track().
"""
from __future__ import annotations

import logging
from typing import Any

from config import get_settings

logger = logging.getLogger(__name__)
_recent: set[str] = set()


def _dedupe(key: str) -> bool:
    """Return True if this event was already tracked recently."""
    if key in _recent:
        return True
    _recent.add(key)
    if len(_recent) > 64:
        _recent.clear()
        _recent.add(key)
    return False


def _client() -> Any | None:
    """Ensure MetricAI is initialized in *this* process, then return the client."""
    try:
        from services.metricai_proxy import init_metricai

        init_metricai()
        from metricai.runtime import get_metricai

        return get_metricai()
    except Exception as e:
        logger.warning("MetricAI client unavailable for voice track: %s", e)
        return None


def track_stt(
    *,
    provider: str,
    model: str,
    text: str,
    language: str | None = None,
) -> None:
    """Record a speech-to-text turn on the MetricAI dashboard."""
    client = _client()
    if client is None:
        return
    settings = get_settings()
    cleaned = (text or "").strip()
    chars = len(cleaned)
    if not chars:
        return
    if _dedupe(f"stt:{provider}:{cleaned.lower()}"):
        return
    try:
        result = client.track(
            provider=provider,
            model=model,
            success=True,
            agent_id=settings.metricai_agent_id or "voice-medicine-assistant",
            user_id=settings.metricai_user_id or "voice-user",
            modalities={"audio_seconds": max(1.0, chars / 12.0), "text_tokens": max(1, chars // 4)},
            extra={
                "operation": "stt",
                "character_count": chars,
                "language": str(language or ""),
                "source": "livekit-agents",
            },
        )
        logger.info(
            "MetricAI track STT provider=%s model=%s chars=%d result=%s",
            provider,
            model,
            chars,
            result,
        )
    except Exception as e:
        logger.warning("MetricAI STT track failed: %s", e)


def track_tts(
    *,
    provider: str,
    model: str,
    text: str,
) -> None:
    """Record a text-to-speech turn on the MetricAI dashboard."""
    client = _client()
    if client is None:
        return
    settings = get_settings()
    cleaned = (text or "").strip()
    chars = len(cleaned)
    if not chars:
        return
    if _dedupe(f"tts:{provider}:{cleaned.lower()[:200]}"):
        return
    try:
        result = client.track(
            provider=provider,
            model=model,
            success=True,
            agent_id=settings.metricai_agent_id or "voice-medicine-assistant",
            user_id=settings.metricai_user_id or "voice-user",
            modalities={"audio_seconds": max(1.0, chars / 12.0), "text_tokens": max(1, chars // 4)},
            extra={
                "operation": "tts",
                "character_count": chars,
                "source": "livekit-agents",
            },
        )
        logger.info(
            "MetricAI track TTS provider=%s model=%s chars=%d result=%s",
            provider,
            model,
            chars,
            result,
        )
    except Exception as e:
        logger.warning("MetricAI TTS track failed: %s", e)
