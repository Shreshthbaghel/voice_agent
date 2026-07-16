"""Agent tools — medicine lookup via PostgreSQL."""
import logging

from database import SessionLocal
from services.medicine_service import (
    format_medicine_response,
    normalize_medicine_query,
    search_medicine_by_name,
)

logger = logging.getLogger(__name__)


async def search_medicine(medicine_name: str) -> str:
    """Look up a medicine by name in the database."""
    db = SessionLocal()
    try:
        resolved = normalize_medicine_query(medicine_name)
        logger.info("search_medicine raw=%r resolved=%r", medicine_name, resolved)

        medicine = search_medicine_by_name(db, medicine_name)
        if medicine:
            return format_medicine_response(medicine)

        return (
            f"No medicine found matching '{medicine_name}'"
            + (f" (interpreted as '{resolved}')" if resolved and resolved.lower() != medicine_name.lower() else "")
            + ". Tell the user the name was not found once. "
            "If they already spelled it, ask for a common brand name "
            "(e.g. Dolo, Crocin) — do not ask them to spell the same name again."
        )
    finally:
        db.close()
