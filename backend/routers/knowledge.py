"""Knowledge router — cached medicine knowledge."""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from orm_models import Knowledge
from retriever.service import get_retrieval_service
from schemas import KnowledgeOut

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


@router.get("", response_model=list[KnowledgeOut])
def list_knowledge(db: Session = Depends(get_db)):
    items = get_retrieval_service().list_knowledge(db)
    return [
        KnowledgeOut(
            id=k.id,
            topic=k.topic,
            title=k.title,
            source=k.source,
            url=k.url,
            summary=k.summary,
            language=k.language,
            created_at=k.created_at,
            confidence=k.confidence,
        )
        for k in items
    ]


@router.delete("/{knowledge_id}")
def delete_knowledge(knowledge_id: int, db: Session = Depends(get_db)):
    deleted = get_retrieval_service().delete_knowledge(db, knowledge_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Knowledge not found")
    return {"deleted": True, "id": knowledge_id}


@router.post("/refresh")
def refresh_expired(db: Session = Depends(get_db)):
    now = datetime.utcnow()
    expired = db.query(Knowledge).filter(Knowledge.expires_at < now).all()
    retrieval = get_retrieval_service()
    for item in expired:
        retrieval.delete_knowledge(db, item.id)
    return {"refreshed": len(expired)}
