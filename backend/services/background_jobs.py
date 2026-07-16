"""Background jobs for knowledge refresh and cache maintenance."""

import asyncio
import logging
from datetime import datetime

from database import SessionLocal
from orm_models import Knowledge
from retriever.service import get_retrieval_service

logger = logging.getLogger(__name__)


def refresh_expired_knowledge() -> int:
    db = SessionLocal()
    try:
        now = datetime.utcnow()
        expired = db.query(Knowledge).filter(Knowledge.expires_at < now).all()
        retrieval = get_retrieval_service()
        for item in expired:
            retrieval.delete_knowledge(db, item.id)
        logger.info("Removed %d expired knowledge entries", len(expired))
        return len(expired)
    finally:
        db.close()


async def run_background_loop(interval_seconds: int = 3600) -> None:
    while True:
        try:
            refresh_expired_knowledge()
        except Exception as e:
            logger.error("Background refresh failed: %s", e)
        await asyncio.sleep(interval_seconds)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_background_loop())
