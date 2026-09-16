import logging
from typing import AsyncGenerator
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from config import settings, BASE_DIR
from database.models import Base

logger = logging.getLogger(__name__)

# Инициализируем движок базы данных с автоматическим пингом соединений и пулом
engine = create_async_engine(
    settings.formatted_database_url,
    echo=False,
    pool_pre_ping=True,
    pool_recycle=300
)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def _migrate_columns(conn) -> None:
    """Безопасное добавление недостающих колонок без сбоев транзакций"""
    dialect = conn.dialect.name
    if dialect == "postgresql":
        await conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS test_result VARCHAR(64)"))
        await conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS test_completed_at TIMESTAMP"))
        await conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS admin_authenticated_until TIMESTAMP"))
    elif dialect == "sqlite":
        res = await conn.execute(text("PRAGMA table_info(users)"))
        cols = [row[1] for row in res.fetchall()]
        if "test_result" not in cols:
            await conn.execute(text("ALTER TABLE users ADD COLUMN test_result VARCHAR(64)"))
        if "test_completed_at" not in cols:
            await conn.execute(text("ALTER TABLE users ADD COLUMN test_completed_at TIMESTAMP"))
        if "admin_authenticated_until" not in cols:
            await conn.execute(text("ALTER TABLE users ADD COLUMN admin_authenticated_until TIMESTAMP"))

async def init_db() -> None:
    """Создание таблиц и автоматическая миграция новых колонок с автоматическим фолбэком на SQLite"""
    global engine
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            await _migrate_columns(conn)
    except Exception as e:
        logger.warning(f"PostgreSQL/Supabase unavailable ({e}). Using local SQLite database...")
        fallback_url = f"sqlite+aiosqlite:///{BASE_DIR / 'bot.db'}"
        engine = create_async_engine(fallback_url, echo=False, pool_pre_ping=True, pool_recycle=300)
        async_session.configure(bind=engine)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            await _migrate_columns(conn)
        logger.info("Local SQLite database initialized and ready.")

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Генератор сессии БД"""
    async with async_session() as session:
        yield session

