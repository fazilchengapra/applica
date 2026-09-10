from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool
from contextlib import asynccontextmanager
from app.core.config import settings
# Celery tasks may query ORM models without importing API routers. Register all
# mapped classes so string relationships (for example Job.matches -> JobMatch)
# can be resolved before the first query is compiled.
from app.db import base_all  # noqa: F401

celery_engine = create_async_engine(
    settings.DATABASE_URL,
    poolclass=NullPool,
    future=True,
)

CelerySessionLocal = async_sessionmaker(
    bind=celery_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

@asynccontextmanager
async def get_celery_db_session():
    async with CelerySessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
