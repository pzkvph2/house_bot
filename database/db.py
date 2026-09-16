import logging
from typing import AsyncGenerator
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from config import settings, BASE_DIR
from database.models import Base

logger = logging.getLogger(__name__)

# Инициализируем движок базы данных (поддерживает как SQLite, так и Supabase PostgreSQL)
engine = create_async_engine(
    settings.formatted_database_url,
    echo=False
)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def init_db() -> None:
    """Создание таблиц и автоматическая миграция новых колонок с автоматическим фолбэком на SQLite"""
    global engine
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            try:
                await conn.execute(text("ALTER TABLE users ADD COLUMN test_result VARCHAR(64)"))
            except Exception:
                pass
            try:
                await conn.execute(text("ALTER TABLE users ADD COLUMN test_completed_at TIMESTAMP"))
            except Exception:
                pass
            try:
                await conn.execute(text("ALTER TABLE users ADD COLUMN admin_authenticated_until TIMESTAMP"))
            except Exception:
                pass
    except Exception as e:
        logger.warning(f"PostgreSQL/Supabase unavailable locally ({e}). Using local SQLite database...")
        fallback_url = f"sqlite+aiosqlite:///{BASE_DIR / 'bot.db'}"
        engine = create_async_engine(fallback_url, echo=False)
        async_session.configure(bind=engine)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            try:
                await conn.execute(text("ALTER TABLE users ADD COLUMN test_result VARCHAR(64)"))
            except Exception:
                pass
            try:
                await conn.execute(text("ALTER TABLE users ADD COLUMN test_completed_at TIMESTAMP"))
            except Exception:
                pass
            try:
                await conn.execute(text("ALTER TABLE users ADD COLUMN admin_authenticated_until TIMESTAMP"))
            except Exception:
                pass
        logger.info("Local SQLite database initialized and ready.")

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Генератор сессии БД"""
    async with async_session() as session:
        yield session
