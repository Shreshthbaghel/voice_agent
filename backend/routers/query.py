"""Query router — text medicine lookups."""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from schemas import QueryRequest
from services.conversation_service import add_message, create_conversation, get_conversation
from services.query_service import process_query

router = APIRouter(prefix="/query", tags=["query"])


@router.post("")
def query(request: QueryRequest, db: Session = Depends(get_db)):
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    conversation_id = request.conversation_id or str(uuid.uuid4())
    create_conversation(db, conversation_id)

    result = process_query(db, request.query)
    add_message(db, conversation_id, "user", request.query)
    add_message(db, conversation_id, "assistant", result["answer"])
    if result.get("medicine"):
        conv = get_conversation(db, conversation_id)
        if conv and not conv.medicine_name:
            conv.medicine_name = result["medicine"]
            db.commit()

    result["conversation_id"] = conversation_id
    return result


@router.post("/search")
def search(request: QueryRequest, db: Session = Depends(get_db)):
    from retriever.service import get_retrieval_service

    return get_retrieval_service().retrieve(db, request.query)
