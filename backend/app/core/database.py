from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings

IS_SQLITE = settings.DATABASE_URL.startswith("sqlite")


def _engine_args(url: str) -> dict:
    if url.startswith("sqlite"):
        # check_same_thread=False: FastAPI runs sync endpoints in a thread pool
        return {"connect_args": {"check_same_thread": False, "timeout": 15}}
    # Server databases (PostgreSQL): a bounded, health-checked connection pool
    return {"pool_size": 10, "max_overflow": 20, "pool_recycle": 1800, "pool_timeout": 30}


engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    **_engine_args(settings.DATABASE_URL),
)

if IS_SQLITE:
    @event.listens_for(engine, "connect")
    def _sqlite_pragmas(dbapi_conn, _record):
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL")      # readers don't block the writer
        cur.execute("PRAGMA synchronous=NORMAL")    # safe with WAL, much faster writes
        cur.execute("PRAGMA foreign_keys=ON")       # enforce relationships
        cur.execute("PRAGMA busy_timeout=15000")    # wait for locks instead of failing
        cur.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
