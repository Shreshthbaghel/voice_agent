"""Voice providers — Deepgram and Sarvam STT+TTS pairs (optionally via MetricAI proxy)."""
from __future__ import annotations

import logging

import aiohttp
from livekit.plugins import deepgram, openai, sarvam, elevenlabs

from config import get_settings
from services.metricai_proxy import (
    deepgram_listen_url,
    deepgram_speak_url,
    make_deepgram_http_session,
    make_sarvam_http_session,
    metricai_api_key,
    openai_extra_headers,
    openai_proxy_base_url,
    sarvam_stt_rest_url,
    sarvam_stt_ws_url,
    sarvam_tts_rest_url,
    sarvam_tts_ws_url,
)

logger = logging.getLogger(__name__)
VALID_PROVIDERS = ("deepgram", "sarvam", "elevenlabs")


def _use_voice_proxy(provider: str | None = None) -> bool:
    """Whether LiveKit should call MetricAI proxy URLs for this voice provider."""
    settings = get_settings()
    if not (metricai_api_key() and settings.metricai_route_voice):
        return False
    # Staging Deepgram /v1/speak returns 500 today — keep Deepgram on direct APIs.
    # Dashboard STT/TTS rows still come from client-side track() (see metricai_voice_telemetry).
    if (provider or "").strip().lower() in ("deepgram", "sarvam"):
        logger.warning(
            f"METRICAI_ROUTE_VOICE=true but {provider} staging proxy is broken; "
            f"using direct {provider} + MetricAI track() for metering"
        )
        return False
    return True


def get_voice_provider(
    name: str,
    *,
    deepgram_session: aiohttp.ClientSession | None = None,
    sarvam_session: aiohttp.ClientSession | None = None,
) -> dict:
    """Return a full STT+TTS pair for Deepgram or Sarvam (never mixed)."""
    provider = (name or "").strip().lower()
    settings = get_settings()
    via_proxy = _use_voice_proxy(provider)

    if provider == "deepgram":
        # Only attach MetricAI BYOK session when calling the proxy.
        # Direct Deepgram needs Authorization: Token <DEEPGRAM_API_KEY> — MetricAI
        # Bearer headers on api.deepgram.com cause 401 Invalid credentials.
        session = deepgram_session if via_proxy else None
        if via_proxy and session is None:
            session = make_deepgram_http_session()
        stt = deepgram.STT(
            model="nova-3",
            language="en-US",
            detect_language=False,
            interim_results=True,
            punctuate=True,
            # Silence gap after speech before committing the user turn
            endpointing_ms=500,
            utterance_end_ms=1000,
            api_key=settings.deepgram_api_key,
            base_url=deepgram_listen_url() if via_proxy else "https://api.deepgram.com/v1/listen",
            http_session=session,
        )
        tts = deepgram.TTS(
            model="aura-2-thalia-en",
            api_key=settings.deepgram_api_key,
            base_url=deepgram_speak_url() if via_proxy else "https://api.deepgram.com/v1/speak",
            http_session=session,
        )
        logger.info("Deepgram STT+TTS pair via %s", "MetricAI" if via_proxy else "direct")
        return {
            "name": "deepgram",
            "language": "en",
            "stt": stt,
            "tts": tts,
            # STT endpointing ends the turn — avoids heavy Silero VAD on CPU
            "turn_detection": "stt",
            "min_endpointing_delay": 0.4,
        }

    if provider == "sarvam":
        session = sarvam_session if via_proxy else None
        if via_proxy and session is None:
            session = make_sarvam_http_session()
        stt = sarvam.STT(
            model="saaras:v3",
            language="hi-IN",
            flush_signal=True,
            api_key=settings.sarvam_api_key,
            base_url=sarvam_stt_rest_url() if via_proxy else None,
            http_session=session,
        )
        if via_proxy:
            # LiveKit STT only accepts base_url; force streaming URL onto the proxy too.
            stt._opts.streaming_url = sarvam_stt_ws_url()

        tts = sarvam.TTS(
            model="bulbul:v3",
            speaker="kavitha",
            target_language_code="hi-IN",
            api_key=settings.sarvam_api_key,
            base_url=sarvam_tts_rest_url() if via_proxy else "https://api.sarvam.ai/text-to-speech",
            ws_url=sarvam_tts_ws_url() if via_proxy else "wss://api.sarvam.ai/text-to-speech/ws",
            http_session=session,
        )
        logger.info("Sarvam STT+TTS pair via %s", "MetricAI" if via_proxy else "direct")
        return {
            "name": "sarvam",
            "language": "hi",
            "stt": stt,
            "tts": tts,
            "turn_detection": "stt",
            "min_endpointing_delay": 0.4,
        }

    if provider == "elevenlabs":
        stt = deepgram.STT(
            model="nova-3",
            language="en-US",
            detect_language=False,
            interim_results=True,
            punctuate=True,
            endpointing_ms=500,
            utterance_end_ms=1000,
            api_key=settings.deepgram_api_key,
            base_url="https://api.deepgram.com/v1/listen",
        )
        tts = elevenlabs.TTS(
            model="eleven_multilingual_v2",
            voice_id="EXAVITQu4vr4xnSDxMaL",
            api_key=settings.elevenlabs_api_key,
        )
        logger.info("ElevenLabs TTS + Deepgram STT pair (direct)")
        return {
            "name": "elevenlabs",
            "language": "en",
            "stt": stt,
            "tts": tts,
            "turn_detection": "stt",
            "min_endpointing_delay": 0.4,
        }

    raise ValueError(
        f"Unknown voice provider: {name!r}. Expected one of: {', '.join(VALID_PROVIDERS)}"
    )


def get_session_kwargs(provider_name: str, **session_kwargs) -> dict:
    voice = get_voice_provider(provider_name, **session_kwargs)
    # Explicit None skips default cloud/Silero VAD (was ~10s behind realtime on this machine).
    kwargs = {
        "stt": voice["stt"],
        "tts": voice["tts"],
        "vad": None,
        "turn_detection": voice["turn_detection"],
        "min_endpointing_delay": voice["min_endpointing_delay"],
    }
    return kwargs


def get_provider_language(provider_name: str) -> str:
    provider = (provider_name or "").strip().lower()
    if provider == "sarvam":
        return "hi"
    return "en"


def get_openai_llm():
    """OpenAI LLM routed through MetricAI proxy.
    We MUST do this manually because MetricAI auto_instrument only patches
    the synchronous OpenAI() client, but LiveKit relies on AsyncOpenAI().
    """
    settings = get_settings()
    ma_key = metricai_api_key()
    if ma_key:
        import openai as openai_sdk
        client = openai_sdk.AsyncOpenAI(
            api_key=ma_key,
            base_url=openai_proxy_base_url(),
            default_headers=openai_extra_headers(),
        )
        return openai.LLM(
            model=settings.llm_model,
            client=client,
        )
    logger.warning("METRICAI_API_KEY not set — OpenAI LLM will call api.openai.com directly")
    return openai.LLM(model=settings.llm_model)
