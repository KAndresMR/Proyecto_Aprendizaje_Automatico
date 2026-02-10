from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from typing import AsyncGenerator

DATABASE_URL = "postgresql+asyncpg://postgres:admin123@localhost:5432/inventario_db"

# 🔹 Engine SYNC (solo migraciones / create_all)
SYNC_DATABASE_URL = DATABASE_URL.replace("+asyncpg", "")
engine = create_engine(SYNC_DATABASE_URL, echo=False)

# 🔹 Engine ASYNC (FastAPI)
async_engine = create_async_engine(DATABASE_URL, echo=True)

AsyncSessionLocal = sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False
)

Base = declarative_base()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session