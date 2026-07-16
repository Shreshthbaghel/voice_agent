"""Voice Medicine Assistant API."""
import logging
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from auth.router import router as auth_router
from config import get_settings
from routers import dashboard, history, query, voice
from services.metricai_proxy import init_metricai

settings = get_settings()
init_metricai()


def _setup_logging():
    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    root = logging.getLogger()
    root.setLevel(level)
    if not root.handlers:
        h = logging.StreamHandler(sys.stdout)
        h.setFormatter(fmt)
        root.addHandler(h)


_setup_logging()

app = FastAPI(
    title="Voice Medicine Assistant API",
    description="Voice medicine assistant with JWT auth and PostgreSQL.",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def init_database() -> None:
    from database import Base, engine
    import orm_models  # noqa: F401

    Path("data").mkdir(exist_ok=True)
    Base.metadata.create_all(bind=engine)
    from database import SessionLocal
    from services.medicine_service import seed_medicines

    db = SessionLocal()
    try:
        seed_medicines(db)
    finally:
        db.close()
    logging.getLogger(__name__).info("Database ready (%s)", settings.database_url.split("?")[0])


@app.on_event("startup")
def _startup_db():
    init_database()


app.include_router(auth_router)
app.include_router(voice.router)
app.include_router(query.router)
app.include_router(history.router)
app.include_router(dashboard.router)


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "llm_ready": settings.llm_ready,
        "livekit_ready": settings.livekit_ready,
        "version": "2.0.0",
    }
