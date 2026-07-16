"""Pydantic schemas for Voice Medicine Assistant."""
import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field
from livekit import api
from sqlalchemy.orm import Session

from config import get_settings
from services.conversation_service import create_conversation

settings = get_settings()


# ─── Auth ─────────────────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    name: str
    email: str
    created_at: datetime

    class Config:
        from_attributes = True


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ─── Voice ────────────────────────────────────────────────────────────────────

class TokenRequest(BaseModel):
    room_name: str | None = None
    participant_name: str = "user"
    conversation_id: str | None = None
    voice_provider: str | None = None


class TokenResponse(BaseModel):
    token: str
    url: str
    room_name: str
    conversation_id: str


# ─── Query ────────────────────────────────────────────────────────────────────

class QueryRequest(BaseModel):
    query: str
    conversation_id: str | None = None


# ─── History ──────────────────────────────────────────────────────────────────

class EndSessionRequest(BaseModel):
    medicine_name: str | None = None


class MessageOut(BaseModel):
    role: str
    content: str
    created_at: datetime


class ConversationSummary(BaseModel):
    id: str
    medicine_name: str | None
    status: str
    started_at: datetime
    ended_at: datetime | None
    summary: str | None
    message_count: int = 0


class ConversationDetail(ConversationSummary):
    messages: list[MessageOut] = Field(default_factory=list)


# ─── Dashboard ────────────────────────────────────────────────────────────────

class DashboardStats(BaseModel):
    conversation_count: int
    completed_sessions: int


# ─── Token helper ─────────────────────────────────────────────────────────────

def create_livekit_token(request: TokenRequest, db: Session, user_id: int | None = None) -> TokenResponse:
    if not settings.livekit_ready:
        raise ValueError("LiveKit credentials not configured")

    room_name = request.room_name or f"medicine-{uuid.uuid4().hex[:8]}"
    conversation_id = request.conversation_id or str(uuid.uuid4())
    create_conversation(db, conversation_id, user_id=user_id)

    provider = request.voice_provider or settings.voice_provider
    token = (
        api.AccessToken(settings.livekit_api_key, settings.livekit_api_secret)
        .with_identity(request.participant_name)
        .with_name(request.participant_name)
        .with_grants(api.VideoGrants(room_join=True, room=room_name))
        .with_metadata(f'{{"conversation_id":"{conversation_id}","voice_provider":"{provider}"}}')
        .to_jwt()
    )

    return TokenResponse(
        token=token,
        url=settings.livekit_url,
        room_name=room_name,
        conversation_id=conversation_id,
    )
