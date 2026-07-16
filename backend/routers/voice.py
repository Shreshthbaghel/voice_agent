"""Voice router — LiveKit token issuance (optional auth to associate session with user)."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from auth.dependencies import get_optional_user
from database import get_db
from orm_models import User
from schemas import TokenRequest, TokenResponse, create_livekit_token

router = APIRouter(prefix="/voice", tags=["voice"])


@router.post("/token", response_model=TokenResponse)
def issue_token(
    request: TokenRequest,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
):
    try:
        user_id = current_user.id if current_user else None
        return create_livekit_token(request, db, user_id=user_id)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.post("", response_model=TokenResponse)
def start_voice_session(
    request: TokenRequest,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
):
    """Alias for POST /voice/token."""
    try:
        user_id = current_user.id if current_user else None
        return create_livekit_token(request, db, user_id=user_id)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
