from sqlalchemy import create_engine, event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings


def _async_engine_kwargs():
    kw: dict = {"echo": settings.DEBUG}
    if settings.DATABASE_URL.startswith("sqlite"):
        kw["connect_args"] = {"check_same_thread": False, "timeout": 15}
    else:
        # Server databases (PostgreSQL): bounded, health-checked pool
        kw.update(pool_pre_ping=True, pool_size=10, max_overflow=20, pool_recycle=1800, pool_timeout=30)
    return kw


def _sync_engine_kwargs():
    kw: dict = {"echo": settings.DEBUG, "pool_pre_ping": True}
    if settings.DATABASE_URL_SYNC.startswith("sqlite"):
        kw["connect_args"] = {"check_same_thread": False, "timeout": 15}
    return kw


def _sqlite_pragmas(dbapi_conn, _record):
    cur = dbapi_conn.cursor()
    cur.execute("PRAGMA journal_mode=WAL")      # readers don't block the writer
    cur.execute("PRAGMA synchronous=NORMAL")    # safe with WAL, faster writes
    cur.execute("PRAGMA foreign_keys=ON")       # enforce relationships
    cur.execute("PRAGMA busy_timeout=15000")    # wait for locks instead of failing
    cur.close()


# Async engine for FastAPI
async_engine = create_async_engine(settings.DATABASE_URL, **_async_engine_kwargs())

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Sync engine: schema upgrades, the email outbox worker and Alembic
sync_engine = create_engine(settings.DATABASE_URL_SYNC, **_sync_engine_kwargs())
SyncSessionLocal = sessionmaker(bind=sync_engine, autocommit=False, autoflush=False)

if settings.DATABASE_URL.startswith("sqlite"):
    event.listen(async_engine.sync_engine, "connect", _sqlite_pragmas)
if settings.DATABASE_URL_SYNC.startswith("sqlite"):
    event.listen(sync_engine, "connect", _sqlite_pragmas)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Create missing tables and add any new columns/indexes (never drops anything)."""
    import asyncio
    from app.core.schema import ensure_schema
    await asyncio.to_thread(ensure_schema, sync_engine, Base.metadata)
