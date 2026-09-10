from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings
# Import every declarative model before any session executes an ORM query.
# This resolves string-based relationships such as Job.matches -> JobMatch in
# Celery workers and standalone scripts, which do not load the API routers.
from app.db import base_all  # noqa: F401

class Base(DeclarativeBase):
    pass

engine = create_async_engine(settings.DATABASE_URL, echo=True, future=True)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

@asynccontextmanager
async def get_session_context():
    async with AsyncSessionLocal() as session:
        yield session
