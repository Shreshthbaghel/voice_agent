from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv(Path(__file__).with_name(".env"), override=True)


class Settings(BaseSettings):
    # App
    app_name: str = "Voice Medicine Assistant"
    frontend_url: str = "http://localhost:5173"
    log_level: str = "INFO"
    debug: bool = False

    # Database
    database_url: str = "sqlite:///./voicemed.db"

    # JWT Auth
    jwt_secret: str = "change-me-in-production-use-a-long-random-string"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7  # 7 days

    # LiveKit
    livekit_url: str = ""
    livekit_api_key: str = ""
    livekit_api_secret: str = ""
    voice_provider: str = "deepgram"

    # MetricAI proxy
    metricai_api_key: str = ""
    metricai_base_url: str = "https://proxy.metricai.co.in"
    metricai_proxy_url: str = ""
    metricai_agent_id: str = "voice-medicine-assistant"
    metricai_user_id: str = "voice-user"
    metricai_route_voice: bool = True

    # LLM
    openai_api_key: str = ""
    llm_model: str = "gpt-4o-mini"
    deepgram_api_key: str = ""
    sarvam_api_key: str = ""
    elevenlabs_api_key: str = ""

    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).with_name(".env")),
        extra="ignore",
    )

    @property
    def llm_ready(self) -> bool:
        return bool(self.openai_api_key)

    @property
    def livekit_ready(self) -> bool:
        return bool(self.livekit_api_key and self.livekit_api_secret and self.livekit_url)


@lru_cache
def get_settings() -> Settings:
    return Settings()
