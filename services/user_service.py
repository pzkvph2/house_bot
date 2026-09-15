from datetime import datetime
from typing import Optional
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import User
from database.db import async_session

class UserService:
    @staticmethod
    async def get_or_create_user(user_id: int, username: Optional[str] = None) -> User:
        """Получение или регистрация пользователя в базе"""
        async with async_session() as session:
            stmt = select(User).where(User.user_id == user_id)
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()

            if not user:
                user = User(
                    user_id=user_id,
                    username=username,
                    language="ru",
                    created_at=datetime.utcnow(),
                    last_active_at=datetime.utcnow()
                )
                session.add(user)
                await session.commit()
                await session.refresh(user)
            else:
                # Обновляем username и дату активности при каждом визите
                if user.username != username:
                    user.username = username
                user.last_active_at = datetime.utcnow()
                await session.commit()
                await session.refresh(user)
            return user

    @staticmethod
    async def set_user_language(user_id: int, language: str) -> None:
        """Сохранение выбранного языка пользователя"""
        async with async_session() as session:
            stmt = (
                update(User)
                .where(User.user_id == user_id)
                .values(language=language, last_active_at=datetime.utcnow())
            )
            await session.execute(stmt)
            await session.commit()

    @staticmethod
    async def track_offer_click(user_id: int, offer_id: str) -> None:
        """Фиксация клика по офферу для аналитики и последующего дожима"""
        async with async_session() as session:
            stmt = (
                update(User)
                .where(User.user_id == user_id)
                .values(last_clicked_offer_id=offer_id, last_active_at=datetime.utcnow())
            )
            await session.execute(stmt)
            await session.commit()

    @staticmethod
    async def get_user_language(user_id: int) -> str:
        """Быстрое получение языка пользователя"""
        async with async_session() as session:
            stmt = select(User.language).where(User.user_id == user_id)
            result = await session.execute(stmt)
            lang = result.scalar_one_or_none()
            return lang or "ru"

    @staticmethod
    async def save_test_result(user_id: int, archetype: str) -> None:
        """Сохранение результатов профориентационного теста для персонального дожима"""
        async with async_session() as session:
            stmt = (
                update(User)
                .where(User.user_id == user_id)
                .values(
                    test_result=archetype,
                    test_completed_at=datetime.utcnow(),
                    last_active_at=datetime.utcnow()
                )
            )
            await session.execute(stmt)
            await session.commit()

    @staticmethod
    async def get_user_test_result(user_id: int) -> Optional[str]:
        """Получение сохраненного результата теста"""
        async with async_session() as session:
            stmt = select(User.test_result).where(User.user_id == user_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

