# FILE: bot/handlers/generation.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT:
# PURPOSE: Обработчики callback действий после подтверждения: запуск генерации, получение game_url, регенерация.
# SCOPE: Кнопки "🚀 Создать игру", "✅ Запустить игру", "🔄 Перегенерировать".
#        Polling GET /sessions/{id} с интервалом 5 сек до 3 мин для получения game_url.
# INPUT: CallbackQuery от InlineKeyboard.
# OUTPUT: Запуск генерации + polling + отправка game_url или уведомление о повторной генерации.
# KEYWORDS: DOMAIN(9): Generation; CONCEPT(9): AsyncPolling; TECH(8): AiogramCallback
#           PATTERN(9): FireAndMonitor
# LINKS: CALLS_METHOD(9): backend_client.trigger_generation; CALLS_METHOD(9): backend_client.get_game_url
# END_MODULE_CONTRACT
#
# START_RATIONALE:
# Q: Почему polling а не webhook от бэкенда?
# A: FS-1 — тест-версия без бэкенда. Polling GET /sessions/{id} — наиболее простой
#    механизм, не требующий изменений на стороне бэкенда.
# Q: Почему asyncio.sleep внутри хендлера?
# A: aiogram использует asyncio event loop — await asyncio.sleep() не блокирует
#    обработку других сообщений. Polling корутина запускается как asyncio.create_task.
# END_RATIONALE
#
# START_CHANGE_SUMMARY:
# LAST_CHANGE: [v1.0.0 - FS-1: create_game, launch_game, regenerate. Polling 5s/3min]
# END_CHANGE_SUMMARY
#
# START_MODULE_MAP:
# FUNC [9][Обработчик кнопки "Создать игру" — запускает trigger_generation] => on_create_game
# FUNC [9][Обработчик кнопки "Запустить игру" — polling game_url и отправка ссылки] => on_launch_game
# FUNC [8][Обработчик кнопки "Перегенерировать" — бесплатная регенерация в тест] => on_regenerate
# FUNC [9][Корутина polling game_url с таймаутом 3 мин] => _poll_game_url
# END_MODULE_MAP

import asyncio
import logging

from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext

from bot.states import OrderState
from bot.keyboards import post_generation_keyboard
from bot.services import backend_client

logger = logging.getLogger(__name__)
router = Router(name="generation")

# Параметры polling
POLL_INTERVAL_SECONDS = 5
POLL_TIMEOUT_SECONDS = 180  # 3 минуты


# START_FUNCTION_on_create_game
# START_CONTRACT:
# PURPOSE: Обрабатывает нажатие "🚀 Создать игру" — запускает trigger_generation, уведомляет пользователя.
# INPUTS:
# - CallbackQuery с data "action:create_game" => callback: CallbackQuery
# - FSMContext пользователя => state: FSMContext
# OUTPUTS:
# - None (сайд-эффект: POST /games/build + сообщение "Запускаю генерацию...")
# SIDE_EFFECTS: Запускает asyncio task _poll_game_url для мониторинга результата.
# KEYWORDS: CONCEPT(9): TriggerGeneration; PATTERN(8): FireAndMonitor
# COMPLEXITY_SCORE: 7
# END_CONTRACT
async def on_create_game(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Обработчик кнопки "🚀 Создать игру" в экране подтверждения.
    1. Получает session_id из FSM data.
    2. Вызывает backend_client.trigger_generation(session_id).
    3. Уведомляет пользователя о начале генерации (~60 сек).
    4. Запускает фоновую задачу _poll_game_url для polling результата.
    """
    await callback.answer()
    data = await state.get_data()
    session_id = data.get("session_id")
    user_id = callback.from_user.id

    logger.info(
        f"[Flow][IMP:6][on_create_game][ENTRY][CreateGamePressed] "
        f"user_id={user_id} session_id={session_id} [INFO]"
    )

    # START_BLOCK_TRIGGER_GENERATION: Запуск генерации
    try:
        await backend_client.trigger_generation(session_id)
        await callback.message.answer(
            "Запускаю генерацию персонажей... ~60 сек ⏳\n"
            "Я отправлю ссылку как только игра будет готова!"
        )
        logger.info(
            f"[BeliefState][IMP:9][on_create_game][TRIGGER_GENERATION][Started] "
            f"session_id={session_id} [SUCCESS]"
        )
    except Exception as exc:
        logger.critical(
            f"[SystemError][IMP:10][on_create_game][TRIGGER_GENERATION][Failed] "
            f"session_id={session_id} err={exc!r} [FATAL]"
        )
        await callback.message.answer(
            "⚠️ Не удалось запустить генерацию. Попробуй ещё раз через /new"
        )
        return
    # END_BLOCK_TRIGGER_GENERATION

    # START_BLOCK_START_POLLING: Запуск фоновой задачи polling
    asyncio.create_task(
        _poll_game_url(
            chat_id=callback.message.chat.id,
            session_id=session_id,
            bot=callback.bot,
        )
    )
    logger.info(
        f"[Flow][IMP:7][on_create_game][START_POLLING][TaskCreated] "
        f"session_id={session_id} poll_interval={POLL_INTERVAL_SECONDS}s "
        f"timeout={POLL_TIMEOUT_SECONDS}s [INFO]"
    )
    # END_BLOCK_START_POLLING
# END_FUNCTION_on_create_game


# START_FUNCTION__poll_game_url
# START_CONTRACT:
# PURPOSE: Фоновая корутина polling GET /sessions/{id} каждые 5 сек до 3 мин.
#          При получении game_url — отправляет ссылку пользователю.
# INPUTS:
# - Telegram chat_id для отправки результата => chat_id: int
# - UUID сессии для polling => session_id: str
# - aiogram Bot instance для отправки сообщений => bot
# OUTPUTS:
# - None (сайд-эффект: отправка сообщения с game_url или уведомление о timeout)
# SIDE_EFFECTS: Multiple GET /sessions/{id} запросы с интервалом 5 сек.
# KEYWORDS: CONCEPT(9): Polling; PATTERN(9): BackgroundTask; CONCEPT(8): Timeout
# COMPLEXITY_SCORE: 8
# END_CONTRACT
async def _poll_game_url(chat_id: int, session_id: str, bot) -> None:
    """
    Фоновая корутина для polling результата генерации.
    Опрашивает GET /sessions/{session_id} каждые POLL_INTERVAL_SECONDS секунд.
    При получении непустого game_url — отправляет ссылку и кнопки пользователю.
    При истечении POLL_TIMEOUT_SECONDS — уведомляет об ошибке.
    """
    elapsed = 0

    logger.info(
        f"[Flow][IMP:7][_poll_game_url][POLLING_START][Begin] "
        f"session_id={session_id} timeout={POLL_TIMEOUT_SECONDS}s [INFO]"
    )

    # START_BLOCK_POLL_LOOP: Цикл опроса с таймаутом
    while elapsed < POLL_TIMEOUT_SECONDS:
        await asyncio.sleep(POLL_INTERVAL_SECONDS)
        elapsed += POLL_INTERVAL_SECONDS

        game_url, pipeline_error = await backend_client.get_game_url(session_id)

        logger.info(
            f"[Flow][IMP:7][_poll_game_url][POLL_LOOP][Check] "
            f"session_id={session_id} elapsed={elapsed}s "
            f"game_url={game_url!r} pipeline_error={pipeline_error!r} [INFO]"
        )

        if game_url:
            await bot.send_message(
                chat_id=chat_id,
                text=(
                    f"🎉 Игра готова!\n\n"
                    f"🔗 <a href='{game_url}'>Открыть игру</a>\n\n"
                    f"Выбери действие:"
                ),
                reply_markup=post_generation_keyboard(),
                parse_mode="HTML"
            )
            logger.info(
                f"[BeliefState][IMP:9][_poll_game_url][POLL_LOOP][GameReady] "
                f"session_id={session_id} game_url={game_url} elapsed={elapsed}s [SUCCESS]"
            )
            return

        # BUG_FIX_CONTEXT: Ранее pipeline_error игнорировался — бот ждал 180 сек даже когда
        # бэкенд уже упал через 5 сек. Теперь при наличии ошибки — немедленный выход.
        if pipeline_error:
            logger.error(
                f"[SystemError][IMP:10][_poll_game_url][POLL_LOOP][PipelineError] "
                f"session_id={session_id} elapsed={elapsed}s error={pipeline_error!r} [FAIL]"
            )
            await bot.send_message(
                chat_id=chat_id,
                text=(
                    "⚠️ Не удалось сгенерировать игру.\n"
                    "Попробуй снова через /new или пришли другое фото."
                )
            )
            return
    # END_BLOCK_POLL_LOOP

    # START_BLOCK_POLL_TIMEOUT: Уведомление о timeout
    logger.warning(
        f"[Flow][IMP:8][_poll_game_url][POLL_TIMEOUT][Expired] "
        f"session_id={session_id} elapsed={elapsed}s [WARN]"
    )
    await bot.send_message(
        chat_id=chat_id,
        text=(
            "⚠️ Генерация заняла слишком много времени.\n"
            "Попробуй снова через /new или обратись в поддержку."
        )
    )
    # END_BLOCK_POLL_TIMEOUT
# END_FUNCTION__poll_game_url


# START_FUNCTION_on_launch_game
# START_CONTRACT:
# PURPOSE: Обрабатывает "✅ Запустить игру" — получает game_url из сессии и отправляет ссылку.
# INPUTS:
# - CallbackQuery с data "action:launch_game" => callback: CallbackQuery
# - FSMContext пользователя => state: FSMContext
# OUTPUTS:
# - None (сайд-эффект: отправка game_url или уведомление "ещё не готово")
# KEYWORDS: CONCEPT(8): GameLaunch
# COMPLEXITY_SCORE: 5
# END_CONTRACT
async def on_launch_game(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Обработчик кнопки "✅ Запустить игру".
    Получает текущий game_url из бэкенда и отправляет пользователю.
    Если game_url ещё не готов — уведомляет что нужно подождать.
    """
    await callback.answer()
    data = await state.get_data()
    session_id = data.get("session_id")

    logger.info(
        f"[Flow][IMP:6][on_launch_game][ENTRY][LaunchPressed] "
        f"user_id={callback.from_user.id} session_id={session_id} [INFO]"
    )

    game_url, _ = await backend_client.get_game_url(session_id)

    if game_url:
        await callback.message.answer(
            f"🎮 Вот твоя игра!\n🔗 {game_url}",
            parse_mode="HTML"
        )
        logger.info(
            f"[BeliefState][IMP:9][on_launch_game][URL_SENT][Success] "
            f"session_id={session_id} [SUCCESS]"
        )
    else:
        await callback.message.answer(
            "⏳ Игра ещё готовится. Подожди немного — я отправлю ссылку автоматически."
        )
# END_FUNCTION_on_launch_game


# START_FUNCTION_on_regenerate
# START_CONTRACT:
# PURPOSE: Обрабатывает "🔄 Перегенерировать" — в тест-версии всегда бесплатно.
# INPUTS:
# - CallbackQuery с data "action:regenerate" => callback: CallbackQuery
# - FSMContext пользователя => state: FSMContext
# OUTPUTS:
# - None (сайд-эффект: повторный trigger_generation + polling)
# SIDE_EFFECTS: POST /games/build повторно. Запускает asyncio task _poll_game_url.
# KEYWORDS: CONCEPT(8): Regeneration; PATTERN(7): RepeatAction
# COMPLEXITY_SCORE: 6
# END_CONTRACT
async def on_regenerate(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Обработчик кнопки "🔄 Перегенерировать".
    В тест-версии регенерация ВСЕГДА бесплатна (нет WAITING_REGEN_PAYMENT).
    Запускает повторный trigger_generation и новый цикл polling.
    """
    await callback.answer()
    data = await state.get_data()
    session_id = data.get("session_id")

    logger.info(
        f"[Flow][IMP:6][on_regenerate][ENTRY][RegeneratePressed] "
        f"user_id={callback.from_user.id} session_id={session_id} [INFO]"
    )

    # START_BLOCK_REGEN_FREE: Тест-версия: регенерация бесплатна
    try:
        await backend_client.trigger_generation(session_id)
        await callback.message.answer(
            "🔄 Повторная генерация запущена... ~60 сек ⏳"
        )
        logger.info(
            f"[BeliefState][IMP:9][on_regenerate][REGEN_FREE][Started] "
            f"session_id={session_id} [SUCCESS]"
        )
    except Exception as exc:
        logger.critical(
            f"[SystemError][IMP:10][on_regenerate][REGEN_FREE][Failed] "
            f"session_id={session_id} err={exc!r} [FATAL]"
        )
        await callback.message.answer("⚠️ Не удалось запустить регенерацию. Попробуй позже.")
        return
    # END_BLOCK_REGEN_FREE

    # START_BLOCK_REGEN_POLLING: Запуск нового цикла polling
    asyncio.create_task(
        _poll_game_url(
            chat_id=callback.message.chat.id,
            session_id=session_id,
            bot=callback.bot,
        )
    )
    # END_BLOCK_REGEN_POLLING
# END_FUNCTION_on_regenerate


def register_handlers(dp) -> None:
    """Регистрирует все хендлеры generation-роутера в диспетчере."""
    router.callback_query.register(
        on_create_game,
        F.data == "action:create_game",
        OrderState.CONFIRM
    )
    router.callback_query.register(
        on_launch_game,
        F.data == "action:launch_game"
    )
    router.callback_query.register(
        on_regenerate,
        F.data == "action:regenerate"
    )
    dp.include_router(router)
