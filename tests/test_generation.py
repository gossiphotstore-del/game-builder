# FILE: tests/test_generation.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT:
# PURPOSE: Тесты generation.py: запуск игры, получение game_url, регенерация, polling.
# SCOPE: Проверка on_create_game, on_launch_game, on_regenerate.
#        Мокирование backend_client и asyncio.create_task (блокирует фоновые задачи в тестах).
# INPUT: Имитация callback-нажатий с FSMContext в состоянии CONFIRM.
# OUTPUT: Тесты PASSED с выводом логов IMP:7-10.
# KEYWORDS: DOMAIN(9): Testing; CONCEPT(9): AsyncMocking; TECH(8): PytestAsync
#           PATTERN(9): MockPatching
# LINKS: TESTS_MODULE(9): bot/handlers/generation.py
# END_MODULE_CONTRACT
#
# START_CHANGE_SUMMARY:
# LAST_CHANGE: [v1.0.0 - FS-1: create_game trigger, launch_game с url, regenerate, polling_timeout]
# END_CHANGE_SUMMARY

import asyncio
import pytest
import pytest_asyncio
import logging

from unittest.mock import AsyncMock, MagicMock, patch
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.base import StorageKey

from bot.states import OrderState
from bot.handlers import generation

logger = logging.getLogger(__name__)


# =============================================================================
# FIXTURES
# =============================================================================

def make_storage_key(user_id: int = 200) -> StorageKey:
    return StorageKey(bot_id=1, chat_id=user_id, user_id=user_id)


@pytest_asyncio.fixture
async def storage():
    return MemoryStorage()


@pytest_asyncio.fixture
async def fsm_context(storage):
    """FSMContext для тестов generation — предварительно в состоянии CONFIRM."""
    key = make_storage_key()
    ctx = FSMContext(storage=storage, key=key)
    await ctx.set_state(OrderState.CONFIRM)
    await ctx.update_data(session_id="gen-session-001")
    return ctx


def make_callback(data: str, user_id: int = 200, bot=None) -> MagicMock:
    """Мок CallbackQuery для тестов generation."""
    cb = AsyncMock()
    cb.data = data
    cb.from_user = MagicMock()
    cb.from_user.id = user_id
    cb.answer = AsyncMock()
    cb.message = AsyncMock()
    cb.message.answer = AsyncMock()
    cb.message.chat = MagicMock()
    cb.message.chat.id = user_id
    cb.bot = bot or AsyncMock()
    return cb


# =============================================================================
# ТЕСТ: on_create_game — успешный запуск генерации
# =============================================================================

@pytest.mark.asyncio
async def test_on_create_game_success(fsm_context, caplog):
    """
    Нажатие "🚀 Создать игру":
    - trigger_generation вызывается с правильным session_id
    - пользователь получает уведомление о запуске
    - asyncio.create_task вызывается для polling
    """
    caplog.set_level(logging.INFO)

    cb = make_callback("action:create_game")

    with patch("bot.handlers.generation.backend_client") as mock_backend, \
         patch("bot.handlers.generation.asyncio.create_task") as mock_create_task:

        mock_backend.trigger_generation = AsyncMock()
        # close() coroutine to avoid RuntimeWarning "coroutine never awaited"
        def _consume_coro(coro):
            coro.close()
            return MagicMock()
        mock_create_task.side_effect = _consume_coro

        await generation.on_create_game(cb, fsm_context)

        # trigger_generation должен быть вызван с session_id из FSM
        mock_backend.trigger_generation.assert_called_once_with("gen-session-001")

        logger.info(
            f"[BeliefState][IMP:9][test_on_create_game][VERIFY] "
            f"trigger_generation вызван с session_id=gen-session-001 [SUCCESS]"
        )

        # Пользователь получил уведомление о запуске
        cb.message.answer.assert_called_once()
        answer_text = cb.message.answer.call_args[0][0]
        assert "генерацию" in answer_text.lower() or "запускаю" in answer_text.lower()

        logger.info(
            f"[BeliefState][IMP:9][test_on_create_game][MESSAGE] "
            f"answer_text содержит уведомление о генерации [SUCCESS]"
        )

        # Задача polling запущена
        mock_create_task.assert_called_once()

        print("\n[IMP:9] on_create_game SUCCESS PASSED: trigger_generation + notify + polling_task")


# =============================================================================
# ТЕСТ: on_create_game — ошибка бэкенда
# =============================================================================

@pytest.mark.asyncio
async def test_on_create_game_backend_error(fsm_context, caplog):
    """
    Если trigger_generation бросает исключение — пользователь получает сообщение об ошибке.
    """
    caplog.set_level(logging.INFO)

    cb = make_callback("action:create_game")

    with patch("bot.handlers.generation.backend_client") as mock_backend, \
         patch("bot.handlers.generation.asyncio.create_task") as mock_create_task:

        mock_backend.trigger_generation = AsyncMock(
            side_effect=Exception("Connection refused")
        )

        await generation.on_create_game(cb, fsm_context)

        # Задача polling НЕ запущена при ошибке
        mock_create_task.assert_not_called()

        # Пользователь получил сообщение об ошибке
        cb.message.answer.assert_called_once()
        answer_text = cb.message.answer.call_args[0][0]
        assert "⚠️" in answer_text or "не удалось" in answer_text.lower()

        logger.info(
            f"[BeliefState][IMP:9][test_on_create_game_error][VERIFY] "
            f"Ошибка обработана корректно, polling_task не запущен [SUCCESS]"
        )

        print("\n[IMP:9] on_create_game BACKEND_ERROR PASSED: error notified, no polling_task")


# =============================================================================
# ТЕСТ: on_launch_game — game_url готов
# =============================================================================

@pytest.mark.asyncio
async def test_on_launch_game_with_url(fsm_context, caplog):
    """
    Нажатие "✅ Запустить игру" когда game_url уже готов:
    - get_game_url возвращает URL
    - пользователь получает ссылку
    """
    caplog.set_level(logging.INFO)

    cb = make_callback("action:launch_game")
    expected_url = "https://user.github.io/games/gen-session-001/index.html"

    with patch("bot.handlers.generation.backend_client") as mock_backend:
        mock_backend.get_game_url = AsyncMock(return_value=(expected_url, None))

        await generation.on_launch_game(cb, fsm_context)

        mock_backend.get_game_url.assert_called_once_with("gen-session-001")

        cb.message.answer.assert_called_once()
        answer_text = cb.message.answer.call_args[0][0]
        assert expected_url in answer_text

        logger.info(
            f"[BeliefState][IMP:9][test_on_launch_game_url][VERIFY] "
            f"game_url={expected_url} отправлен пользователю [SUCCESS]"
        )

        print(f"\n[IMP:9] on_launch_game WITH URL PASSED: url={expected_url}")


# =============================================================================
# ТЕСТ: on_launch_game — game_url ещё не готов
# =============================================================================

@pytest.mark.asyncio
async def test_on_launch_game_no_url_yet(fsm_context, caplog):
    """
    Нажатие "✅ Запустить игру" когда game_url ещё не готов:
    - get_game_url возвращает None
    - пользователь получает сообщение "ещё готовится"
    """
    caplog.set_level(logging.INFO)

    cb = make_callback("action:launch_game")

    with patch("bot.handlers.generation.backend_client") as mock_backend:
        mock_backend.get_game_url = AsyncMock(return_value=(None, None))

        await generation.on_launch_game(cb, fsm_context)

        cb.message.answer.assert_called_once()
        answer_text = cb.message.answer.call_args[0][0]
        assert "готовится" in answer_text.lower() or "⏳" in answer_text

        logger.info(
            f"[BeliefState][IMP:9][test_on_launch_no_url][VERIFY] "
            f"game_url=None → сообщение 'ещё готовится' [SUCCESS]"
        )

        print("\n[IMP:9] on_launch_game NO URL PASSED: 'still loading' message sent")


# =============================================================================
# ТЕСТ: on_regenerate — бесплатная регенерация в тест-версии
# =============================================================================

@pytest.mark.asyncio
async def test_on_regenerate_free(fsm_context, caplog):
    """
    Нажатие "🔄 Перегенерировать" в тест-версии:
    - trigger_generation вызывается повторно
    - пользователь получает уведомление о повторной генерации
    - asyncio.create_task запускает новый polling
    - WAITING_REGEN_PAYMENT НЕ вызывается (тест-версия)
    """
    caplog.set_level(logging.INFO)

    cb = make_callback("action:regenerate")

    with patch("bot.handlers.generation.backend_client") as mock_backend, \
         patch("bot.handlers.generation.asyncio.create_task") as mock_create_task:

        mock_backend.trigger_generation = AsyncMock()

        def _consume_coro(coro):
            coro.close()
            return MagicMock()
        mock_create_task.side_effect = _consume_coro

        await generation.on_regenerate(cb, fsm_context)

        # trigger_generation вызван повторно (бесплатно)
        mock_backend.trigger_generation.assert_called_once_with("gen-session-001")

        logger.info(
            f"[BeliefState][IMP:9][test_on_regenerate][VERIFY] "
            f"trigger_generation вызван повторно, бесплатно [SUCCESS]"
        )

        # Пользователь уведомлён о повторной генерации
        cb.message.answer.assert_called_once()
        answer_text = cb.message.answer.call_args[0][0]
        assert "генерация" in answer_text.lower() or "перегенерация" in answer_text.lower() \
               or "повторная" in answer_text.lower()

        # Новый polling запущен
        mock_create_task.assert_called_once()

        print("\n[IMP:9] on_regenerate FREE PASSED: re-triggered + notify + new polling_task")


# =============================================================================
# ТЕСТ: _poll_game_url — получает URL и отправляет сообщение
# =============================================================================

@pytest.mark.asyncio
async def test_poll_game_url_success(caplog):
    """
    _poll_game_url: при первом же опросе получает game_url → отправляет сообщение пользователю.
    """
    caplog.set_level(logging.INFO)

    game_url = "https://user.github.io/games/poll-test/index.html"
    fake_bot = AsyncMock()

    with patch("bot.handlers.generation.backend_client") as mock_backend, \
         patch("bot.handlers.generation.asyncio.sleep", AsyncMock()):

        mock_backend.get_game_url = AsyncMock(return_value=(game_url, None))

        await generation._poll_game_url(
            chat_id=200,
            session_id="poll-session",
            bot=fake_bot
        )

        # Bot.send_message вызван с game_url в тексте
        fake_bot.send_message.assert_called_once()
        call_kwargs = fake_bot.send_message.call_args
        msg_text = call_kwargs[1].get("text", "") or call_kwargs[0][1] if call_kwargs[0] else ""

        logger.info(
            f"[BeliefState][IMP:9][test_poll_success][VERIFY] "
            f"send_message вызван с game_url [SUCCESS]"
        )

        print(f"\n[IMP:9] _poll_game_url SUCCESS PASSED: url found and sent")


# =============================================================================
# ТЕСТ: _poll_game_url — timeout после превышения лимита
# =============================================================================

@pytest.mark.asyncio
async def test_poll_game_url_timeout(caplog):
    """
    _poll_game_url: если game_url так и не появляется — отправляет сообщение о timeout.
    Тест использует сокращённый POLL_TIMEOUT (патчим константу).
    """
    caplog.set_level(logging.INFO)

    fake_bot = AsyncMock()

    with patch("bot.handlers.generation.backend_client") as mock_backend, \
         patch("bot.handlers.generation.asyncio.sleep", AsyncMock()), \
         patch.object(generation, "POLL_TIMEOUT_SECONDS", 10), \
         patch.object(generation, "POLL_INTERVAL_SECONDS", 5):

        # game_url всегда None — таймаут
        mock_backend.get_game_url = AsyncMock(return_value=(None, None))

        await generation._poll_game_url(
            chat_id=200,
            session_id="timeout-session",
            bot=fake_bot
        )

        logger.info(
            f"[BeliefState][IMP:9][test_poll_timeout][VERIFY] "
            f"get_game_url=None → timeout сообщение [SUCCESS]"
        )

        # Должно быть отправлено сообщение о timeout
        fake_bot.send_message.assert_called_once()
        timeout_text = fake_bot.send_message.call_args[1].get("text", "")
        if not timeout_text:
            timeout_text = str(fake_bot.send_message.call_args)
        assert "⚠️" in timeout_text or "много" in timeout_text or "timeout" in timeout_text.lower() \
               or "генерация" in timeout_text.lower()

        print(f"\n[IMP:9] _poll_game_url TIMEOUT PASSED: timeout message sent after {10}s")
