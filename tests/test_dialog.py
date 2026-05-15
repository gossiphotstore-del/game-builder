# FILE: tests/test_dialog.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT:
# PURPOSE: Тесты FSM-диалога: happy path (char_count=1 и char_count=2), валидация имени, сброс /new.
# SCOPE: Проверка корректных переходов FSM, вызовов backend_client, валидации входных данных.
#        Мокирование: aiogram Bot, FSMContext, backend_client.
# INPUT: Имитация сообщений и callback-нажатий от пользователя Telegram.
# OUTPUT: Прохождение всех тест-сценариев с выводом логов IMP:7-10.
# KEYWORDS: DOMAIN(9): Testing; CONCEPT(9): FSMTesting; TECH(8): PytestAsync
#           PATTERN(9): MockPatching; CONCEPT(8): HappyPath
# LINKS: TESTS_MODULE(9): bot/handlers/dialog.py; TESTS_MODULE(8): bot/handlers/start.py
# END_MODULE_CONTRACT
#
# START_RATIONALE:
# Q: Почему мокируем backend_client целиком а не отдельные функции?
# A: backend_client.create_session требует работающего aiohttp-соединения.
#    Мок всего модуля — изоляция теста от сетевого слоя, тест FSM без сайд-эффектов HTTP.
# Q: Почему FakeBot вместо MagicMock для Bot?
# A: aiogram's Bot.download_file возвращает BytesIO — нужна специфическая заглушка.
#    AsyncMock с нужными return_value — чище и прозрачнее для reader'а тестов.
# END_RATIONALE
#
# START_CHANGE_SUMMARY:
# LAST_CHANGE: [v1.0.0 - FS-1: happy path x2, validate_name x4, /new, companion_gender]
# END_CHANGE_SUMMARY

import io
import pytest
import pytest_asyncio
import logging

from unittest.mock import AsyncMock, MagicMock, patch
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.base import StorageKey

from bot.states import OrderState
from bot.handlers import dialog, start

logger = logging.getLogger(__name__)

# =============================================================================
# FIXTURES
# =============================================================================

def make_storage_key(user_id: int = 100, chat_id: int = 100) -> StorageKey:
    """Создаёт StorageKey для FSMContext с реальным MemoryStorage."""
    return StorageKey(bot_id=1, chat_id=chat_id, user_id=user_id)


@pytest_asyncio.fixture
async def storage():
    """MemoryStorage — реальный (не мок) для корректного тестирования FSM переходов."""
    return MemoryStorage()


@pytest_asyncio.fixture
async def fsm_context(storage):
    """Реальный FSMContext на MemoryStorage — позволяет проверить реальные переходы состояний."""
    key = make_storage_key()
    return FSMContext(storage=storage, key=key)


def make_message(text: str = "", user_id: int = 100, photo=None, bot=None) -> MagicMock:
    """
    Фабрика мок-сообщений aiogram.
    text — текст сообщения (для ввода имени и т.д.)
    photo — список PhotoSize объектов (для тестов загрузки фото)
    bot — мок Bot instance (для download_file)
    """
    msg = AsyncMock()
    msg.text = text
    msg.photo = photo
    msg.from_user = MagicMock()
    msg.from_user.id = user_id
    msg.bot = bot or AsyncMock()
    msg.answer = AsyncMock()
    return msg


def make_callback(data: str, user_id: int = 100, bot=None) -> MagicMock:
    """
    Фабрика мок-callback-запросов aiogram.
    data — callback_data строка (например "scenario:birthday")
    """
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


def make_photo_size(file_id: str = "test_file_id_hero") -> MagicMock:
    """Мок PhotoSize объекта aiogram."""
    photo = MagicMock()
    photo.file_id = file_id
    photo.file_unique_id = f"unique_{file_id}"
    photo.width = 512
    photo.height = 512
    return photo


def make_fake_bot_with_valid_photo(width: int = 512, height: int = 512) -> AsyncMock:
    """
    Фабрика мок-Bot с реалистичным download_file.
    Генерирует минимальный валидный PNG нужного размера в памяти через PIL.
    """
    from PIL import Image

    # Создаём реальный PNG в памяти нужного размера
    img = Image.new("RGB", (width, height), color=(100, 150, 200))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    fake_bot = AsyncMock()
    file_mock = MagicMock()
    file_mock.file_path = "photos/test.jpg"
    fake_bot.get_file = AsyncMock(return_value=file_mock)

    # BytesIO нужно оборачивать чтобы read() вернул данные
    fake_bot.download_file = AsyncMock(return_value=io.BytesIO(buf.getvalue()))

    return fake_bot


# =============================================================================
# ТЕСТЫ HAPPY PATH char_count=1 (6 шагов, без companion_gender и companion_photo)
# =============================================================================

@pytest.mark.asyncio
async def test_happy_path_single_character(fsm_context, caplog):
    """
    Тест полного диалога с ОДНИМ персонажем (char_count=1).
    Шаги: scenario → char_count → hero_gender → name → hero_photo → confirm.
    Шаги companion_gender и companion_photo должны быть ПРОПУЩЕНЫ.
    Логи IMP:7-10 должны появиться в выводе.
    """
    caplog.set_level(logging.INFO)

    with patch("bot.handlers.dialog.backend_client") as mock_backend, \
         patch("bot.handlers.start.backend_client") as mock_start_backend:

        mock_backend.patch_session = AsyncMock()
        mock_start_backend.create_session = AsyncMock(return_value="session-001")

        # Шаг 0: нажатие CTA-кнопки "Создать игру" — создаёт сессию и устанавливает WAITING_SCENARIO
        cb_start = make_callback("action:start_game")
        await start.on_start_game(cb_start, fsm_context)

        state_after_start = await fsm_context.get_state()
        logger.info(
            f"[BeliefState][IMP:9][test_happy_path_single][START][Check] "
            f"state={state_after_start} [VALUE]"
        )
        assert state_after_start == OrderState.WAITING_SCENARIO.state

        # Шаг 1: Выбор сценария
        cb_scenario = make_callback("scenario:birthday")
        await dialog.on_scenario(cb_scenario, fsm_context)

        state = await fsm_context.get_state()
        logger.info(
            f"[BeliefState][IMP:9][test_happy_path_single][SCENARIO][Check] "
            f"state={state} [VALUE]"
        )
        assert state == OrderState.WAITING_CHAR_COUNT.state

        # Шаг 2: Выбор кол-ва персонажей = 1
        cb_char = make_callback("char_count:1")
        await dialog.on_char_count(cb_char, fsm_context)

        state = await fsm_context.get_state()
        logger.info(
            f"[BeliefState][IMP:9][test_happy_path_single][CHAR_COUNT][Check] "
            f"state={state} char_count=1 [VALUE]"
        )
        assert state == OrderState.WAITING_HERO_GENDER.state

        # Шаг 3: Выбор пола героя → должен перейти к NAME (не COMPANION_GENDER)
        cb_gender = make_callback("hero_gender:m")
        await dialog.on_hero_gender(cb_gender, fsm_context)

        state = await fsm_context.get_state()
        logger.info(
            f"[BeliefState][IMP:9][test_happy_path_single][HERO_GENDER][Check] "
            f"state={state} — ожидаем WAITING_NAME (пропуск COMPANION_GENDER) [VALUE]"
        )
        assert state == OrderState.WAITING_NAME.state, \
            f"char_count=1 должен пропустить WAITING_COMPANION_GENDER, получено: {state}"

        # Шаг 4: Ввод имени
        msg_name = make_message(text="Александр")
        await dialog.on_name(msg_name, fsm_context)

        state = await fsm_context.get_state()
        logger.info(
            f"[BeliefState][IMP:9][test_happy_path_single][NAME][Check] "
            f"state={state} name='Александр' [VALUE]"
        )
        assert state == OrderState.WAITING_HERO_PHOTO.state

        # Шаг 5: Загрузка фото героя → должен перейти к CONFIRM (не COMPANION_PHOTO)
        fake_bot = make_fake_bot_with_valid_photo(512, 512)
        photo_size = make_photo_size("hero_file_id_001")
        msg_photo = make_message(photo=[photo_size], bot=fake_bot)

        with patch("bot.handlers.dialog._show_confirm_summary", AsyncMock()) as mock_summary:
            await dialog.on_hero_photo(msg_photo, fsm_context)

        state = await fsm_context.get_state()
        logger.info(
            f"[BeliefState][IMP:9][test_happy_path_single][HERO_PHOTO][Check] "
            f"state={state} — ожидаем CONFIRM (пропуск COMPANION_PHOTO) [VALUE]"
        )
        assert state == OrderState.CONFIRM.state, \
            f"char_count=1 должен пропустить WAITING_COMPANION_PHOTO, получено: {state}"

        # Проверка FSM data
        fsm_data = await fsm_context.get_data()
        logger.info(
            f"[BeliefState][IMP:9][test_happy_path_single][FSM_DATA][Final] "
            f"scenario={fsm_data.get('scenario')} char_count={fsm_data.get('char_count')} "
            f"hero_gender={fsm_data.get('hero_gender')} name={fsm_data.get('name')!r} [VALUE]"
        )
        assert fsm_data["scenario"] == "birthday"
        assert fsm_data["char_count"] == 1
        assert fsm_data["hero_gender"] == "m"
        assert fsm_data["name"] == "Александр"
        assert "companion_gender" not in fsm_data  # пропущен шаг

        print("\n[IMP:9] HAPPY PATH char_count=1 PASSED: все 6 шагов без companion_gender/photo")


# =============================================================================
# ТЕСТ HAPPY PATH char_count=2 (все 8 шагов)
# =============================================================================

@pytest.mark.asyncio
async def test_happy_path_two_characters(fsm_context, caplog):
    """
    Тест полного диалога с ДВУМЯ персонажами (char_count=2).
    Все 8 шагов: scenario → char_count → hero_gender → companion_gender →
    name → hero_photo → companion_photo → confirm.
    """
    caplog.set_level(logging.INFO)

    with patch("bot.handlers.dialog.backend_client") as mock_backend, \
         patch("bot.handlers.start.backend_client") as mock_start_backend:

        mock_backend.patch_session = AsyncMock()
        mock_start_backend.create_session = AsyncMock(return_value="session-002")

        # Шаг 0: нажатие CTA-кнопки "Создать игру" — создаёт сессию и устанавливает WAITING_SCENARIO
        cb_start = make_callback("action:start_game")
        await start.on_start_game(cb_start, fsm_context)

        # Шаг 1: Сценарий
        cb_scenario = make_callback("scenario:love")
        await dialog.on_scenario(cb_scenario, fsm_context)

        # Шаг 2: char_count=2
        cb_char = make_callback("char_count:2")
        await dialog.on_char_count(cb_char, fsm_context)

        # Шаг 3: Пол героя → должен перейти к COMPANION_GENDER (не NAME)
        cb_hero_gender = make_callback("hero_gender:f")
        await dialog.on_hero_gender(cb_hero_gender, fsm_context)

        state = await fsm_context.get_state()
        logger.info(
            f"[BeliefState][IMP:9][test_happy_path_two][HERO_GENDER][Check] "
            f"state={state} — ожидаем WAITING_COMPANION_GENDER [VALUE]"
        )
        assert state == OrderState.WAITING_COMPANION_GENDER.state, \
            f"char_count=2 должен идти к COMPANION_GENDER, получено: {state}"

        # Шаг 4: Пол компаньона (условный шаг)
        cb_companion_gender = make_callback("companion_gender:m")
        await dialog.on_companion_gender(cb_companion_gender, fsm_context)

        state = await fsm_context.get_state()
        logger.info(
            f"[BeliefState][IMP:9][test_happy_path_two][COMPANION_GENDER][Check] "
            f"state={state} — ожидаем WAITING_NAME [VALUE]"
        )
        assert state == OrderState.WAITING_NAME.state

        # Шаг 5: Имя
        msg_name = make_message(text="Мария")
        await dialog.on_name(msg_name, fsm_context)

        state = await fsm_context.get_state()
        assert state == OrderState.WAITING_HERO_PHOTO.state

        # Шаг 6: Фото героя → должен перейти к COMPANION_PHOTO (не CONFIRM)
        fake_bot = make_fake_bot_with_valid_photo(400, 400)
        photo_hero = make_photo_size("hero_file_002")
        msg_hero_photo = make_message(photo=[photo_hero], bot=fake_bot)

        await dialog.on_hero_photo(msg_hero_photo, fsm_context)

        state = await fsm_context.get_state()
        logger.info(
            f"[BeliefState][IMP:9][test_happy_path_two][HERO_PHOTO][Check] "
            f"state={state} — ожидаем WAITING_COMPANION_PHOTO [VALUE]"
        )
        assert state == OrderState.WAITING_COMPANION_PHOTO.state, \
            f"char_count=2 должен идти к COMPANION_PHOTO, получено: {state}"

        # Шаг 7: Фото компаньона (условный шаг)
        fake_bot_2 = make_fake_bot_with_valid_photo(350, 350)
        photo_companion = make_photo_size("companion_file_002")
        msg_companion_photo = make_message(photo=[photo_companion], bot=fake_bot_2)

        with patch("bot.handlers.dialog._show_confirm_summary", AsyncMock()):
            await dialog.on_companion_photo(msg_companion_photo, fsm_context)

        state = await fsm_context.get_state()
        logger.info(
            f"[BeliefState][IMP:9][test_happy_path_two][COMPANION_PHOTO][Check] "
            f"state={state} — ожидаем CONFIRM [VALUE]"
        )
        assert state == OrderState.CONFIRM.state

        # Проверка FSM data — все 8 полей заполнены
        fsm_data = await fsm_context.get_data()
        logger.info(
            f"[BeliefState][IMP:9][test_happy_path_two][FSM_DATA][Final] "
            f"scenario={fsm_data.get('scenario')} char_count={fsm_data.get('char_count')} "
            f"hero_gender={fsm_data.get('hero_gender')} "
            f"companion_gender={fsm_data.get('companion_gender')} "
            f"name={fsm_data.get('name')!r} [VALUE]"
        )
        assert fsm_data["scenario"] == "love"
        assert fsm_data["char_count"] == 2
        assert fsm_data["hero_gender"] == "f"
        assert fsm_data["companion_gender"] == "m"
        assert fsm_data["name"] == "Мария"
        assert "hero_photo_file_id" in fsm_data
        assert "companion_photo_file_id" in fsm_data

        print("\n[IMP:9] HAPPY PATH char_count=2 PASSED: все 8 шагов пройдены")


# =============================================================================
# ТЕСТЫ ВАЛИДАЦИИ ИМЕНИ
# =============================================================================

@pytest.mark.asyncio
async def test_name_validation_empty_string(fsm_context, caplog):
    """Пустая строка → имя должно быть отклонено, FSM остаётся в WAITING_NAME."""
    caplog.set_level(logging.INFO)

    await fsm_context.set_state(OrderState.WAITING_NAME)
    await fsm_context.update_data(session_id="session-test")

    with patch("bot.handlers.dialog.backend_client"):
        msg = make_message(text="")
        await dialog.on_name(msg, fsm_context)

    state = await fsm_context.get_state()
    logger.info(
        f"[BeliefState][IMP:9][test_name_empty][Check] "
        f"state={state} — должен остаться WAITING_NAME [VALUE]"
    )
    assert state == OrderState.WAITING_NAME.state
    msg.answer.assert_called_once()
    call_text = msg.answer.call_args[0][0]
    assert "пустым" in call_text.lower() or "не может" in call_text.lower()

    print(f"\n[IMP:9] NAME VALIDATION empty PASSED: rejected, state={state}")


@pytest.mark.asyncio
async def test_name_validation_too_long(fsm_context, caplog):
    """Строка > 30 символов → должна быть отклонена."""
    caplog.set_level(logging.INFO)

    await fsm_context.set_state(OrderState.WAITING_NAME)
    await fsm_context.update_data(session_id="session-test")

    long_name = "А" * 35  # 35 кириллических букв

    with patch("bot.handlers.dialog.backend_client"):
        msg = make_message(text=long_name)
        await dialog.on_name(msg, fsm_context)

    state = await fsm_context.get_state()
    logger.info(
        f"[BeliefState][IMP:9][test_name_long][Check] "
        f"state={state} len={len(long_name)} — должен остаться WAITING_NAME [VALUE]"
    )
    assert state == OrderState.WAITING_NAME.state
    msg.answer.assert_called_once()

    print(f"\n[IMP:9] NAME VALIDATION too_long PASSED: rejected len={len(long_name)}")


@pytest.mark.asyncio
async def test_name_validation_only_digits(fsm_context, caplog):
    """Строка из только цифр → должна быть отклонена (нет букв)."""
    caplog.set_level(logging.INFO)

    await fsm_context.set_state(OrderState.WAITING_NAME)
    await fsm_context.update_data(session_id="session-test")

    with patch("bot.handlers.dialog.backend_client"):
        msg = make_message(text="12345")
        await dialog.on_name(msg, fsm_context)

    state = await fsm_context.get_state()
    logger.info(
        f"[BeliefState][IMP:9][test_name_digits][Check] "
        f"state={state} name='12345' — должен остаться WAITING_NAME [VALUE]"
    )
    assert state == OrderState.WAITING_NAME.state
    msg.answer.assert_called_once()

    print(f"\n[IMP:9] NAME VALIDATION only_digits PASSED: rejected '12345'")


@pytest.mark.asyncio
async def test_name_validation_valid_mixed(fsm_context, caplog):
    """Валидное смешанное имя (латиница + пробел) → должно быть принято."""
    caplog.set_level(logging.INFO)

    await fsm_context.set_state(OrderState.WAITING_NAME)
    await fsm_context.update_data(session_id="session-test")

    with patch("bot.handlers.dialog.backend_client") as mock_backend:
        mock_backend.patch_session = AsyncMock()
        msg = make_message(text="Mary Jane")
        await dialog.on_name(msg, fsm_context)

    state = await fsm_context.get_state()
    logger.info(
        f"[BeliefState][IMP:9][test_name_valid][Check] "
        f"state={state} name='Mary Jane' — ожидаем WAITING_HERO_PHOTO [VALUE]"
    )
    assert state == OrderState.WAITING_HERO_PHOTO.state

    print(f"\n[IMP:9] NAME VALIDATION valid 'Mary Jane' PASSED: accepted")


# =============================================================================
# ТЕСТ /new — СБРОС FSM
# =============================================================================

@pytest.mark.asyncio
async def test_cmd_new_resets_fsm(fsm_context, caplog):
    """
    /new должен полностью сбросить FSM (включая накопленные данные)
    и создать новую сессию.
    """
    caplog.set_level(logging.INFO)

    # Предварительно задаём состояние и данные
    await fsm_context.set_state(OrderState.WAITING_NAME)
    await fsm_context.update_data(
        session_id="old-session",
        scenario="birthday",
        char_count=1,
        hero_gender="m"
    )

    old_state = await fsm_context.get_state()
    old_data = await fsm_context.get_data()
    logger.info(
        f"[BeliefState][IMP:9][test_cmd_new][BEFORE] "
        f"state={old_state} session_id={old_data.get('session_id')} [VALUE]"
    )

    with patch("bot.handlers.start.backend_client") as mock_backend:
        mock_backend.create_session = AsyncMock(return_value="new-session-999")
        msg = make_message()
        await start.cmd_new(msg, fsm_context)

    new_state = await fsm_context.get_state()
    new_data = await fsm_context.get_data()

    logger.info(
        f"[BeliefState][IMP:9][test_cmd_new][AFTER] "
        f"state={new_state} session_id={new_data.get('session_id')} [VALUE]"
    )

    # После /new: состояние = WAITING_SCENARIO, новая session_id
    assert new_state == OrderState.WAITING_SCENARIO.state, \
        f"После /new ожидаем WAITING_SCENARIO, получено: {new_state}"
    assert new_data.get("session_id") == "new-session-999", \
        f"session_id должен обновиться, получено: {new_data.get('session_id')}"

    # Старые данные должны быть очищены
    assert "scenario" not in new_data or new_data.get("scenario") is None
    assert "char_count" not in new_data or new_data.get("char_count") is None

    mock_backend.create_session.assert_called_once()

    print(
        f"\n[IMP:9] /new RESET FSM PASSED: "
        f"state={new_state} new_session_id={new_data.get('session_id')}"
    )


# =============================================================================
# ТЕСТ ФОТО — маленький размер отклоняется
# =============================================================================

@pytest.mark.asyncio
async def test_hero_photo_too_small_rejected(fsm_context, caplog):
    """Фото меньше 300×300px должно быть отклонено, FSM остаётся в WAITING_HERO_PHOTO."""
    caplog.set_level(logging.INFO)

    await fsm_context.set_state(OrderState.WAITING_HERO_PHOTO)
    await fsm_context.update_data(session_id="session-photo-test", char_count=1)

    # Создаём маленькое фото 100×100
    fake_bot = make_fake_bot_with_valid_photo(width=100, height=100)
    photo_size = make_photo_size("small_photo_id")
    msg = make_message(photo=[photo_size], bot=fake_bot)

    with patch("bot.handlers.dialog.backend_client"):
        await dialog.on_hero_photo(msg, fsm_context)

    state = await fsm_context.get_state()
    logger.info(
        f"[BeliefState][IMP:9][test_photo_small][Check] "
        f"state={state} photo=100x100 — должен остаться WAITING_HERO_PHOTO [VALUE]"
    )
    assert state == OrderState.WAITING_HERO_PHOTO.state
    msg.answer.assert_called_once()

    print(f"\n[IMP:9] PHOTO VALIDATION 100x100 PASSED: rejected, state={state}")


@pytest.mark.asyncio
async def test_hero_photo_no_photo_message_rejected(fsm_context, caplog):
    """Сообщение без фото (документ или текст) должно быть отклонено."""
    caplog.set_level(logging.INFO)

    await fsm_context.set_state(OrderState.WAITING_HERO_PHOTO)
    await fsm_context.update_data(session_id="session-no-photo", char_count=1)

    msg = make_message(text="вот моё фото", photo=None)

    with patch("bot.handlers.dialog.backend_client"):
        await dialog.on_hero_photo(msg, fsm_context)

    state = await fsm_context.get_state()
    assert state == OrderState.WAITING_HERO_PHOTO.state
    msg.answer.assert_called_once()

    print(f"\n[IMP:9] PHOTO VALIDATION no-photo PASSED: rejected document/text")
