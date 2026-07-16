"""MetricAI cloud proxy setup for OpenAI + LiveKit Deepgram/Sarvam voice."""
from __future__ import annotations

import logging
from typing import Any

import aiohttp
from multidict import CIMultiDict, CIMultiDictProxy

from config import get_settings

logger = logging.getLogger(__name__)
_initialized = False


def init_metricai(*, force: bool = False) -> None:
    """Initialize MetricAI once per process (API + agent worker + job subprocess)."""
    global _initialized
    if force:
        # Prefer reuse if this job process already has a live client
        try:
            from metricai.runtime import get_metricai

            get_metricai()
            _initialized = True
            return
        except Exception:
            _initialized = False

    if _initialized:
        try:
            from metricai.runtime import get_metricai

            get_metricai()
            return
        except Exception:
            _initialized = False

    # Pick up .env edits made after process import
    get_settings.cache_clear()
    settings = get_settings()
    api_key = (settings.metricai_api_key or "").strip()
    if not api_key:
        logger.warning("METRICAI_API_KEY not set — provider calls will bypass MetricAI proxy")
        return

    try:
        import metricai
    except ImportError:
        logger.error("metricai package not installed — pip install metricai")
        return

    llm_keys: dict[str, str] = {}
    if settings.openai_api_key:
        llm_keys["openai"] = settings.openai_api_key

    kwargs: dict[str, Any] = {
        "api_key": api_key,
        "mode": "cloud",
        # LiveKit uses its own Deepgram/Sarvam plugins (not deepgram-sdk / sarvamai).
        # We also manually route OpenAI because MetricAI's auto_instrument currently
        # fails to patch `AsyncOpenAI` (which LiveKit requires), only patching `OpenAI`.
        "auto_instrument": False,
        "active_providers": ("openai",),
        "default_agent_id": settings.metricai_agent_id,
        "default_user_id": settings.metricai_user_id,
        "llm_keys": llm_keys or None,
    }
    proxy_url = (settings.metricai_proxy_url or settings.metricai_base_url or "").strip()
    if proxy_url:
        kwargs["backend_endpoint"] = proxy_url

    metricai.init(**kwargs)
    _initialized = True
    logger.info(
        "MetricAI proxy initialized (endpoint=%s, providers=%s)",
        proxy_url or "https://proxy.metricai.co.in",
        ", ".join(sorted(llm_keys)) or "none",
    )


def proxy_base() -> str:
    settings = get_settings()
    return (settings.metricai_proxy_url or settings.metricai_base_url or "https://proxy.metricai.co.in").rstrip("/")


def provider_proxy_root(provider: str) -> str:
    return f"{proxy_base()}/v1/proxy/{provider}"


def deepgram_listen_url() -> str:
    return f"{provider_proxy_root('deepgram')}/v1/listen"


def deepgram_speak_url() -> str:
    return f"{provider_proxy_root('deepgram')}/v1/speak"


def sarvam_stt_rest_url() -> str:
    return f"{provider_proxy_root('sarvam')}/speech-to-text"


def sarvam_stt_ws_url() -> str:
    root = provider_proxy_root("sarvam").replace("https://", "wss://").replace("http://", "ws://")
    return f"{root}/speech-to-text/ws"


def sarvam_tts_rest_url() -> str:
    return f"{provider_proxy_root('sarvam')}/text-to-speech"


def sarvam_tts_ws_url() -> str:
    root = provider_proxy_root("sarvam").replace("https://", "wss://").replace("http://", "ws://")
    return f"{root}/text-to-speech/ws"


def openai_proxy_base_url() -> str:
    return provider_proxy_root("openai")


def _attribution_headers(*, byok_header: str | None = None, byok_value: str | None = None) -> dict[str, str]:
    settings = get_settings()
    metricai_key = (settings.metricai_api_key or "").strip()
    headers: dict[str, str] = {
        "X-Agent-ID": settings.metricai_agent_id or "voice-medicine-assistant",
        "X-User-ID": settings.metricai_user_id or "voice-user",
        "X-Billing-Mode": "hybrid",
    }
    if metricai_key:
        headers["Authorization"] = f"Bearer {metricai_key}"
        headers["X-MetricAI-API-Key"] = metricai_key
    if byok_header and byok_value:
        headers[byok_header] = byok_value
    return headers


class _BearerRewriteSession(aiohttp.ClientSession):
    """LiveKit Deepgram sets Authorization: Token <key>; MetricAI needs Bearer."""

    def __init__(self, *args: Any, bearer_token: str, **kwargs: Any) -> None:
        self._bearer_token = bearer_token
        super().__init__(*args, **kwargs)

    async def _request(self, method: str, url: Any, **kwargs: Any) -> Any:
        headers = kwargs.get("headers")
        if headers is not None:
            if isinstance(headers, (CIMultiDict, CIMultiDictProxy)):
                merged = CIMultiDict(headers)
            else:
                merged = CIMultiDict(headers)
            auth = merged.get("Authorization", "")
            if isinstance(auth, str) and auth.lower().startswith("token "):
                merged["Authorization"] = f"Bearer {self._bearer_token}"
            kwargs["headers"] = merged
        return await super()._request(method, url, **kwargs)


def make_deepgram_http_session() -> aiohttp.ClientSession:
    """Must be created inside a running asyncio loop (agent job)."""
    settings = get_settings()
    ma_key = (settings.metricai_api_key or "").strip()
    return _BearerRewriteSession(
        bearer_token=ma_key,
        headers=_attribution_headers(
            byok_header="X-Deepgram-API-Key",
            byok_value=settings.deepgram_api_key or None,
        ),
    )


def make_sarvam_http_session() -> aiohttp.ClientSession:
    """Must be created inside a running asyncio loop (agent job)."""
    settings = get_settings()
    return aiohttp.ClientSession(
        headers=_attribution_headers(
            byok_header="X-Sarvam-API-Key",
            byok_value=settings.sarvam_api_key or None,
        )
    )


def openai_extra_headers() -> dict[str, str]:
    settings = get_settings()
    return _attribution_headers(
        byok_header="X-OpenAI-API-Key",
        byok_value=settings.openai_api_key or None,
    )


def metricai_api_key() -> str:
    return (get_settings().metricai_api_key or "").strip()
