import csv
import io
from datetime import datetime, timedelta
from typing import Dict, Any, List
from sqlalchemy import select, func, desc
from database.db import async_session
from database.models import User

class AdminService:
    @staticmethod
    async def get_stats() -> Dict[str, Any]:
        """Сбор подробной статистики по пользователям, языкам, тестам и офферам"""
        try:
            async with async_session() as session:
                # Общее количество пользователей
                total_users_res = await session.execute(select(func.count(User.user_id)))
                total_users = total_users_res.scalar() or 0

                # Новые за 24 часа и 7 дней
                now = datetime.utcnow()
                day_ago = now - timedelta(days=1)
                week_ago = now - timedelta(days=7)

                today_res = await session.execute(select(func.count(User.user_id)).where(User.created_at >= day_ago))
                users_today = today_res.scalar() or 0

                week_res = await session.execute(select(func.count(User.user_id)).where(User.created_at >= week_ago))
                users_week = week_res.scalar() or 0

                # Статистика по языкам (безопасная распаковка)
                lang_res = await session.execute(
                    select(User.language, func.count(User.user_id)).group_by(User.language)
                )
                languages = {row[0]: row[1] for row in lang_res.all() if row[0]}

                # Статистика по прохождению теста
                completed_test_res = await session.execute(
                    select(func.count(User.user_id)).where(User.test_result.isnot(None))
                )
                completed_test = completed_test_res.scalar() or 0

                # Результаты теста по направлениям
                test_results_res = await session.execute(
                    select(User.test_result, func.count(User.user_id))
                    .where(User.test_result.isnot(None))
                    .group_by(User.test_result)
                )
                test_results = {row[0]: row[1] for row in test_results_res.all() if row[0]}

                # Клики по офферам
                clicks_res = await session.execute(
                    select(User.last_clicked_offer_id, func.count(User.user_id))
                    .where(User.last_clicked_offer_id.isnot(None))
                    .group_by(User.last_clicked_offer_id)
                    .order_by(desc(func.count(User.user_id)))
                )
                clicks = {row[0]: row[1] for row in clicks_res.all() if row[0]}

                return {
                    "total_users": total_users,
                    "users_today": users_today,
                    "users_week": users_week,
                    "languages": languages,
                    "completed_test": completed_test,
                    "test_results": test_results,
                    "clicks": clicks,
                }
        except Exception as e:
            return {
                "total_users": 0,
                "users_today": 0,
                "users_week": 0,
                "languages": {},
                "completed_test": 0,
                "test_results": {},
                "clicks": {},
                "error": str(e)
            }

    @staticmethod
    async def get_audience_ids(target: str) -> List[int]:
        """Возвращает список user_id для выбранного сегмента рассылки"""
        async with async_session() as session:
            stmt = select(User.user_id)

            if target == "all":
                pass
            elif target == "ru":
                stmt = stmt.where(User.language == "ru")
            elif target == "kz":
                stmt = stmt.where(User.language == "kz")
            elif target in ["it", "marketing", "design", "english"]:
                stmt = stmt.where(User.test_result == target)
            elif target == "not_tested":
                stmt = stmt.where(User.test_result.is_(None))

            res = await session.execute(stmt)
            return list(res.scalars().all())

    @staticmethod
    async def export_csv() -> io.BytesIO:
        """Генерация CSV-файла со всеми пользователями (UTF-8 с BOM для Excel)"""
        async with async_session() as session:
            stmt = select(User).order_by(desc(User.created_at))
            res = await session.execute(stmt)
            users = res.scalars().all()

            output = io.StringIO()
            writer = csv.writer(output, delimiter=";", quoting=csv.QUOTE_MINIMAL)
            writer.writerow([
                "Telegram ID",
                "Username",
                "Язык",
                "Результат теста",
                "Последний оффер",
                "Дата регистрации (UTC)",
                "Последняя активность (UTC)"
            ])

            for u in users:
                writer.writerow([
                    u.user_id,
                    f"@{u.username}" if u.username else "",
                    u.language,
                    u.test_result or "Не проходил",
                    u.last_clicked_offer_id or "Нет",
                    u.created_at.strftime("%Y-%m-%d %H:%M:%S") if u.created_at else "",
                    u.last_active_at.strftime("%Y-%m-%d %H:%M:%S") if u.last_active_at else ""
                ])

            bytes_io = io.BytesIO()
            # UTF-8 BOM для корректного отображения кириллицы в Excel на Windows и Mac
            bytes_io.write(output.getvalue().encode("utf-8-sig"))
            bytes_io.seek(0)
            return bytes_io

admin_service = AdminService()
