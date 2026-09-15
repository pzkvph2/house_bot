from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from services.i18n import i18n
from services.offers import Offer, offer_service
from config import settings

def get_language_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора языка при первом старте или смене языка"""
    builder = InlineKeyboardBuilder()
    builder.button(text="🇷🇺 Русский", callback_data="lang:ru")
    builder.button(text="🇰🇿 Қазақша", callback_data="lang:kz")
    builder.adjust(2)
    return builder.as_markup()

def get_main_menu_keyboard(lang: str = "ru", user_id: int = 0) -> InlineKeyboardMarkup:
    """
    Главное меню:
    1. Главный CTA — Прохождение теста на предрасположенность (максимальный вовлекающий триггер)
    2. Кнопки направлений обучения / офферов
    3. Ссылка на канал и смену языка
    """
    builder = InlineKeyboardBuilder()

    # Топовая кнопка профориентации
    builder.row(
        InlineKeyboardButton(
            text=i18n.get("btn_start_quiz", lang),
            callback_data="quiz:start"
        )
    )

    # Список актуальных офферов
    active_offers = offer_service.get_active_offers()
    for offer in active_offers:
        builder.button(
            text=offer.get_title(lang),
            callback_data=f"offer:{offer.id}:menu"
        )
    builder.adjust(1)

    # Сервисные кнопки: канал и переключение языка
    channel_url = settings.formatted_channel_url
    builder.row(
        InlineKeyboardButton(
            text=i18n.get("btn_channel", lang),
            url=channel_url
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=i18n.get("btn_change_lang", lang),
            callback_data="change_lang"
        )
    )

    return builder.as_markup()

def get_all_courses_keyboard(lang: str = "ru", from_quiz: bool = False) -> InlineKeyboardMarkup:
    """
    Каталог всех доступных курсов (чтобы пользователь после теста или из меню мог изучить всё)
    """
    builder = InlineKeyboardBuilder()
    active_offers = offer_service.get_active_offers()

    back_target = "quiz:show_result" if from_quiz else "menu:back"

    for offer in active_offers:
        builder.button(
            text=offer.get_title(lang),
            callback_data=f"offer:{offer.id}:{back_target}"
        )
    builder.adjust(1)

    back_btn_text = i18n.get("btn_back_to_result", lang) if from_quiz else i18n.get("btn_back", lang)
    builder.row(
        InlineKeyboardButton(
            text=back_btn_text,
            callback_data=back_target
        )
    )
    return builder.as_markup()

def get_quiz_question_keyboard(question_index: int, options: list, lang: str = "ru") -> InlineKeyboardMarkup:
    """
    Клавиатура с вариантами ответов на текущий вопрос теста.
    Использует короткие метки кнопок, чтобы текст никогда не обрезался на смартфонах.
    """
    builder = InlineKeyboardBuilder()
    for opt in options:
        btn_text = opt.get_btn_text(lang)
        builder.button(
            text=btn_text,
            callback_data=f"quiz:ans:{question_index}:{opt.category}"
        )
    builder.adjust(1)

    back_text = "⬅️ Главное меню" if lang == "ru" else "⬅️ Басты мәзір"
    builder.row(
        InlineKeyboardButton(
            text=back_text,
            callback_data="menu:back"
        )
    )
    return builder.as_markup()

def get_quiz_result_keyboard(recommended_offer: Offer, user_id: int, lang: str = "ru") -> InlineKeyboardMarkup:
    """
    Клавиатура экрана результатов теста:
    1. Главный CTA — Прямой переход на рекомендованный курс с subID
    2. Кнопка «Посмотреть все курсы» (чтобы не резать конверсии)
    3. Кнопка «Пройти тест заново»
    4. В главное меню
    """
    builder = InlineKeyboardBuilder()

    # 1. Прямая ссылка на рекомендованный оффер
    tracking_url = recommended_offer.get_tracking_url(user_id=user_id)
    btn_text = i18n.get("btn_take_recommended", lang, title=recommended_offer.get_title(lang))
    builder.button(
        text=btn_text,
        url=tracking_url
    )

    # 2. Посмотреть все курсы
    builder.button(
        text=i18n.get("btn_all_courses", lang),
        callback_data="courses:all_from_quiz"
    )

    # 3. Перепройти тест
    builder.button(
        text=i18n.get("btn_restart_quiz", lang),
        callback_data="quiz:start"
    )

    # 4. Главное меню
    builder.button(
        text=i18n.get("btn_back", lang),
        callback_data="menu:back"
    )

    builder.adjust(1)
    return builder.as_markup()

def get_offer_details_keyboard(offer: Offer, user_id: int, lang: str = "ru", back_target: str = "menu:back") -> InlineKeyboardMarkup:
    """
    Клавиатура прелендинг-карточки оффера:
    - Кнопка-ссылка с динамическим subID (user_id)
    - Кнопка возврата (в меню или к результатам теста)
    """
    builder = InlineKeyboardBuilder()
    
    tracking_url = offer.get_tracking_url(user_id=user_id)
    builder.button(
        text=i18n.get("btn_apply", lang),
        url=tracking_url
    )

    back_text = i18n.get("btn_back_to_result", lang) if "quiz" in back_target else i18n.get("btn_back", lang)
    builder.button(
        text=back_text,
        callback_data=back_target
    )
    builder.adjust(1)
    return builder.as_markup()
