"""History router — past conversation sessions (requires auth)."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from auth.dependencies import get_current_user
from database import get_db
from orm_models import User
from schemas import ConversationDetail, ConversationSummary, EndSessionRequest, MessageOut
from services.conversation_service import end_conversation, get_conversation, list_conversations

router = APIRouter(prefix="/history", tags=["history"])


@router.get("", response_model=list[ConversationSummary])
def get_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conversations = list_conversations(db, user_id=current_user.id)
    return [
        ConversationSummary(
            id=c.id,
            medicine_name=c.medicine_name,
            status=c.status,
            started_at=c.started_at,
            ended_at=c.ended_at,
            summary=c.summary,
            message_count=len(c.messages),
        )
        for c in conversations
    ]


@router.get("/{session_id}", response_model=ConversationDetail)
def get_history_detail(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conv = get_conversation(db, session_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Session not found")
    if conv.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your session")
    return ConversationDetail(
        id=conv.id,
        medicine_name=conv.medicine_name,
        status=conv.status,
        started_at=conv.started_at,
        ended_at=conv.ended_at,
        summary=conv.summary,
        message_count=len(conv.messages),
        messages=[
            MessageOut(role=m.role, content=m.content, created_at=m.created_at)
            for m in conv.messages
        ],
    )


@router.post("/sessions/{session_id}/end")
def end_session(
    session_id: str,
    body: EndSessionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        conv = end_conversation(db, session_id, body.medicine_name)
        return {
            "id": conv.id,
            "status": conv.status,
            "summary": conv.summary,
            "medicine_name": conv.medicine_name,
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
