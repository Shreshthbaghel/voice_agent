import json
import logging
import os

from livekit.agents import Agent, AgentSession, JobContext, WorkerOptions, cli, function_tool
from livekit.agents.llm import ChatContext

from agents.providers import (
    _use_voice_proxy,
    get_openai_llm,
    get_provider_language,
    get_session_kwargs,
)
from agents.system_prompt import SYSTEM_PROMPT, english_session_hint, hindi_session_hint
from agents.tools import search_medicine as search_medicine_impl
from config import get_settings
from database import SessionLocal
from services.conversation_service import get_conversation
from services.metricai_proxy import init_metricai
from services.metricai_voice_telemetry import track_stt, track_tts

logger = logging.getLogger(__name__)
settings = get_settings()
init_metricai()
VALID_PROVIDERS = {"deepgram", "sarvam", "elevenlabs"}


class MedicineAgent(Agent):
    def __init__(self, *, language: str = "en", chat_ctx: ChatContext | None = None) -> None:
        language_block = (
            "Language rule: Speak and respond in English only. "
            "Never reply in Hindi or any other language."
            if language == "en"
            else "Language rule: Prefer Hindi (हिंदी) for spoken replies when the user speaks Hindi."
        )
        context_block = (
            "You already have prior conversation history in context. "
            "Use it: if the user asks about dosage, side effects, or follow-ups, "
            "tie answers to medicines already discussed. Do not treat follow-up phrases "
            "as a new medicine name unless the user clearly names a different medicine."
        )
        super().__init__(
            instructions=f"{SYSTEM_PROMPT}\n\n{language_block}\n\n{context_block}",
            chat_ctx=chat_ctx,
        )

    @function_tool
    async def search_medicine(self, medicine_name: str) -> str:
        """Look up a medicine by name. Returns use case, side effects, and prescription requirement."""
        return await search_medicine_impl(medicine_name)


def _parse_metadata(participant_metadata: str | None) -> dict:
    if not participant_metadata:
        return {}
    try:
        data = json.loads(participant_metadata)
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        logger.warning("Invalid participant metadata; using defaults")
        return {}


def _resolve_voice_provider(meta: dict) -> str:
    provider = os.environ.get("VOICE_PROVIDER", settings.voice_provider)
    selected = (meta.get("voice_provider") or "").strip().lower()
    if selected in VALID_PROVIDERS:
        provider = selected
    if provider not in VALID_PROVIDERS:
        provider = "deepgram"
    return provider


def _load_chat_context(conversation_id: str | None) -> ChatContext:
    """Load prior text/voice messages so the agent keeps conversation context."""
    chat_ctx = ChatContext.empty()
    if not conversation_id:
        return chat_ctx

    db = SessionLocal()
    try:
        conv = get_conversation(db, conversation_id)
        if not conv or not conv.messages:
            return chat_ctx
        for msg in conv.messages[-30:]:
            role = msg.role if msg.role in ("user", "assistant", "system") else "user"
            content = (msg.content or "").strip()
            if content:
                chat_ctx.add_message(role=role, content=content)
        logger.info(
            "Loaded %d prior messages for conversation %s",
            len(chat_ctx.items),
            conversation_id,
        )
    except Exception as e:
        logger.error("Failed to load conversation history: %s", e)
    finally:
        db.close()
    return chat_ctx


def _pause_listen_while_agent_busy(session: AgentSession) -> None:
    """Stop ingesting mic audio while the agent thinks/speaks; resume when listening again."""

    @session.on("agent_state_changed")
    def _on_agent_state(ev) -> None:
        # thinking/speaking => pause STT input; listening => open mic pipeline again
        busy = ev.new_state in ("thinking", "speaking")
        try:
            session.input.set_audio_enabled(not busy)
            logger.info(
                "Mic input %s (agent_state=%s)",
                "paused" if busy else "resumed",
                ev.new_state,
            )
        except Exception as e:
            logger.warning("Failed to toggle mic input: %s", e)


def _wire_metricai_voice_tracks(session: AgentSession, *, provider_name: str, conversation_id: str | None) -> None:
    """Push STT/TTS usage to MetricAI dashboard and save messages to the database."""
    stt_model = "nova-3" if provider_name in ("deepgram", "elevenlabs") else "saaras:v3"
    tts_model = "elevenlabs:eleven_multilingual_v2" if provider_name == "elevenlabs" else ("aura-2-thalia-en" if provider_name == "deepgram" else "bulbul:v3")

    @session.on("user_input_transcribed")
    def _on_stt(ev) -> None:
        if not getattr(ev, "is_final", True):
            return
        text = (getattr(ev, "transcript", None) or "").strip()
        if not text:
            return
        track_stt(
            provider=provider_name,
            model=stt_model,
            text=text,
            language=getattr(ev, "language", None),
        )

    @session.on("conversation_item_added")
    def _on_item(ev) -> None:
        item = getattr(ev, "item", None)
        role = str(getattr(item, "role", "") or "").lower()
        text = getattr(item, "text_content", None)
        if text is None:
            content = getattr(item, "content", None)
            if isinstance(content, list):
                text = " ".join(str(part) for part in content)
            else:
                text = content
        text = str(text or "").strip()
        if not text:
            return

        if role == "user":
            track_stt(provider=provider_name, model=stt_model, text=text)
        elif role == "assistant":
            track_tts(provider=provider_name, model=tts_model, text=text)

        if conversation_id and role in ("user", "assistant"):
            try:
                from services.conversation_service import add_message
                db = SessionLocal()
                add_message(db, conversation_id, role, text)
                db.close()
            except Exception as e:
                logger.error("Failed to save message to db: %s", e)



async def entrypoint(ctx: JobContext) -> None:
    # Job subprocesses need their own MetricAI client (worker init does not carry over).
    init_metricai(force=True)

    await ctx.connect()
    participant = await ctx.wait_for_participant()

    meta = _parse_metadata(participant.metadata)
    provider_name = _resolve_voice_provider(meta)
    conversation_id = (meta.get("conversation_id") or "").strip() or None
    language = get_provider_language(provider_name)

    logger.info(
        "Starting session with full %s STT+TTS pair (language=%s, conversation=%s)",
        provider_name,
        language,
        conversation_id or "new",
    )

    chat_ctx = _load_chat_context(conversation_id)

    dg_session = None
    sv_session = None
    # Only build MetricAI BYOK sessions when that provider is actually proxied.
    if _use_voice_proxy(provider_name):
        from services.metricai_proxy import make_deepgram_http_session, make_sarvam_http_session

        if provider_name == "deepgram":
            dg_session = make_deepgram_http_session()
        elif provider_name == "sarvam":
            sv_session = make_sarvam_http_session()

    session_kwargs = get_session_kwargs(
        provider_name,
        deepgram_session=dg_session,
        sarvam_session=sv_session,
    )
    session = AgentSession(
        **session_kwargs,
        llm=get_openai_llm(),
        turn_handling={
            # No barge-in: after the user finishes, we pause listening until the reply is done.
            "interruption": {
                "enabled": False,
                "discard_audio_if_uninterruptible": True,
            },
        },
    )
    _pause_listen_while_agent_busy(session)
    _wire_metricai_voice_tracks(session, provider_name=provider_name, conversation_id=conversation_id)

    agent = MedicineAgent(language=language, chat_ctx=chat_ctx)
    await session.start(agent=agent, room=ctx.room)

    # Only greet on a fresh session; keep quiet when continuing prior chat context
    if not chat_ctx.items:
        greet = english_session_hint if language == "en" else hindi_session_hint
        await session.generate_reply(instructions=greet)


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
