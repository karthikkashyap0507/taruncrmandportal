from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings


def _engine_args(url: str) -> dict:
    if url.startswith("sqlite"):
        # Required for SQLite when using FastAPI (multi-threaded requests)
        return {"connect_args": {"check_same_thread": False}}
    return {}


engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    **_engine_args(settings.DATABASE_URL),
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
