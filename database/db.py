from typing import AsyncGenerator
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from config import settings
from database.models import Base

# Инициализируем движок базы данных (поддерживает как SQLite, так и Supabase PostgreSQL)
engine = create_async_engine(
    settings.formatted_database_url,
    echo=False
)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def init_db() -> None:
    """Создание таблиц и автоматическая миграция новых колонок"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
        # Безопасное добавление новых колонок, если таблица уже существовала
        try:
            await conn.execute(text("ALTER TABLE users ADD COLUMN test_result VARCHAR(64)"))
        except Exception:
            pass
        try:
            await conn.execute(text("ALTER TABLE users ADD COLUMN test_completed_at TIMESTAMP"))
        except Exception:
            pass

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Генератор сессии БД"""
    async with async_session() as session:
        yield session
