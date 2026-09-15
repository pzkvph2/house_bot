from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from services.user_service import UserService
from services.i18n import i18n
from services.offers import offer_service
from services.quiz import quiz_service
from keyboards.inline import (
    get_language_keyboard,
    get_main_menu_keyboard,
    get_all_courses_keyboard,
    get_quiz_question_keyboard,
    get_quiz_result_keyboard,
    get_offer_details_keyboard,
)

router = Router(name="user_router")

class QuizFSM(StatesGroup):
    answering = State()

def get_progress_bar(current: int, total: int) -> str:
    """Генерирует визуальный прогресс-бар: [🟩🟩⬜⬜⬜⬜] 33%"""
    filled = "🟩" * current
    empty = "⬜" * (total - current)
    percent = int((current / total) * 100)
    return f"[{filled}{empty}] {percent}%"

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    """
    Точка входа /start.
    1. Регистрирует/обновляет пользователя в базе данных.
    2. Запрашивает язык интерфейса (RU / KZ).
    """
    await state.clear()
    user_id = message.from_user.id
    username = message.from_user.username

    await UserService.get_or_create_user(user_id=user_id, username=username)

    text = i18n.get("choose_language", lang="ru")
    await message.answer(
        text=text,
        reply_markup=get_language_keyboard(),
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("lang:"))
async def on_language_chosen(callback: CallbackQuery, state: FSMContext):
    """Выбор языка и переход в главное меню"""
    await state.clear()
    lang_code = callback.data.split(":")[1]
    user_id = callback.from_user.id

    await UserService.set_user_language(user_id, lang_code)
    await callback.answer(i18n.get("language_selected", lang=lang_code))

    menu_text = i18n.get("main_menu_text", lang=lang_code)
    keyboard = get_main_menu_keyboard(lang=lang_code, user_id=user_id)

    if callback.message:
        await callback.message.edit_text(
            text=menu_text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )

# ==================== ПРОФОРИЕНТАЦИОННЫЙ ТЕСТ ====================

@router.callback_query(F.data == "quiz:start")
async def on_quiz_start(callback: CallbackQuery, state: FSMContext):
    """Старт интерактивного теста на предрасположенность"""
    user_id = callback.from_user.id
    lang = await UserService.get_user_language(user_id)
    await state.set_state(QuizFSM.answering)
    await state.update_data(answers=[])

    await show_quiz_question(callback=callback, question_index=0, lang=lang)

async def show_quiz_question(callback: CallbackQuery, question_index: int, lang: str):
    """Отображение вопроса: полный текст вариантов выводится в сообщении, а кнопки содержат короткие метки"""
    total = quiz_service.get_total_questions()
    question = quiz_service.get_question_by_index(question_index)
    if not question:
        return

    progress = get_progress_bar(current=question_index + 1, total=total)
    q_title = question.get_text(lang)

    # Выводим полный текст каждого варианта в теле сообщения — на любом телефоне читается на 100% без обрезания!
    options_lines = []
    for opt in question.options:
        letter = opt.letter or "•"
        full_text = opt.get_full_text(lang)
        options_lines.append(f"<b>{letter})</b> {full_text}")

    options_block = "\n".join(options_lines)
    text = f"{progress}\n\n{q_title}\n\n{options_block}"

    keyboard = get_quiz_question_keyboard(
        question_index=question_index,
        options=question.options,
        lang=lang
    )

    await callback.answer()
    if callback.message:
        await callback.message.edit_text(
            text=text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )

@router.callback_query(QuizFSM.answering, F.data.startswith("quiz:ans:"))
async def on_quiz_answer(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора ответа и переход к следующему вопросу или результатам"""
    parts = callback.data.split(":")
    current_index = int(parts[2])
    category = parts[3]

    data = await state.get_data()
    answers = data.get("answers", [])
    answers.append(category)
    await state.update_data(answers=answers)

    total = quiz_service.get_total_questions()
    next_index = current_index + 1

    user_id = callback.from_user.id
    lang = await UserService.get_user_language(user_id)

    if next_index < total:
        await show_quiz_question(callback=callback, question_index=next_index, lang=lang)
    else:
        # Тест завершен — подсчет направления и показ персонализированного результата
        best_archetype = quiz_service.calculate_result(answers)
        await UserService.save_test_result(user_id, best_archetype)
        await state.update_data(last_archetype=best_archetype)
        await show_quiz_results(callback=callback, archetype=best_archetype, user_id=user_id, lang=lang)

async def show_quiz_results(callback: CallbackQuery, archetype: str, user_id: int, lang: str):
    """Генерация персонализированного экрана результатов теста с оффером"""
    profile = quiz_service.get_profile(archetype)
    if not profile:
        profile = quiz_service.get_profile("it")

    recommended_offer = offer_service.get_offer_by_id(profile.recommended_offer_id)
    if not recommended_offer:
        active = offer_service.get_active_offers()
        recommended_offer = active[0] if active else None

    header = i18n.get("quiz_result_header", lang)
    p_title = profile.get_title(lang)
    p_desc = profile.get_description(lang)
    rec_label = i18n.get("quiz_recommended_offer_label", lang)

    rec_offer_title = recommended_offer.get_title(lang) if recommended_offer else ""
    rec_offer_desc = recommended_offer.get_description(lang) if recommended_offer else ""

    perks = (
        "• Доступна рассрочка через <b>Kaspi 0-0-12 / 0-0-24</b>\n"
        "• Для подробной информации и фиксации условий нажмите кнопку ниже:"
    ) if lang == "ru" else (
        "• <b>Kaspi 0-0-12 / 0-0-24 бөліп төлеу</b> қарастырылған\n"
        "• Толық ақпарат алу және шарттарды бекіту үшін төмендегі батырманы басыңыз:"
    )

    message_text = (
        f"{header}\n\n"
        f"<b>{p_title}</b>\n\n"
        f"{p_desc}\n\n"
        f"{rec_label}\n"
        f"🎓 <b>{rec_offer_title}</b>\n"
        f"{rec_offer_desc}\n\n"
        f"{perks}"
    )

    keyboard = get_quiz_result_keyboard(
        recommended_offer=recommended_offer,
        user_id=user_id,
        lang=lang
    )

    await callback.answer()
    if callback.message:
        await callback.message.edit_text(
            text=message_text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )

@router.callback_query(F.data == "quiz:show_result")
async def on_quiz_show_result(callback: CallbackQuery, state: FSMContext):
    """Возврат к экрану результатов теста (из каталога всех курсов)"""
    user_id = callback.from_user.id
    lang = await UserService.get_user_language(user_id)
    data = await state.get_data()
    archetype = data.get("last_archetype")

    if not archetype:
        archetype = await UserService.get_user_test_result(user_id) or "it"

    await show_quiz_results(callback=callback, archetype=archetype, user_id=user_id, lang=lang)

# ==================== КАТАЛОГ ВСЕХ КУРСОВ ====================

@router.callback_query(F.data == "courses:all_from_quiz")
async def on_all_courses_from_quiz(callback: CallbackQuery):
    """Просмотр всех курсов после прохождения теста (чтобы не срезать конверсии)"""
    user_id = callback.from_user.id
    lang = await UserService.get_user_language(user_id)

    text = (
        "📚 <b>Каталог всех доступных программ со скидками:</b>\n\n"
        "Вы можете ознакомиться с любым другим направлением. "
        "Для всех программ доступна рассрочка <b>Kaspi 0-0-12 / 0-0-24</b>:"
    ) if lang == "ru" else (
        "📚 <b>Барлық қолжетімді білім беру бағдарламалары:</b>\n\n"
        "Кез келген басқа бағытпен таныса аласыз. "
        "Барлық курстарға <b>Kaspi 0-0-12 / 0-0-24 бөліп төлеу</b> қарастырылған:"
    )

    keyboard = get_all_courses_keyboard(lang=lang, from_quiz=True)
    await callback.answer()
    if callback.message:
        await callback.message.edit_text(
            text=text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )

# ==================== КАРТОЧКА ОФФЕРА ====================

@router.callback_query(F.data.startswith("offer:"))
async def on_offer_clicked(callback: CallbackQuery):
    """
    Обработчик клика по офферу:
    offer:<offer_id>:<back_target>
    """
    parts = callback.data.split(":")
    offer_id = parts[1]
    back_target = parts[2] if len(parts) > 2 else "menu:back"
    user_id = callback.from_user.id

    # Аналитика и трекинг клика в базе данных
    await UserService.track_offer_click(user_id=user_id, offer_id=offer_id)

    lang = await UserService.get_user_language(user_id)
    offer = offer_service.get_offer_by_id(offer_id)
    if not offer:
        await callback.answer("Оффер временно недоступен", show_alert=True)
        return

    await callback.answer()

    title = offer.get_title(lang)
    description = offer.get_description(lang)

    header = i18n.get("offer_details_title", lang=lang, title=title)
    body = i18n.get("offer_details_body", lang=lang, description=description)
    message_text = f"{header}\n\n{body}"

    keyboard = get_offer_details_keyboard(
        offer=offer,
        user_id=user_id,
        lang=lang,
        back_target=back_target
    )

    if callback.message:
        await callback.message.edit_text(
            text=message_text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )

# ==================== НАВИГАЦИЯ ====================

@router.callback_query(F.data == "menu:back")
async def on_back_to_menu(callback: CallbackQuery, state: FSMContext):
    """Возврат в главное меню"""
    await state.clear()
    user_id = callback.from_user.id
    lang = await UserService.get_user_language(user_id)

    menu_text = i18n.get("main_menu_text", lang=lang)
    keyboard = get_main_menu_keyboard(lang=lang, user_id=user_id)

    await callback.answer()
    if callback.message:
        await callback.message.edit_text(
            text=menu_text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )

@router.callback_query(F.data == "change_lang")
async def on_change_language_request(callback: CallbackQuery, state: FSMContext):
    """Смена языка"""
    await state.clear()
    text = i18n.get("choose_language", lang="ru")
    await callback.answer()
    if callback.message:
        await callback.message.edit_text(
            text=text,
            reply_markup=get_language_keyboard(),
            parse_mode="HTML"
        )
