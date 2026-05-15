# FILE: bot/main.py
# VERSION: 1.1.0
# START_MODULE_CONTRACT:
# PURPOSE: Точка входа Telegram-бота. Bot + Dispatcher + MemoryStorage + регистрация роутеров + polling.
# SCOPE: Инициализация бота, настройка FSM storage (MemoryStorage для тест-версии FS-1),
#        регистрация всех роутеров, запуск long-polling.
# INPUT: Конфигурация из settings (BOT_TOKEN).
# OUTPUT: Работающий Telegram-бот в режиме polling.
# KEYWORDS: DOMAIN(9): BotEntry; CONCEPT(9): Dispatcher; TECH(9): AiogramPolling
# LINKS: USES_API(9): aiogram.Bot; USES_API(9): aiogram.Dispatcher
# END_MODULE_CONTRACT
#
# START_RATIONALE:
# Q: Почему MemoryStorage, а не RedisStorage?
# A: FS-1 — тест-версия без бэкенда. Redis может быть недоступен.
#    MemoryStorage достаточен для разработки и тестирования FSM.
#    В production (FS-4) будет заменён на RedisStorage через aiogram_contrib.
# Q: Почему logging настраивается здесь, а не в config?
# A: Лог-конфигурация — ответственность точки входа. Разделение: config.py управляет
#    переменными окружения, main.py — инфраструктурой запуска.
# END_RATIONALE
#
# START_CHANGE_SUMMARY:
# LAST_CHANGE: [v1.1.0 - Настройка профиля бота: description, short_description, commands на старте]
# PREV_CHANGE_SUMMARY: [v1.0.0 - FS-1: polling + MemoryStorage + три роутера]
# END_CHANGE_SUMMARY
#
# START_MODULE_MAP:
# FUNC [10][Главная async coroutine — инит и запуск бота] => main
# END_MODULE_MAP

import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand

from bot.config import settings
from bot.handlers import start as start_module
from bot.handlers import dialog as dialog_module
from bot.handlers import generation as generation_module

# START_BLOCK_LOGGING_SETUP: Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ]
)
logger = logging.getLogger(__name__)
# END_BLOCK_LOGGING_SETUP


# START_FUNCTION_main
# START_CONTRACT:
# PURPOSE: Инициализирует бот, диспетчер и запускает long-polling.
# INPUTS: Нет (конфигурация из settings)
# OUTPUTS: Нет (бесконечный цикл polling до прерывания)
# SIDE_EFFECTS: Запускает asyncio event loop с polling-соединением к Telegram API.
# KEYWORDS: PATTERN(9): AsyncMain; CONCEPT(9): BotLifecycle
# COMPLEXITY_SCORE: 6
# END_CONTRACT
async def main() -> None:
    """
    Главная корутина точки входа бота.
    1. Создаёт Bot с DefaultBotProperties (HTML parse_mode по умолчанию).
    2. Создаёт Dispatcher с MemoryStorage для FSM (тест-версия).
    3. Регистрирует роутеры: start → dialog → generation.
    4. Удаляет webhook (на случай если был установлен ранее).
    5. Запускает long-polling через dp.start_polling().
    """

    logger.info(
        "[Flow][IMP:6][main][STARTUP][BotInit] Инициализация бота... [INFO]"
    )

    # START_BLOCK_INIT_BOT: Создание Bot и Dispatcher
    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher(storage=MemoryStorage())
    # END_BLOCK_INIT_BOT

    # START_BLOCK_REGISTER_ROUTERS: Подключение роутеров в правильном порядке
    start_module.register_handlers(dp)
    dialog_module.register_handlers(dp)
    generation_module.register_handlers(dp)

    logger.info(
        "[Flow][IMP:7][main][REGISTER_ROUTERS][Done] "
        "Роутеры зарегистрированы: start, dialog, generation [SUCCESS]"
    )
    # END_BLOCK_REGISTER_ROUTERS

    # START_BLOCK_SETUP_BOT_PROFILE: Настройка профиля бота (описание + команды меню)
    try:
        await bot.set_my_description(
            "🎮✨ PersonaGame\n\n"
            "Загрузи фото — и твой друг станет героем персональной игры!\n\n"
            "Выбери сценарий: День рождения, Любовь или Сюрприз. "
            "AI создаёт уникальных персонажей из твоих фото. "
            "Игра открывается прямо в браузере. Готово за 2 минуты! 🎁"
        )
        await bot.set_my_short_description(
            "🎮 Персональная игра с AI-персонажами из твоих фото — "
            "необычный подарок за 2 минуты!"
        )
        await bot.set_my_commands([
            BotCommand(command="start", description="🎮 Главный экран — создать игру"),
            BotCommand(command="new", description="🔄 Начать заново"),
            BotCommand(command="help", description="❓ Справка"),
        ])
        logger.info(
            "[Flow][IMP:7][main][SETUP_BOT_PROFILE][Done] "
            "Профиль бота обновлён: description + short_description + commands [SUCCESS]"
        )
    except Exception as exc:
        logger.warning(
            f"[Flow][IMP:5][main][SETUP_BOT_PROFILE][Skip] "
            f"Не удалось обновить профиль бота: {exc!r} [WARN]"
        )
    # END_BLOCK_SETUP_BOT_PROFILE

    # START_BLOCK_START_POLLING: Удаление webhook и запуск polling
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info(
        "[BeliefState][IMP:9][main][START_POLLING][Begin] "
        f"Бот запущен. backend_url={settings.BACKEND_URL} [SUCCESS]"
    )

    try:
        await dp.start_polling(bot)
    except KeyboardInterrupt:
        logger.info(
            "[Flow][IMP:6][main][START_POLLING][Interrupted] "
            "Polling остановлен пользователем [INFO]"
        )
    finally:
        await bot.session.close()
        logger.info(
            "[Flow][IMP:6][main][START_POLLING][Closed] Bot session закрыта [INFO]"
        )
    # END_BLOCK_START_POLLING
# END_FUNCTION_main


if __name__ == "__main__":
    asyncio.run(main())
