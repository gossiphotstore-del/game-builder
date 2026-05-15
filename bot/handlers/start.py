# FILE: bot/handlers/start.py
# VERSION: 1.1.0
# START_MODULE_CONTRACT:
# PURPOSE: Обработчики команд /start, /new, /help и CTA-кнопки "Создать игру" — точка входа в диалог.
# SCOPE: Welcome-экран (продающий текст + закреп), инициализация FSM, создание сессии, показ сценария.
# INPUT: Message от пользователя (команды) и CallbackQuery (кнопка action:start_game).
# OUTPUT: Welcome-сообщение с закреплением + переход FSM в WAITING_SCENARIO.
# KEYWORDS: DOMAIN(9): BotCommands; CONCEPT(9): DialogInit; TECH(8): AiogramRouter
#           CONCEPT(8): WelcomeScreen; PATTERN(8): CTA
# LINKS: USES_API(9): aiogram.Router; CALLS_METHOD(9): backend_client.create_session
# END_MODULE_CONTRACT
#
# START_RATIONALE:
# Q: Почему /start показывает welcome-экран, а сессия создаётся только по кнопке?
# A: Пользователь должен осознанно начать диалог, нажав CTA. Welcome-сообщение закрепляется
#    и служит постоянной точкой входа. Сессия на бэкенде создаётся только когда пользователь
#    готов — иначе плодятся "мёртвые" сессии при случайных /start.
# Q: Почему pin_chat_message обёрнут в try/except?
# A: В групповых чатах бот может не иметь прав на закреп. В личке работает всегда.
#    Тихое игнорирование ошибки не ломает основной флоу.
# END_RATIONALE
#
# START_CHANGE_SUMMARY:
# LAST_CHANGE: [v1.1.0 - Welcome-экран с продающим текстом, закреп, CTA-кнопка on_start_game]
# PREV_CHANGE_SUMMARY: [v1.0.0 - /start с прямым созданием сессии и показом сценариев]
# END_CHANGE_SUMMARY
#
# START_MODULE_MAP:
# FUNC [9][Показывает welcome-экран и закрепляет сообщение] => cmd_start
# FUNC [9][CTA-кнопка: создаёт сессию и запускает FSM-диалог] => on_start_game
# FUNC [8][Сброс FSM и быстрый старт нового диалога без welcome] => cmd_new
# FUNC [6][Показывает справку по командам] => cmd_help
# END_MODULE_MAP
#
# START_USE_CASES:
# - cmd_start: User -> /start -> WelcomeShown + MessagePinned
# - on_start_game: User -> ClickCTA -> SessionCreated + ScenarioKeyboardShown
# - cmd_new: User -> /new -> FSMCleared + NewSessionCreated + ScenarioShown
# END_USE_CASES

import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from bot.states import OrderState
from bot.keyboards import welcome_keyboard, scenario_keyboard
from bot.services import backend_client

logger = logging.getLogger(__name__)
router = Router(name="start")

# START_BLOCK_WELCOME_TEXT: Продающий текст welcome-экрана (закрепляется в чате)
WELCOME_TEXT = (
    "🍄 Представь: твой человек открывает ссылку —\n"
    "и видит <b>СЕБЯ главным героем игры в стиле Марио!</b>\n\n"
    "Загружаешь фото. AI создаёт персонажа.\n"
    "Отправляешь ссылку. Всё.\n\n"
    "⏱ 1 минута\n"
    "🎉 С днём рождения  •  ❤️ Признание в любви  •  💫 Сюрприз\n\n"
    "А хочешь — просто поиграй сам, чтобы разгрузиться 🕹\n\n"
    "👇 <i>Создать игру прямо сейчас</i>"
)
# END_BLOCK_WELCOME_TEXT


# START_FUNCTION_cmd_start
# START_CONTRACT:
# PURPOSE: Обрабатывает /start — показывает welcome-экран и закрепляет сообщение.
#          Сессия НЕ создаётся здесь — только при нажатии CTA-кнопки.
# INPUTS:
# - Telegram сообщение с командой /start => message: Message
# - FSM контекст пользователя => state: FSMContext
# OUTPUTS:
# - None (сайд-эффект: welcome-сообщение + попытка pin_chat_message)
# SIDE_EFFECTS: FSM.clear(). Попытка pin_chat_message — тихо игнорируется при ошибке.
# KEYWORDS: PATTERN(9): CommandHandler; CONCEPT(8): WelcomeScreen; PATTERN(8): PinMessage
# COMPLEXITY_SCORE: 5
# END_CONTRACT
async def cmd_start(message: Message, state: FSMContext) -> None:
    """
    Обработчик команды /start.
    1. Сбрасывает предыдущее FSM-состояние.
    2. Отправляет продающий welcome-экран с CTA-кнопкой "🎮 Создать игру".
    3. Закрепляет welcome-сообщение в чате (disable_notification=True).
    Сессия на бэкенде создаётся ТОЛЬКО после нажатия CTA — в on_start_game.
    """
    user_id = message.from_user.id

    logger.info(
        f"[Flow][IMP:6][cmd_start][ENTRY][Command] "
        f"/start от user_id={user_id} [INFO]"
    )

    # START_BLOCK_CLEAR_STATE: Очистка предыдущего состояния FSM
    await state.clear()
    # END_BLOCK_CLEAR_STATE

    # START_BLOCK_SEND_WELCOME: Отправка продающего welcome-сообщения
    welcome_msg = await message.answer(
        WELCOME_TEXT,
        reply_markup=welcome_keyboard(),
        parse_mode="HTML"
    )
    logger.info(
        f"[Flow][IMP:7][cmd_start][SEND_WELCOME][MessageSent] "
        f"user_id={user_id} message_id={welcome_msg.message_id} [SUCCESS]"
    )
    # END_BLOCK_SEND_WELCOME

    # START_BLOCK_PIN_MESSAGE: Закрепление welcome-сообщения в чате
    try:
        await message.bot.pin_chat_message(
            chat_id=message.chat.id,
            message_id=welcome_msg.message_id,
            disable_notification=True
        )
        logger.info(
            f"[Flow][IMP:7][cmd_start][PIN_MESSAGE][Pinned] "
            f"chat_id={message.chat.id} message_id={welcome_msg.message_id} [SUCCESS]"
        )
    except Exception as exc:
        # BUG_FIX_CONTEXT: pin_chat_message требует прав в группах, в личке работает всегда.
        # Тихое игнорирование позволяет боту работать в любом контексте без ломки флоу.
        logger.warning(
            f"[Flow][IMP:5][cmd_start][PIN_MESSAGE][SkipPin] "
            f"chat_id={message.chat.id} err={exc!r} [WARN]"
        )
    # END_BLOCK_PIN_MESSAGE
# END_FUNCTION_cmd_start


# START_FUNCTION_on_start_game
# START_CONTRACT:
# PURPOSE: CTA-обработчик кнопки "🎮 Создать игру" — создаёт сессию и запускает FSM-диалог.
# INPUTS:
# - CallbackQuery с data "action:start_game" => callback: CallbackQuery
# - FSM контекст пользователя => state: FSMContext
# OUTPUTS:
# - None (сайд-эффект: POST /sessions + FSM → WAITING_SCENARIO + ответ со сценариями)
# SIDE_EFFECTS: FSM.clear() + backend_client.create_session() + FSM.set_state(WAITING_SCENARIO).
# KEYWORDS: PATTERN(9): CTAHandler; CONCEPT(9): SessionInit; CONCEPT(8): FSMTransition
# COMPLEXITY_SCORE: 6
# END_CONTRACT
async def on_start_game(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Обработчик нажатия CTA-кнопки "🎮 Создать игру" на welcome-экране.
    Создаёт новую сессию на бэкенде, сохраняет session_id в FSM,
    переводит FSM в WAITING_SCENARIO и показывает клавиатуру выбора сценария.
    Может быть вызван из любого FSM-состояния (фильтр состояния не задан).
    """
    await callback.answer()
    user_id = callback.from_user.id

    logger.info(
        f"[Flow][IMP:6][on_start_game][ENTRY][CTAPressed] "
        f"user_id={user_id} [INFO]"
    )

    # START_BLOCK_RESET_FSM: Сброс предыдущего состояния (если было)
    await state.clear()
    # END_BLOCK_RESET_FSM

    # START_BLOCK_CREATE_SESSION: Создание сессии на бэкенде
    try:
        session_id = await backend_client.create_session(user_id)
        await state.update_data(session_id=session_id)
        logger.info(
            f"[BeliefState][IMP:9][on_start_game][CREATE_SESSION][SessionSet] "
            f"user_id={user_id} session_id={session_id} [SUCCESS]"
        )
    except Exception as exc:
        logger.critical(
            f"[SystemError][IMP:10][on_start_game][CREATE_SESSION][BackendFail] "
            f"user_id={user_id} err={exc!r} [FATAL]"
        )
        await callback.message.answer(
            "⚠️ Не удалось подключиться к серверу. Попробуй позже."
        )
        return
    # END_BLOCK_CREATE_SESSION

    # START_BLOCK_SET_STATE_AND_REPLY: Переход FSM и показ клавиатуры сценариев
    await state.set_state(OrderState.WAITING_SCENARIO)
    await callback.message.answer(
        "Выбери сценарий 👇",
        reply_markup=scenario_keyboard()
    )
    logger.info(
        f"[Flow][IMP:6][on_start_game][SET_STATE_AND_REPLY][StateSet] "
        f"user_id={user_id} FSM=WAITING_SCENARIO [SUCCESS]"
    )
    # END_BLOCK_SET_STATE_AND_REPLY
# END_FUNCTION_on_start_game


# START_FUNCTION_cmd_new
# START_CONTRACT:
# PURPOSE: /new — быстрый сброс и старт нового диалога без welcome-экрана (для опытных).
# INPUTS:
# - Telegram сообщение с командой /new => message: Message
# - FSM контекст пользователя => state: FSMContext
# OUTPUTS:
# - None (сайд-эффект: FSM очищен, новая сессия, сразу показывает сценарии)
# SIDE_EFFECTS: FSM.clear() → backend_client.create_session() → FSM → WAITING_SCENARIO.
# KEYWORDS: PATTERN(9): Reset; CONCEPT(8): DialogRestart
# COMPLEXITY_SCORE: 5
# END_CONTRACT
async def cmd_new(message: Message, state: FSMContext) -> None:
    """
    Обработчик команды /new — сбрасывает диалог и начинает заново без welcome-экрана.
    Шорткат для опытных пользователей: сразу показывает клавиатуру сценариев.
    """
    user_id = message.from_user.id

    logger.info(
        f"[Flow][IMP:6][cmd_new][ENTRY][Command] "
        f"/new от user_id={user_id} [INFO]"
    )

    # START_BLOCK_RESET_FSM: Полный сброс FSM
    await state.clear()
    logger.info(
        f"[Flow][IMP:7][cmd_new][RESET_FSM][Cleared] "
        f"FSM очищен для user_id={user_id} [SUCCESS]"
    )
    # END_BLOCK_RESET_FSM

    # START_BLOCK_NEW_SESSION: Создание новой сессии
    try:
        session_id = await backend_client.create_session(user_id)
        await state.update_data(session_id=session_id)
        logger.info(
            f"[BeliefState][IMP:9][cmd_new][NEW_SESSION][SessionSet] "
            f"user_id={user_id} new_session_id={session_id} [SUCCESS]"
        )
    except Exception as exc:
        logger.critical(
            f"[SystemError][IMP:10][cmd_new][NEW_SESSION][BackendFail] "
            f"user_id={user_id} err={exc!r} [FATAL]"
        )
        await message.answer(
            "⚠️ Не удалось подключиться к серверу. Попробуй позже."
        )
        return
    # END_BLOCK_NEW_SESSION

    await state.set_state(OrderState.WAITING_SCENARIO)
    await message.answer(
        "Начнём заново! Выбери сценарий 👇",
        reply_markup=scenario_keyboard()
    )
# END_FUNCTION_cmd_new


# START_FUNCTION_cmd_help
# START_CONTRACT:
# PURPOSE: Обрабатывает /help — показывает справку по командам бота.
# INPUTS:
# - Telegram сообщение => message: Message
# OUTPUTS:
# - None (сайд-эффект: ответ бота со справкой)
# SIDE_EFFECTS: Отсутствуют (FSM не изменяется).
# KEYWORDS: CONCEPT(6): Help; PATTERN(6): InfoResponse
# COMPLEXITY_SCORE: 2
# END_CONTRACT
async def cmd_help(message: Message) -> None:
    """
    Обработчик команды /help.
    Показывает краткую справку по командам бота без изменения состояния FSM.
    """
    help_text = (
        "🎮 <b>PersonaGame — справка</b>\n\n"
        "/start — показать welcome-экран (с закрепом)\n"
        "/new — начать создание игры заново\n"
        "/help — эта справка\n\n"
        "<i>Нажми 🎮 Создать игру — и через 2 минуты получишь уникальную игру с фото!</i>"
    )
    await message.answer(help_text, parse_mode="HTML")
    logger.info(
        f"[Flow][IMP:4][cmd_help][REPLY][HelpShown] "
        f"user_id={message.from_user.id} [SUCCESS]"
    )
# END_FUNCTION_cmd_help


def register_handlers(dp) -> None:
    """Регистрирует все хендлеры start-роутера в диспетчере."""
    router.message.register(cmd_start, Command("start"))
    router.message.register(cmd_new, Command("new"))
    router.message.register(cmd_help, Command("help"))
    # CTA-кнопка welcome-экрана: без фильтра FSM-состояния — работает из любого контекста
    router.callback_query.register(on_start_game, F.data == "action:start_game")
    dp.include_router(router)
