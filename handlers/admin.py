import asyncio
import logging
from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, BufferedInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.exceptions import TelegramForbiddenError, TelegramRetryAfter, TelegramBadRequest

from config import settings
from services.admin_service import admin_service
from services.user_service import UserService
from keyboards.admin import (
    get_admin_menu_keyboard,
    get_admin_stats_keyboard,
    get_broadcast_target_keyboard,
    get_broadcast_confirm_keyboard,
)

logger = logging.getLogger(__name__)
router = Router(name="admin_router")

# Локальный кэш сессий для мгновенной проверки без лишних запросов к БД
authenticated_admins: set[int] = set()

class AdminAuthFSM(StatesGroup):
    waiting_for_password = State()

class BroadcastFSM(StatesGroup):
    waiting_for_message = State()
    confirm_send = State()

def is_admin_id(user_id: int) -> bool:
    """Проверка Telegram ID по списку ADMIN_IDS в настройках"""
    return user_id in settings.admin_id_list

async def is_authenticated(user_id: int) -> bool:
    """
    Проверка авторизации:
    1. Проверяет в локальном кэше памяти
    2. Проверяет сохраненную сессию в базе данных (не слетает при перезапуске Render!)
    """
    if not is_admin_id(user_id):
        return False
    if user_id in authenticated_admins:
        return True
    if await UserService.is_admin_session_valid(user_id):
        authenticated_admins.add(user_id)
        return True
    return False

@router.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext):
    """
    Точка входа /admin.
    Если сессия активна (в БД или памяти) — сразу открывает меню.
    Иначе — запрашивает секретный пароль.
    """
    user_id = message.from_user.id
    if not is_admin_id(user_id):
        return

    # Убеждаемся, что админ есть в таблице users
    await UserService.get_or_create_user(user_id, message.from_user.username)

    if await is_authenticated(user_id):
        await state.clear()
        text = (
            "🔐 <b>Панель администратора</b>\n\n"
            "Сессия активна. Выберите необходимое действие:"
        )
        await message.answer(text=text, reply_markup=get_admin_menu_keyboard(), parse_mode="HTML")
    else:
        await state.set_state(AdminAuthFSM.waiting_for_password)
        await message.answer(
            text=(
                "🛡 <b>Вход в панель администратора</b>\n\n"
                "Введите секретный пароль доступа:"
            ),
            parse_mode="HTML"
        )

@router.message(AdminAuthFSM.waiting_for_password)
async def on_admin_password_entered(message: Message, state: FSMContext):
    """
    Проверка пароля:
    - Сообщение с паролем удаляется из чата
    - Сессия сохраняется в БД на 7 дней (не сбрасывается при перезапусках сервера)
    """
    user_id = message.from_user.id
    if not is_admin_id(user_id):
        return

    entered_password = (message.text or "").strip()

    # Немедленно удаляем пароль из чата
    try:
        await message.delete()
    except Exception:
        pass

    if entered_password == settings.ADMIN_PASSWORD.strip():
        authenticated_admins.add(user_id)
        # Убеждаемся, что запись есть в таблице и сохраняем сессию на 7 дней
        await UserService.get_or_create_user(user_id, message.from_user.username)
        await UserService.set_admin_session(user_id, days=7)
        await state.clear()
        await message.answer(
            text=(
                "✅ <b>Пароль принят! Доступ разрешен.</b>\n\n"
                "🔐 <b>Панель администратора</b>\n"
                "Выберите необходимое действие:"
            ),
            reply_markup=get_admin_menu_keyboard(),
            parse_mode="HTML"
        )
    else:
        await message.answer(
            text=(
                "⛔ <b>Неверный пароль доступа!</b>\n\n"
                "Попробуйте ввести пароль еще раз или отправьте /start для выхода."
            ),
            parse_mode="HTML"
        )

@router.callback_query(F.data == "admin:logout")
async def on_admin_logout(callback: CallbackQuery, state: FSMContext):
    """Завершение сессии администратора"""
    user_id = callback.from_user.id
    authenticated_admins.discard(user_id)
    await UserService.clear_admin_session(user_id)
    await state.clear()

    await callback.answer("Сессия закрыта")
    if callback.message:
        await callback.message.edit_text(
            text="🔒 <b>Сессия администратора завершена.</b>\nДля повторного входа используйте команду /admin.",
            parse_mode="HTML"
        )

@router.callback_query(F.data == "admin:menu")
async def on_admin_menu(callback: CallbackQuery, state: FSMContext):
    """Возврат в главное меню админки"""
    if not await is_authenticated(callback.from_user.id):
        await callback.answer("Сессия истекла. Введите пароль.", show_alert=True)
        await state.set_state(AdminAuthFSM.waiting_for_password)
        if callback.message:
            await callback.message.edit_text(
                text="🛡 <b>Сессия истекла</b>\n\nВведите секретный пароль администратора для входа:",
                parse_mode="HTML"
            )
        return

    await state.clear()
    text = (
        "🔐 <b>Панель администратора</b>\n\n"
        "Выберите необходимое действие:"
    )
    await callback.answer()
    if callback.message:
        try:
            await callback.message.edit_text(text=text, reply_markup=get_admin_menu_keyboard(), parse_mode="HTML")
        except TelegramBadRequest as e:
            if "message is not modified" not in str(e).lower():
                raise

@router.callback_query(F.data == "admin:stats")
async def on_admin_stats(callback: CallbackQuery, state: FSMContext):
    """Отображение развернутой статистики бота"""
    if not await is_authenticated(callback.from_user.id):
        await callback.answer("Сессия истекла. Введите пароль.", show_alert=True)
        await state.set_state(AdminAuthFSM.waiting_for_password)
        if callback.message:
            await callback.message.edit_text(
                text="🛡 <b>Сессия истекла</b>\n\nВведите секретный пароль администратора для входа:",
                parse_mode="HTML"
            )
        return

    await callback.answer("Загружаю актуальную статистику...")
    try:
        stats = await admin_service.get_stats()
    except Exception as e:
        logger.error(f"Error loading stats: {e}", exc_info=True)
        if callback.message:
            await callback.message.edit_text(
                text=f"⚠️ <b>Не удалось загрузить данные из базы:</b>\n\n<code>{e}</code>",
                reply_markup=get_admin_stats_keyboard(),
                parse_mode="HTML"
            )
        return

    if "error" in stats and stats["error"]:
        logger.error(f"Database stats error: {stats['error']}")
        if callback.message:
            await callback.message.edit_text(
                text=f"⚠️ <b>Ошибка при запросе к базе данных:</b>\n\n<code>{stats['error']}</code>",
                reply_markup=get_admin_stats_keyboard(),
                parse_mode="HTML"
            )
        return

    total = stats.get("total_users", 0)
    today = stats.get("users_today", 0)
    week = stats.get("users_week", 0)
    langs = stats.get("languages", {})
    completed = stats.get("completed_test", 0)
    conv = int((completed / total) * 100) if total > 0 else 0
    results = stats.get("test_results", {})
    clicks = stats.get("clicks", {})

    report = [
        "📊 <b>СТАТИСТИКА БОТА И ЛИДОВ</b>\n",
        f"👥 <b>Всего пользователей:</b> {total}",
        f"⚡ <b>Новых за 24 часа:</b> +{today}",
        f"📅 <b>Новых за 7 дней:</b> +{week}\n",
        "🌐 <b>Языковая аудитория:</b>",
        f"• 🇷🇺 Русский: {langs.get('ru', 0)}",
        f"• 🇰🇿 Қазақша: {langs.get('kz', 0)}\n",
        "🎯 <b>Профориентационный тест:</b>",
        f"• Завершили: <b>{completed}</b> ({conv}% от всей базы)",
        f"• Не завершили: {total - completed}\n",
        "📌 <b>Определенные направления (интересы):</b>",
        f"• 💻 IT-разработка: {results.get('it', 0)}",
        f"• 📈 Таргет / Маркетинг: {results.get('marketing', 0)}",
        f"• 🎨 UX/UI Дизайн: {results.get('design', 0)}",
        f"• 🌍 Английский язык: {results.get('english', 0)}\n",
        "🔥 <b>Клики по офферам (интерес к покупке):</b>"
    ]

    if clicks:
        for offer_id, count in clicks.items():
            report.append(f"• <code>{offer_id}</code>: {count} чел.")
    else:
        report.append("• <i>Пока кликов не зафиксировано</i>")

    text = "\n".join(report)

    if callback.message:
        try:
            await callback.message.edit_text(
                text=text,
                reply_markup=get_admin_stats_keyboard(),
                parse_mode="HTML"
            )
        except TelegramBadRequest as e:
            if "message is not modified" in str(e).lower():
                await callback.answer("Данные уже актуальны 👍")
            else:
                raise

@router.callback_query(F.data == "admin:export_csv")
async def on_admin_export_csv(callback: CallbackQuery, state: FSMContext):
    """Выгрузка базы пользователей в формате CSV"""
    if not await is_authenticated(callback.from_user.id):
        await callback.answer("Сессия истекла. Введите пароль.", show_alert=True)
        await state.set_state(AdminAuthFSM.waiting_for_password)
        if callback.message:
            await callback.message.edit_text(
                text="🛡 <b>Сессия истекла</b>\n\nВведите секретный пароль администратора для входа:",
                parse_mode="HTML"
            )
        return

    await callback.answer("Формирую CSV-файл базы...")
    try:
        csv_bytes = await admin_service.export_csv()
        doc = BufferedInputFile(csv_bytes.getvalue(), filename="users_export.csv")
        stats = await admin_service.get_stats()
        caption = (
            f"📥 <b>Экспорт базы пользователей</b>\n\n"
            f"• Всего записей: <b>{stats['total_users']}</b>\n"
            f"• Формат: CSV (UTF-8 с разделителем ';')\n"
            f"• Открывается в Excel, Google Таблицах или Numbers."
        )
        if callback.message:
            await callback.message.answer_document(document=doc, caption=caption, parse_mode="HTML")
    except Exception as e:
        logger.error(f"Error exporting CSV: {e}", exc_info=True)
        if callback.message:
            await callback.message.answer(f"⚠️ Ошибка при формировании файла: {e}")

# ==================== РАССЫЛКА (ДОЖИМ) ====================

@router.callback_query(F.data == "admin:bc_menu")
async def on_broadcast_menu(callback: CallbackQuery, state: FSMContext):
    """Выбор аудитории для рассылки"""
    if not await is_authenticated(callback.from_user.id):
        await callback.answer("Сессия истекла. Введите пароль.", show_alert=True)
        await state.set_state(AdminAuthFSM.waiting_for_password)
        if callback.message:
            await callback.message.edit_text(
                text="🛡 <b>Сессия истекла</b>\n\nВведите секретный пароль администратора для входа:",
                parse_mode="HTML"
            )
        return

    text = (
        "📢 <b>Создание рассылки (дожим аудитории)</b>\n\n"
        "Выберите целевой сегмент получателей:"
    )
    await callback.answer()
    if callback.message:
        try:
            await callback.message.edit_text(
                text=text,
                reply_markup=get_broadcast_target_keyboard(),
                parse_mode="HTML"
            )
        except TelegramBadRequest as e:
            if "message is not modified" not in str(e).lower():
                raise

@router.callback_query(F.data.startswith("admin:bc_target:"))
async def on_broadcast_target_selected(callback: CallbackQuery, state: FSMContext):
    """Фиксация сегмента и запрос сообщения для рассылки"""
    if not await is_authenticated(callback.from_user.id):
        await callback.answer("Сессия истекла. Введите пароль.", show_alert=True)
        await state.set_state(AdminAuthFSM.waiting_for_password)
        if callback.message:
            await callback.message.edit_text(
                text="🛡 <b>Сессия истекла</b>\n\nВведите секретный пароль администратора для входа:",
                parse_mode="HTML"
            )
        return

    target = callback.data.split(":")[2]
    user_ids = await admin_service.get_audience_ids(target)

    await state.update_data(target=target, audience_count=len(user_ids))
    await state.set_state(BroadcastFSM.waiting_for_message)

    target_names = {
        "all": "Всем пользователям",
        "ru": "Только RU аудитории",
        "kz": "Только KZ аудитории",
        "it": "Сегмент IT",
        "marketing": "Сегмент Маркетинг",
        "design": "Сегмент Дизайн",
        "english": "Сегмент Английский",
        "not_tested": "Не завершившие тест",
    }
    target_title = target_names.get(target, target)

    text = (
        f"🎯 Выбран сегмент: <b>{target_title}</b>\n"
        f"👥 Получателей в базе: <b>{len(user_ids)} чел.</b>\n\n"
        "👇 <b>Отправьте сообщение для рассылки прямо в этот чат:</b>\n"
        "<i>(Поддерживается текст, ссылки, форматирование, а также фото с подписью)</i>"
    )

    await callback.answer()
    if callback.message:
        await callback.message.edit_text(text=text, parse_mode="HTML")

@router.message(BroadcastFSM.waiting_for_message)
async def on_broadcast_message_received(message: Message, state: FSMContext):
    """Получение шаблона сообщения от админа и показ предпросмотра"""
    if not await is_authenticated(message.from_user.id):
        return

    await state.update_data(message_id=message.message_id, from_chat_id=message.chat.id)
    await state.set_state(BroadcastFSM.confirm_send)

    data = await state.get_data()
    count = data.get("audience_count", 0)

    await message.answer(
        text=(
            f"👆 <b>Предпросмотр сообщения выше.</b>\n\n"
            f"👥 Получателей: <b>{count} чел.</b>\n"
            "Запустить отправку рассылки?"
        ),
        reply_markup=get_broadcast_confirm_keyboard(),
        parse_mode="HTML"
    )

@router.callback_query(BroadcastFSM.confirm_send, F.data == "admin:bc_send")
async def on_broadcast_send(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Выполнение массовой рассылки с контролем скорости и отчетом"""
    if not await is_authenticated(callback.from_user.id):
        return

    data = await state.get_data()
    target = data.get("target", "all")
    from_chat_id = data.get("from_chat_id")
    message_id = data.get("message_id")

    await state.clear()
    await callback.answer()

    user_ids = await admin_service.get_audience_ids(target)
    status_msg = await callback.message.answer(
        text=f"⏳ Рассылка запущена на <b>{len(user_ids)}</b> пользователей...",
        parse_mode="HTML"
    )

    sent_count = 0
    blocked_count = 0

    for uid in user_ids:
        try:
            await bot.copy_message(
                chat_id=uid,
                from_chat_id=from_chat_id,
                message_id=message_id
            )
            sent_count += 1
            await asyncio.sleep(0.04)  # Защита от лимитов Telegram (25-30 сообщений/сек)
        except TelegramForbiddenError:
            blocked_count += 1
        except TelegramRetryAfter as e:
            await asyncio.sleep(e.retry_after)
            try:
                await bot.copy_message(chat_id=uid, from_chat_id=from_chat_id, message_id=message_id)
                sent_count += 1
            except Exception:
                pass
        except Exception as e:
            logger.warning(f"Broadcast error for {uid}: {e}")

    await status_msg.edit_text(
        text=(
            "✅ <b>Рассылка успешно завершена!</b>\n\n"
            f"• Доставлено: <b>{sent_count}</b>\n"
            f"• Заблокировали бота: <b>{blocked_count}</b>"
        ),
        reply_markup=get_admin_menu_keyboard(),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "admin:bc_cancel")
async def on_broadcast_cancel(callback: CallbackQuery, state: FSMContext):
    """Отмена рассылки"""
    if not await is_authenticated(callback.from_user.id):
        return

    await state.clear()
    await callback.answer("Рассылка отменена")
    if callback.message:
        await callback.message.edit_text(
            text="❌ Рассылка отменена.",
            reply_markup=get_admin_menu_keyboard(),
            parse_mode="HTML"
        )
