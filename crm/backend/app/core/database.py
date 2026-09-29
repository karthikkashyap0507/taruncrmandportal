from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import create_engine
from app.core.config import settings


def _async_engine_kwargs():
    kw: dict = {"echo": settings.DEBUG}
    if settings.DATABASE_URL.startswith("sqlite"):
        kw["connect_args"] = {"check_same_thread": False}
    else:
        kw["pool_pre_ping"] = True
        kw["pool_size"] = 10
        kw["max_overflow"] = 20
    return kw


def _sync_engine_kwargs():
    kw: dict = {"echo": settings.DEBUG}
    if settings.DATABASE_URL_SYNC.startswith("sqlite"):
        kw["connect_args"] = {"check_same_thread": False}
    return kw


# Async engine for FastAPI
async_engine = create_async_engine(settings.DATABASE_URL, **_async_engine_kwargs())

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Sync engine for Alembic
sync_engine = create_engine(settings.DATABASE_URL_SYNC, **_sync_engine_kwargs())


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
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
