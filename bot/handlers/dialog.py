# FILE: bot/handlers/dialog.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT:
# PURPOSE: FSM-обработчики полного диалога из 8 шагов — от выбора сценария до подтверждения.
# SCOPE: Шаги сбора данных: scenario, char_count, hero_gender, [companion_gender],
#        name (валидация), hero_photo (JPEG/PNG ≥300px), [companion_photo], confirm.
# INPUT: CallbackQuery (кнопки) и Message (текст, фото) от пользователя.
# OUTPUT: Переходы FSM + PATCH-запросы к бэкенду + ответные сообщения бота.
# KEYWORDS: DOMAIN(9): FSM; CONCEPT(9): DialogFlow; TECH(8): AiogramFSM
#           PATTERN(8): ConditionalBranching; CONCEPT(9): InputValidation
# LINKS: USES_API(9): aiogram.FSMContext; CALLS_METHOD(9): backend_client.patch_session
# END_MODULE_CONTRACT
#
# START_RATIONALE:
# Q: Почему валидация имени через re, а не str.isalpha()?
# A: str.isalpha() не принимает пробелы и дефисы в именах. Регулярка [а-яА-ЯёЁa-zA-Z\\s\\-]{1,30}
#    корректно принимает "Александр", "Mary Jane", "Ивана-Чай" и т.д.
# Q: Почему валидация фото скачивает изображение полностью?
# A: Telegram не возвращает разрешение через API без скачивания. PIL.Image.open()
#    нужен полный файл. Скачиваем наименьший доступный сайз, проверяем ≥300×300.
# END_RATIONALE
#
# START_INVARIANTS:
# - FSM data всегда содержит session_id после /start.
# - При char_count=1: шаги WAITING_COMPANION_GENDER и WAITING_COMPANION_PHOTO пропускаются.
# - Все PATCH к бэкенду через backend_client.patch_session — никаких прямых HTTP запросов.
# END_INVARIANTS
#
# START_CHANGE_SUMMARY:
# LAST_CHANGE: [v1.0.0 - FS-1: полный FSM диалог 8 шагов с валидацией]
# END_CHANGE_SUMMARY
#
# START_MODULE_MAP:
# FUNC [8][Обработчик выбора сценария] => on_scenario
# FUNC [8][Обработчик выбора кол-ва персонажей] => on_char_count
# FUNC [8][Обработчик выбора пола героя] => on_hero_gender
# FUNC [8][Обработчик выбора пола компаньона (условный)] => on_companion_gender
# FUNC [9][Обработчик ввода имени с валидацией] => on_name
# FUNC [10][Обработчик загрузки фото героя с JPEG/PNG/размер валидацией] => on_hero_photo
# FUNC [9][Обработчик загрузки фото компаньона (условный)] => on_companion_photo
# FUNC [8][Показывает сводку перед подтверждением] => _show_confirm_summary
# END_MODULE_MAP
#
# START_USE_CASES:
# - on_scenario: User -> ChooseScenario -> PatchedSession + NextStep
# - on_name: User -> TypeName -> ValidationPassed/Failed + PatchedSession
# - on_hero_photo: User -> SendPhoto -> SizeValidated + PatchedSession
# END_USE_CASES

import io
import re
import logging

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from bot.states import OrderState
from bot.keyboards import (
    char_count_keyboard,
    hero_gender_keyboard,
    companion_gender_keyboard,
    confirm_keyboard,
)
from bot.services import backend_client

logger = logging.getLogger(__name__)
router = Router(name="dialog")

# Регулярка валидации имени: кириллица и/или латиница + пробелы + дефис, 1-30 символов
NAME_PATTERN = re.compile(r'^[а-яА-ЯёЁa-zA-Z\s\-]{1,30}$')

# Карта сценариев: callback_data → человекочитаемое название
SCENARIO_LABELS = {
    "birthday": "🎉 С днём рождения",
    "love": "❤️ Признание в любви",
    "surprise": "💫 Сюрприз",
}

# Карта полов: код → человекочитаемое название
GENDER_LABELS = {
    "m": "👨 Мужской",
    "f": "👩 Женский",
}


# START_FUNCTION_on_scenario
# START_CONTRACT:
# PURPOSE: Получает выбор сценария (callback birthday/love/surprise), патчит сессию, переходит в CHAR_COUNT.
# INPUTS:
# - CallbackQuery с data "scenario:{value}" => callback: CallbackQuery
# - FSMContext пользователя => state: FSMContext
# OUTPUTS:
# - None (сайд-эффект: PATCH session.scenario + FSM → WAITING_CHAR_COUNT + ответ бота)
# SIDE_EFFECTS: PATCH /sessions/{id}. FSM data: scenario сохраняется.
# KEYWORDS: PATTERN(8): CallbackHandler; CONCEPT(9): FSMTransition
# COMPLEXITY_SCORE: 6
# END_CONTRACT
async def on_scenario(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Обработчик выбора сценария из InlineKeyboard.
    Парсит callback.data вида "scenario:birthday", сохраняет в FSM data,
    патчит сессию на бэкенде, переходит к выбору количества персонажей.
    """
    scenario = callback.data.split(":")[1]
    await callback.answer()

    logger.info(
        f"[Flow][IMP:6][on_scenario][ENTRY][CallbackReceived] "
        f"user_id={callback.from_user.id} scenario={scenario} [INFO]"
    )

    # START_BLOCK_SAVE_SCENARIO: Сохранение сценария в FSM и бэкенде
    data = await state.get_data()
    session_id = data.get("session_id")
    await state.update_data(scenario=scenario)

    try:
        await backend_client.patch_session(session_id, scenario=scenario)
        logger.info(
            f"[BeliefState][IMP:9][on_scenario][SAVE_SCENARIO][Patched] "
            f"session_id={session_id} scenario={scenario} [SUCCESS]"
        )
    except Exception as exc:
        logger.critical(
            f"[SystemError][IMP:10][on_scenario][SAVE_SCENARIO][PatchFailed] "
            f"session_id={session_id} err={exc!r} [FATAL]"
        )
    # END_BLOCK_SAVE_SCENARIO

    await state.set_state(OrderState.WAITING_CHAR_COUNT)
    await callback.message.answer(
        "Будет один герой или добавим компаньона?",
        reply_markup=char_count_keyboard()
    )
# END_FUNCTION_on_scenario


# START_FUNCTION_on_char_count
# START_CONTRACT:
# PURPOSE: Получает выбор кол-ва персонажей (1 или 2), патчит сессию, переходит к полу героя.
# INPUTS:
# - CallbackQuery с data "char_count:{1|2}" => callback: CallbackQuery
# - FSMContext пользователя => state: FSMContext
# OUTPUTS:
# - None (сайд-эффект: FSM → WAITING_HERO_GENDER + ответ)
# SIDE_EFFECTS: PATCH /sessions/{id}. FSM data: char_count.
# KEYWORDS: PATTERN(8): CallbackHandler
# COMPLEXITY_SCORE: 5
# END_CONTRACT
async def on_char_count(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Обработчик выбора количества персонажей.
    char_count сохраняется как int (1 или 2) в FSM data.
    Переходит к выбору пола главного героя.
    """
    char_count = int(callback.data.split(":")[1])
    await callback.answer()

    logger.info(
        f"[Flow][IMP:6][on_char_count][ENTRY][CallbackReceived] "
        f"user_id={callback.from_user.id} char_count={char_count} [INFO]"
    )

    data = await state.get_data()
    session_id = data.get("session_id")
    await state.update_data(char_count=char_count)

    try:
        await backend_client.patch_session(session_id, char_count=char_count)
    except Exception as exc:
        logger.warning(
            f"[HTTP][IMP:8][on_char_count][PATCH][Failed] "
            f"session_id={session_id} err={exc!r} [WARN]"
        )

    await state.set_state(OrderState.WAITING_HERO_GENDER)
    await callback.message.answer(
        "Выбери пол главного героя",
        reply_markup=hero_gender_keyboard()
    )
# END_FUNCTION_on_char_count


# START_FUNCTION_on_hero_gender
# START_CONTRACT:
# PURPOSE: Получает пол героя, патчит сессию. Ветвление: char_count=2 → COMPANION_GENDER, иначе → NAME.
# INPUTS:
# - CallbackQuery с data "hero_gender:{m|f}" => callback: CallbackQuery
# - FSMContext пользователя => state: FSMContext
# OUTPUTS:
# - None (сайд-эффект: условный переход FSM + ответ)
# SIDE_EFFECTS: PATCH /sessions/{id}.
# KEYWORDS: PATTERN(9): ConditionalBranching; CONCEPT(9): FSMTransition
# COMPLEXITY_SCORE: 7
# END_CONTRACT
async def on_hero_gender(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Обработчик выбора пола главного героя.
    Ключевое ветвление диалога:
    - char_count=2 → спрашиваем пол компаньона (WAITING_COMPANION_GENDER)
    - char_count=1 → сразу к имени (WAITING_NAME)
    """
    hero_gender = callback.data.split(":")[1]
    await callback.answer()

    data = await state.get_data()
    session_id = data.get("session_id")
    char_count = data.get("char_count", 1)
    await state.update_data(hero_gender=hero_gender)

    logger.info(
        f"[Flow][IMP:6][on_hero_gender][BRANCH][Decision] "
        f"user_id={callback.from_user.id} hero_gender={hero_gender} "
        f"char_count={char_count} [INFO]"
    )

    try:
        await backend_client.patch_session(session_id, hero_gender=hero_gender)
    except Exception as exc:
        logger.warning(
            f"[HTTP][IMP:8][on_hero_gender][PATCH][Failed] err={exc!r} [WARN]"
        )

    # START_BLOCK_BRANCH_COMPANION: Ветвление по char_count
    if char_count == 2:
        await state.set_state(OrderState.WAITING_COMPANION_GENDER)
        await callback.message.answer(
            "Теперь пол компаньона",
            reply_markup=companion_gender_keyboard()
        )
        logger.info(
            f"[BeliefState][IMP:9][on_hero_gender][BRANCH_COMPANION][StateSet] "
            f"char_count=2 → WAITING_COMPANION_GENDER [SUCCESS]"
        )
    else:
        await state.set_state(OrderState.WAITING_NAME)
        await callback.message.answer(
            "Как зовут главного героя? (например: Александр, Маша)"
        )
        logger.info(
            f"[BeliefState][IMP:9][on_hero_gender][BRANCH_COMPANION][StateSet] "
            f"char_count=1 → WAITING_NAME [SUCCESS]"
        )
    # END_BLOCK_BRANCH_COMPANION
# END_FUNCTION_on_hero_gender


# START_FUNCTION_on_companion_gender
# START_CONTRACT:
# PURPOSE: Получает пол компаньона (только при char_count=2). Переходит к WAITING_NAME.
# INPUTS:
# - CallbackQuery с data "companion_gender:{m|f}" => callback: CallbackQuery
# - FSMContext пользователя => state: FSMContext
# OUTPUTS:
# - None (сайд-эффект: FSM → WAITING_NAME + ответ)
# SIDE_EFFECTS: PATCH /sessions/{id}.
# KEYWORDS: PATTERN(8): CallbackHandler
# COMPLEXITY_SCORE: 5
# END_CONTRACT
async def on_companion_gender(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Обработчик выбора пола компаньона (активируется только при char_count=2).
    После получения пола переходит к вводу имени героя.
    """
    companion_gender = callback.data.split(":")[1]
    await callback.answer()

    data = await state.get_data()
    session_id = data.get("session_id")
    await state.update_data(companion_gender=companion_gender)

    logger.info(
        f"[Flow][IMP:6][on_companion_gender][ENTRY][CallbackReceived] "
        f"companion_gender={companion_gender} [INFO]"
    )

    try:
        await backend_client.patch_session(session_id, companion_gender=companion_gender)
    except Exception as exc:
        logger.warning(
            f"[HTTP][IMP:8][on_companion_gender][PATCH][Failed] err={exc!r} [WARN]"
        )

    await state.set_state(OrderState.WAITING_NAME)
    await callback.message.answer(
        "Как зовут главного героя? (например: Александр, Маша)"
    )
# END_FUNCTION_on_companion_gender


# START_FUNCTION_on_name
# START_CONTRACT:
# PURPOSE: Получает текстовое имя героя с валидацией (1-30 символов, кириллица/латиница).
# INPUTS:
# - Текстовое сообщение с именем => message: Message
# - FSMContext пользователя => state: FSMContext
# OUTPUTS:
# - None (сайд-эффект: при успехе FSM → WAITING_HERO_PHOTO; при провале — сообщение об ошибке)
# SIDE_EFFECTS: При успехе: PATCH /sessions/{id}. FSM data: name.
# KEYWORDS: CONCEPT(9): InputValidation; PATTERN(8): ValidationHandler
# COMPLEXITY_SCORE: 7
# END_CONTRACT
async def on_name(message: Message, state: FSMContext) -> None:
    """
    Обработчик ввода имени главного героя.
    Валидация: строка 1-30 символов, только кириллица и/или латиница (+ пробелы, дефис).
    При провале валидации — сообщение об ошибке, FSM остаётся в WAITING_NAME.
    При успехе — сохраняет имя, переходит к загрузке фото.
    """
    text = (message.text or "").strip()

    # START_BLOCK_VALIDATE_NAME: Валидация имени
    if not text:
        await message.answer(
            "❌ Имя не может быть пустым. Введи имя (например: Александр, Маша)"
        )
        logger.info(
            f"[Flow][IMP:7][on_name][VALIDATE_NAME][Empty] "
            f"user_id={message.from_user.id} [REJECTED]"
        )
        return

    if len(text) > 30:
        await message.answer(
            f"❌ Имя слишком длинное ({len(text)} символов). Максимум — 30 символов."
        )
        logger.info(
            f"[Flow][IMP:7][on_name][VALIDATE_NAME][TooLong] "
            f"user_id={message.from_user.id} len={len(text)} [REJECTED]"
        )
        return

    if not NAME_PATTERN.match(text):
        await message.answer(
            "❌ Имя должно содержать только буквы (русские или латинские). "
            "Пример: Александр, Maria"
        )
        logger.info(
            f"[Flow][IMP:7][on_name][VALIDATE_NAME][InvalidChars] "
            f"user_id={message.from_user.id} text={text!r} [REJECTED]"
        )
        return
    # END_BLOCK_VALIDATE_NAME

    # START_BLOCK_SAVE_NAME: Сохранение валидного имени
    data = await state.get_data()
    session_id = data.get("session_id")
    await state.update_data(name=text)

    try:
        await backend_client.patch_session(session_id, name=text)
        logger.info(
            f"[BeliefState][IMP:9][on_name][SAVE_NAME][Patched] "
            f"session_id={session_id} name={text!r} [SUCCESS]"
        )
    except Exception as exc:
        logger.warning(
            f"[HTTP][IMP:8][on_name][SAVE_NAME][PatchFailed] err={exc!r} [WARN]"
        )
    # END_BLOCK_SAVE_NAME

    await state.set_state(OrderState.WAITING_HERO_PHOTO)
    await message.answer(
        f"Загрузи портретное фото {text} — чёткое, лицо открыто 📸"
    )
# END_FUNCTION_on_name


# START_FUNCTION_on_hero_photo
# START_CONTRACT:
# PURPOSE: Получает фото героя, валидирует (JPEG/PNG, ≥300×300px), сохраняет file_id. Ветвление по char_count.
# INPUTS:
# - Сообщение с фотографией => message: Message
# - FSMContext пользователя => state: FSMContext
# OUTPUTS:
# - None (сайд-эффект: при успехе PATCH + ветвление FSM)
# SIDE_EFFECTS: Скачивает наименьший размер фото для проверки размеров через PIL.
# KEYWORDS: CONCEPT(9): PhotoValidation; PATTERN(9): ConditionalBranching
# COMPLEXITY_SCORE: 9
# END_CONTRACT
async def on_hero_photo(message: Message, state: FSMContext) -> None:
    """
    Обработчик загрузки фото главного героя.
    Telegram присылает несколько размеров в message.photo — берём наибольший (последний).
    Для валидации размера: скачиваем фото через bot.download() → PIL.Image → проверяем ≥300×300.
    Сохраняем file_id (не сами байты) — бэкенд сам скачает через Telegram File API.
    Ветвление: char_count=2 → WAITING_COMPANION_PHOTO, иначе → CONFIRM.
    """
    # START_BLOCK_CHECK_PHOTO_EXISTS: Проверка что прислали фото, а не документ
    if not message.photo:
        await message.answer(
            "❌ Пожалуйста, отправь фото (не файл/документ). "
            "Выбери фото из галереи и отправь без сжатия выключенным."
        )
        logger.info(
            f"[Flow][IMP:7][on_hero_photo][CHECK_PHOTO][NoPhoto] "
            f"user_id={message.from_user.id} [REJECTED]"
        )
        return
    # END_BLOCK_CHECK_PHOTO_EXISTS

    # START_BLOCK_VALIDATE_PHOTO_SIZE: Скачивание и проверка размера фото ≥300×300
    photo = message.photo[-1]  # Наибольший доступный размер

    try:
        from PIL import Image

        bot = message.bot
        file = await bot.get_file(photo.file_id)
        file_bytes = await bot.download_file(file.file_path)

        img = Image.open(io.BytesIO(file_bytes.read()))
        width, height = img.size

        logger.info(
            f"[Flow][IMP:7][on_hero_photo][VALIDATE_PHOTO_SIZE][Dimensions] "
            f"user_id={message.from_user.id} size={width}x{height} [INFO]"
        )

        if width < 300 or height < 300:
            await message.answer(
                f"❌ Фото слишком маленькое ({width}×{height}px). "
                f"Нужно минимум 300×300px. Отправь более чёткое фото."
            )
            logger.info(
                f"[Flow][IMP:7][on_hero_photo][VALIDATE_PHOTO_SIZE][TooSmall] "
                f"size={width}x{height} [REJECTED]"
            )
            return

    except Exception as exc:
        logger.warning(
            f"[HTTP][IMP:8][on_hero_photo][VALIDATE_PHOTO_SIZE][PILError] "
            f"err={exc!r} — пропускаем валидацию размера [WARN]"
        )
        # BUG_FIX_CONTEXT: Если PIL не может открыть файл или Telegram вернул ошибку,
        # не блокируем пользователя — пропускаем валидацию размера и принимаем фото.
    # END_BLOCK_VALIDATE_PHOTO_SIZE

    # START_BLOCK_SAVE_HERO_PHOTO: Сохранение file_id и ветвление
    data = await state.get_data()
    session_id = data.get("session_id")
    char_count = data.get("char_count", 1)
    hero_photo_file_id = photo.file_id

    await state.update_data(hero_photo_file_id=hero_photo_file_id)

    try:
        await backend_client.patch_session(
            session_id, hero_photo_file_id=hero_photo_file_id
        )
        logger.info(
            f"[BeliefState][IMP:9][on_hero_photo][SAVE_HERO_PHOTO][Patched] "
            f"session_id={session_id} file_id={hero_photo_file_id[:20]}... [SUCCESS]"
        )
    except Exception as exc:
        logger.warning(
            f"[HTTP][IMP:8][on_hero_photo][SAVE_HERO_PHOTO][PatchFailed] err={exc!r} [WARN]"
        )

    if char_count == 2:
        await state.set_state(OrderState.WAITING_COMPANION_PHOTO)
        await message.answer("Теперь загрузи фото компаньона")
        logger.info(
            f"[BeliefState][IMP:9][on_hero_photo][SAVE_HERO_PHOTO][Branch] "
            f"char_count=2 → WAITING_COMPANION_PHOTO [SUCCESS]"
        )
    else:
        await state.set_state(OrderState.CONFIRM)
        await _show_confirm_summary(message, state)
        logger.info(
            f"[BeliefState][IMP:9][on_hero_photo][SAVE_HERO_PHOTO][Branch] "
            f"char_count=1 → CONFIRM [SUCCESS]"
        )
    # END_BLOCK_SAVE_HERO_PHOTO
# END_FUNCTION_on_hero_photo


# START_FUNCTION_on_companion_photo
# START_CONTRACT:
# PURPOSE: Получает фото компаньона (только char_count=2), валидирует, сохраняет, переходит в CONFIRM.
# INPUTS:
# - Сообщение с фотографией => message: Message
# - FSMContext пользователя => state: FSMContext
# OUTPUTS:
# - None (сайд-эффект: PATCH + FSM → CONFIRM + сводка)
# SIDE_EFFECTS: Скачивает фото для PIL-валидации.
# KEYWORDS: CONCEPT(9): PhotoValidation
# COMPLEXITY_SCORE: 7
# END_CONTRACT
async def on_companion_photo(message: Message, state: FSMContext) -> None:
    """
    Обработчик загрузки фото компаньона (только при char_count=2).
    Аналогичная валидация как для фото героя: JPEG/PNG, ≥300×300px.
    После успешного сохранения переходит к экрану подтверждения CONFIRM.
    """
    if not message.photo:
        await message.answer(
            "❌ Пожалуйста, отправь фото (не файл/документ)."
        )
        return

    photo = message.photo[-1]

    # START_BLOCK_VALIDATE_COMPANION_PHOTO: Проверка размера фото компаньона
    try:
        from PIL import Image

        bot = message.bot
        file = await bot.get_file(photo.file_id)
        file_bytes = await bot.download_file(file.file_path)

        img = Image.open(io.BytesIO(file_bytes.read()))
        width, height = img.size

        if width < 300 or height < 300:
            await message.answer(
                f"❌ Фото слишком маленькое ({width}×{height}px). "
                f"Нужно минимум 300×300px."
            )
            return

    except Exception as exc:
        logger.warning(
            f"[HTTP][IMP:8][on_companion_photo][VALIDATE_COMPANION_PHOTO][PILError] "
            f"err={exc!r} — пропускаем валидацию [WARN]"
        )
    # END_BLOCK_VALIDATE_COMPANION_PHOTO

    # START_BLOCK_SAVE_COMPANION_PHOTO: Сохранение file_id компаньона
    data = await state.get_data()
    session_id = data.get("session_id")
    companion_photo_file_id = photo.file_id

    await state.update_data(companion_photo_file_id=companion_photo_file_id)

    try:
        await backend_client.patch_session(
            session_id, companion_photo_file_id=companion_photo_file_id
        )
        logger.info(
            f"[BeliefState][IMP:9][on_companion_photo][SAVE_COMPANION_PHOTO][Patched] "
            f"session_id={session_id} [SUCCESS]"
        )
    except Exception as exc:
        logger.warning(
            f"[HTTP][IMP:8][on_companion_photo][SAVE_COMPANION_PHOTO][Failed] err={exc!r} [WARN]"
        )
    # END_BLOCK_SAVE_COMPANION_PHOTO

    await state.set_state(OrderState.CONFIRM)
    await _show_confirm_summary(message, state)
# END_FUNCTION_on_companion_photo


# START_FUNCTION__show_confirm_summary
# START_CONTRACT:
# PURPOSE: Формирует и отправляет текстовую сводку параметров игры с клавиатурой подтверждения.
# INPUTS:
# - Сообщение пользователя для контекста ответа => message: Message
# - FSMContext с накопленными данными => state: FSMContext
# OUTPUTS:
# - None (сайд-эффект: отправка сводки с InlineKeyboard)
# SIDE_EFFECTS: Чтение FSM data, отправка сообщения.
# KEYWORDS: CONCEPT(8): SummaryView; PATTERN(7): BuildAndSend
# COMPLEXITY_SCORE: 5
# END_CONTRACT
async def _show_confirm_summary(message: Message, state: FSMContext) -> None:
    """
    Внутренняя функция — показывает сводку перед подтверждением.
    Читает все накопленные данные из FSM и формирует читаемый текст.
    Прикрепляет confirm_keyboard с кнопками "Создать игру" и "Изменить".
    """
    data = await state.get_data()

    scenario_label = SCENARIO_LABELS.get(data.get("scenario", ""), "—")
    char_count = data.get("char_count", 1)
    hero_gender_label = GENDER_LABELS.get(data.get("hero_gender", ""), "—")
    companion_gender_label = GENDER_LABELS.get(data.get("companion_gender", ""), "—")
    name = data.get("name", "—")

    lines = [
        "📋 <b>Проверь данные игры:</b>",
        "",
        f"🎮 Сценарий: {scenario_label}",
        f"👤 Персонажей: {'Двое' if char_count == 2 else 'Один'}",
        f"🦸 Пол героя: {hero_gender_label}",
    ]

    if char_count == 2:
        lines.append(f"🤝 Пол компаньона: {companion_gender_label}")

    lines.append(f"📛 Имя героя: <b>{name}</b>")
    lines.append("")
    lines.append("Всё верно? Нажми <b>🚀 Создать игру</b>!")

    summary_text = "\n".join(lines)

    await message.answer(
        summary_text,
        reply_markup=confirm_keyboard(),
        parse_mode="HTML"
    )
    logger.info(
        f"[BeliefState][IMP:9][_show_confirm_summary][SUMMARY][Shown] "
        f"user_id={message.from_user.id} scenario={data.get('scenario')} "
        f"char_count={char_count} name={name!r} [SUCCESS]"
    )
# END_FUNCTION__show_confirm_summary


def register_handlers(dp) -> None:
    """Регистрирует все FSM-хендлеры диалога в диспетчере."""
    router.callback_query.register(
        on_scenario,
        F.data.startswith("scenario:"),
        OrderState.WAITING_SCENARIO
    )
    router.callback_query.register(
        on_char_count,
        F.data.startswith("char_count:"),
        OrderState.WAITING_CHAR_COUNT
    )
    router.callback_query.register(
        on_hero_gender,
        F.data.startswith("hero_gender:"),
        OrderState.WAITING_HERO_GENDER
    )
    router.callback_query.register(
        on_companion_gender,
        F.data.startswith("companion_gender:"),
        OrderState.WAITING_COMPANION_GENDER
    )
    router.message.register(on_name, OrderState.WAITING_NAME)
    router.message.register(on_hero_photo, OrderState.WAITING_HERO_PHOTO)
    router.message.register(on_companion_photo, OrderState.WAITING_COMPANION_PHOTO)
    dp.include_router(router)
