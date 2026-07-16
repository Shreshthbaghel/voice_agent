"""Query service — text query over medicine database."""
import logging
from typing import Any

from openai import OpenAI
from sqlalchemy.orm import Session

from config import get_settings
from services.intent_service import detect_intent
from services.medicine_service import format_medicine_response, search_medicine_by_name

logger = logging.getLogger(__name__)
settings = get_settings()


def process_query(db: Session, query: str) -> dict[str, Any]:
    intent = detect_intent(query)
    medicine = search_medicine_by_name(db, query)
    if medicine:
        context = format_medicine_response(medicine)
        answer = _llm_answer(query, context)
        return {
            "answer": answer,
            "source": "local_db",
            "intent": intent,
            "medicine": medicine.name,
        }

    return {
        "answer": (
            "I couldn't find information about that medicine. "
            "Please check the spelling or try a different name. "
            "Confirm details with a pharmacist or doctor."
        ),
        "source": "not_found",
        "intent": intent,
    }


def _llm_answer(query: str, context: str) -> str:
    if not settings.openai_api_key:
        return context[:500]

    client = OpenAI(api_key=settings.openai_api_key)
    try:
        response = client.chat.completions.create(
            model=settings.llm_model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a medicine information assistant. Use only the provided context. "
                        "Keep answers to 1-2 sentences. Never give dosage advice or personal medical recommendations."
                    ),
                },
                {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {query}"},
            ],
            max_tokens=200,
        )
        return response.choices[0].message.content or context[:300]
    except Exception as e:
        logger.error("LLM answer failed: %s", e)
        return context[:500]
