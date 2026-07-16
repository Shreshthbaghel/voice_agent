"""Dashboard router — usage stats."""
from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import get_db
from orm_models import Conversation
from schemas import DashboardStats

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("", response_model=DashboardStats)
def dashboard(db: Session = Depends(get_db)):
    conv_count = db.query(func.count(Conversation.id)).scalar() or 0
    completed = (
        db.query(func.count(Conversation.id))
        .filter(Conversation.status == "completed")
        .scalar()
        or 0
    )
    return DashboardStats(
        conversation_count=conv_count,
        completed_sessions=completed,
    )
