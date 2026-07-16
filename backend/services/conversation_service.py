"""Conversation service — create, retrieve, and end conversations."""
import logging
import uuid
from datetime import datetime

from sqlalchemy.orm import Session, joinedload

from config import get_settings
from orm_models import Conversation, Message

logger = logging.getLogger(__name__)
settings = get_settings()


def create_conversation(
    db: Session,
    conversation_id: str | None = None,
    user_id: int | None = None,
) -> Conversation:
    cid = conversation_id or str(uuid.uuid4())
    existing = db.query(Conversation).filter(Conversation.id == cid).first()
    if existing:
        return existing
    conv = Conversation(id=cid, user_id=user_id)
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return conv


def add_message(db: Session, conversation_id: str, role: str, content: str) -> Message:
    msg = Message(conversation_id=conversation_id, role=role, content=content)
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg


def end_conversation(db: Session, conversation_id: str, medicine_name: str | None = None) -> Conversation:
    conv = (
        db.query(Conversation)
        .options(joinedload(Conversation.messages))
        .filter(Conversation.id == conversation_id)
        .first()
    )
    if not conv:
        raise ValueError(f"Conversation {conversation_id} not found")

    conv.status = "completed"
    conv.ended_at = datetime.utcnow()
    if medicine_name:
        conv.medicine_name = medicine_name
    conv.summary = _generate_summary(conv.messages)
    db.commit()
    db.refresh(conv)
    return conv


def _generate_summary(messages: list[Message]) -> str:
    if not messages:
        return "Empty conversation."
    user_msgs = [m.content for m in messages if m.role == "user"]
    return f"Discussed: {user_msgs[0][:80]}..." if user_msgs else "Brief medicine inquiry."


def list_conversations(db: Session, user_id: int, limit: int = 50) -> list[Conversation]:
    return (
        db.query(Conversation)
        .options(joinedload(Conversation.messages))
        .filter(Conversation.user_id == user_id)
        .order_by(Conversation.started_at.desc())
        .limit(limit)
        .all()
    )


def get_conversation(db: Session, conversation_id: str) -> Conversation | None:
    return (
        db.query(Conversation)
        .options(joinedload(Conversation.messages))
        .filter(Conversation.id == conversation_id)
        .first()
    )
