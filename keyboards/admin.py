from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

def get_admin_menu_keyboard() -> InlineKeyboardMarkup:
    """Главное меню админ-панели"""
    builder = InlineKeyboardBuilder()
    builder.button(text="📊 Подробная статистика", callback_data="admin:stats")
    builder.button(text="📢 Создать рассылку (дожим)", callback_data="admin:bc_menu")
    builder.button(text="📥 Выгрузить базу (CSV)", callback_data="admin:export_csv")
    builder.button(text="🔒 Выйти из админки", callback_data="admin:logout")
    builder.adjust(1)
    return builder.as_markup()

def get_broadcast_target_keyboard() -> InlineKeyboardMarkup:
    """Выбор сегмента аудитории для рассылки"""
    builder = InlineKeyboardBuilder()
    builder.button(text="📢 Всем пользователям", callback_data="admin:bc_target:all")
    builder.button(text="🇷🇺 Только RU аудитории", callback_data="admin:bc_target:ru")
    builder.button(text="🇰🇿 Только KZ аудитории", callback_data="admin:bc_target:kz")
    builder.button(text="💻 Сегмент IT", callback_data="admin:bc_target:it")
    builder.button(text="📈 Сегмент Маркетинг", callback_data="admin:bc_target:marketing")
    builder.button(text="🎨 Сегмент Дизайн", callback_data="admin:bc_target:design")
    builder.button(text="🌍 Сегмент Английский", callback_data="admin:bc_target:english")
    builder.button(text="❓ Не завершили тест", callback_data="admin:bc_target:not_tested")
    builder.button(text="⬅️ Назад в админку", callback_data="admin:menu")
    builder.adjust(1)
    return builder.as_markup()

def get_broadcast_confirm_keyboard() -> InlineKeyboardMarkup:
    """Подтверждение отправки рассылки"""
    builder = InlineKeyboardBuilder()
    builder.button(text="🚀 Запустить рассылку", callback_data="admin:bc_send")
    builder.button(text="❌ Отмена", callback_data="admin:bc_cancel")
    builder.adjust(2)
    return builder.as_markup()
