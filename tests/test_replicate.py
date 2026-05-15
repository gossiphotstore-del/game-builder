# FILE: tests/test_replicate.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT:
# PURPOSE: Тесты функции generate_sprite: проверка промптов и поведения при timeout/ошибке.
# SCOPE: Mock-тесты Replicate API, проверка gender-specific промптов, timeout behavior.
# KEYWORDS: DOMAIN(9): Testing; CONCEPT(9): MockReplicate; TECH(8): pytest; TECH(8): unittest.mock
# END_MODULE_CONTRACT
#
# START_CHANGE_SUMMARY:
# LAST_CHANGE: [v1.0.0 - Первичная реализация тестов replicate_client.]
# END_CHANGE_SUMMARY

import io
import time
import logging
import pytest
from unittest.mock import patch, MagicMock

from PIL import Image

logging.basicConfig(level=logging.DEBUG, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def _make_fake_photo_bytes() -> bytes:
    """Создаёт минимальный валидный PNG для передачи в generate_sprite."""
    img = Image.new("RGB", (50, 50), color=(100, 150, 200))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _make_fake_png_response_bytes() -> bytes:
    """Создаёт байты PNG-ответа имитации Replicate."""
    img = Image.new("RGB", (100, 100), color=(200, 100, 50))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# START_FUNCTION_test_hero_prompt_contains_accent_color
def test_hero_prompt_contains_accent_color():
    """
    Для prompt_key="hero" промпт ДОЛЖЕН содержать переданный accent_color.
    Mock: replicate.Client.run() возвращает URL фейкового PNG.
    """
    logger.info("[BeliefState][IMP:9][test_hero_prompt_contains_accent_color][Setup][Init] Тест промпта hero с accent_color [START]")

    fake_photo_bytes = _make_fake_photo_bytes()
    fake_png_bytes = _make_fake_png_response_bytes()
    accent_color = "#ff5500"

    captured_input = {}

    def mock_run(model, input, **kwargs):
        captured_input.update(input)
        return "http://fake-url/result.png"

    with patch("replicate.Client") as MockClient:
        mock_instance = MagicMock()
        MockClient.return_value = mock_instance
        mock_instance.run.side_effect = mock_run

        # Также mock urllib.request.urlopen для скачивания PNG
        mock_response = MagicMock()
        mock_response.read.return_value = fake_png_bytes
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_response):
            from backend.ai import replicate_client as rc
            # Принудительно устанавливаем env-токен чтобы клиент создался
            with patch.dict("os.environ", {"REPLICATE_API_TOKEN": "test-token"}):
                result_bytes = rc.generate_sprite(fake_photo_bytes, "hero", accent_color)

    logger.info(f"[BeliefState][IMP:9][test_hero_prompt_contains_accent_color][Assert][Result] captured prompt: {captured_input.get('prompt', '')[:80]}... [VALUE]")

    assert isinstance(result_bytes, bytes), "Ожидались bytes"
    assert len(result_bytes) > 0

    captured_prompt = captured_input.get("prompt", "")
    assert accent_color in captured_prompt, (
        f"accent_color {accent_color!r} не найден в промпте: {captured_prompt!r}"
    )
    # hero промпт содержит UTV
    assert "Can-Am" in captured_prompt or "UTV" in captured_prompt, (
        f"hero промпт должен содержать 'Can-Am' или 'UTV': {captured_prompt!r}"
    )
# END_FUNCTION_test_hero_prompt_contains_accent_color


# START_FUNCTION_test_companion_m_prompt_contains_masculine
def test_companion_m_prompt_contains_masculine():
    """
    Для prompt_key="companion_m" промпт ДОЛЖЕН содержать "masculine silhouette".
    """
    logger.info("[BeliefState][IMP:9][test_companion_m_prompt_contains_masculine][Setup][Init] Тест промпта companion_m [START]")

    fake_photo_bytes = _make_fake_photo_bytes()
    fake_png_bytes = _make_fake_png_response_bytes()
    accent_color = "#3344cc"

    captured_input = {}

    def mock_run(model, input, **kwargs):
        captured_input.update(input)
        return "http://fake-url/result.png"

    with patch("replicate.Client") as MockClient:
        mock_instance = MagicMock()
        MockClient.return_value = mock_instance
        mock_instance.run.side_effect = mock_run

        mock_response = MagicMock()
        mock_response.read.return_value = fake_png_bytes
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_response):
            from backend.ai import replicate_client as rc
            with patch.dict("os.environ", {"REPLICATE_API_TOKEN": "test-token"}):
                result_bytes = rc.generate_sprite(fake_photo_bytes, "companion_m", accent_color)

    captured_prompt = captured_input.get("prompt", "")
    logger.info(f"[BeliefState][IMP:9][test_companion_m_prompt_contains_masculine][Assert][Prompt] {captured_prompt[:100]}... [VALUE]")

    assert "masculine silhouette" in captured_prompt, (
        f"companion_m промпт должен содержать 'masculine silhouette': {captured_prompt!r}"
    )
    assert accent_color in captured_prompt
# END_FUNCTION_test_companion_m_prompt_contains_masculine


# START_FUNCTION_test_companion_f_prompt_contains_feminine
def test_companion_f_prompt_contains_feminine():
    """
    Для prompt_key="companion_f" промпт ДОЛЖЕН содержать "feminine silhouette".
    """
    logger.info("[BeliefState][IMP:9][test_companion_f_prompt_contains_feminine][Setup][Init] Тест промпта companion_f [START]")

    fake_photo_bytes = _make_fake_photo_bytes()
    fake_png_bytes = _make_fake_png_response_bytes()
    accent_color = "#aabbcc"

    captured_input = {}

    def mock_run(model, input, **kwargs):
        captured_input.update(input)
        return "http://fake-url/result.png"

    with patch("replicate.Client") as MockClient:
        mock_instance = MagicMock()
        MockClient.return_value = mock_instance
        mock_instance.run.side_effect = mock_run

        mock_response = MagicMock()
        mock_response.read.return_value = fake_png_bytes
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_response):
            from backend.ai import replicate_client as rc
            with patch.dict("os.environ", {"REPLICATE_API_TOKEN": "test-token"}):
                result_bytes = rc.generate_sprite(fake_photo_bytes, "companion_f", accent_color)

    captured_prompt = captured_input.get("prompt", "")
    logger.info(f"[BeliefState][IMP:9][test_companion_f_prompt_contains_feminine][Assert][Prompt] {captured_prompt[:100]}... [VALUE]")

    assert "feminine silhouette" in captured_prompt, (
        f"companion_f промпт должен содержать 'feminine silhouette': {captured_prompt!r}"
    )
    assert accent_color in captured_prompt
# END_FUNCTION_test_companion_f_prompt_contains_feminine


# START_FUNCTION_test_timeout_raises_timeout_error
def test_timeout_raises_timeout_error():
    """
    Если replicate.run() занимает больше TIMEOUT_SEC → должен подняться TimeoutError.
    Патчим TIMEOUT_SEC = 0 для мгновенного срабатывания.
    """
    logger.info("[BeliefState][IMP:9][test_timeout_raises_timeout_error][Setup][Init] Тест timeout после 120 сек [START]")

    fake_photo_bytes = _make_fake_photo_bytes()

    def slow_run(model, input, **kwargs):
        # Имитируем превышение timeout: устанавливаем start_time заранее в прошлом
        time.sleep(0.01)
        return "http://fake-url/result.png"

    with patch("replicate.Client") as MockClient:
        mock_instance = MagicMock()
        MockClient.return_value = mock_instance
        mock_instance.run.side_effect = slow_run

        mock_response = MagicMock()
        mock_response.read.return_value = b"fake_png"
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_response):
            from backend.ai import replicate_client as rc
            # Патчим TIMEOUT_SEC = 0 чтобы любое время вызова было timeout
            with patch.object(rc, "TIMEOUT_SEC", 0):
                with patch.dict("os.environ", {"REPLICATE_API_TOKEN": "test-token"}):
                    with pytest.raises(TimeoutError) as exc_info:
                        rc.generate_sprite(fake_photo_bytes, "hero", "#ff0000")

    logger.info(f"[BeliefState][IMP:9][test_timeout_raises_timeout_error][Assert][Exception] TimeoutError raised: {exc_info.value!r} [SUCCESS]")
    assert "timed out" in str(exc_info.value).lower() or "timeout" in str(exc_info.value).lower()
# END_FUNCTION_test_timeout_raises_timeout_error


# START_FUNCTION_test_replicate_error_raises_runtime_error
def test_replicate_error_raises_runtime_error():
    """
    Если replicate.run() кидает исключение → generate_sprite должен поднять RuntimeError.
    """
    logger.info("[BeliefState][IMP:9][test_replicate_error_raises_runtime_error][Setup][Init] Тест ошибки Replicate API [START]")

    fake_photo_bytes = _make_fake_photo_bytes()

    def failing_run(model, input, **kwargs):
        raise Exception("Replicate internal error: model not found")

    with patch("replicate.Client") as MockClient:
        mock_instance = MagicMock()
        MockClient.return_value = mock_instance
        mock_instance.run.side_effect = failing_run

        from backend.ai import replicate_client as rc
        with patch.dict("os.environ", {"REPLICATE_API_TOKEN": "test-token"}):
            with pytest.raises(RuntimeError) as exc_info:
                rc.generate_sprite(fake_photo_bytes, "hero", "#ff0000")

    logger.info(f"[BeliefState][IMP:9][test_replicate_error_raises_runtime_error][Assert][Exception] RuntimeError raised: {exc_info.value!r} [SUCCESS]")
    assert "Replicate API error" in str(exc_info.value)
# END_FUNCTION_test_replicate_error_raises_runtime_error


# START_FUNCTION_test_invalid_prompt_key_raises_value_error
def test_invalid_prompt_key_raises_value_error():
    """
    Если передан неизвестный prompt_key → должен подняться ValueError.
    """
    logger.info("[BeliefState][IMP:9][test_invalid_prompt_key_raises_value_error][Setup][Init] Тест неизвестного prompt_key [START]")

    fake_photo_bytes = _make_fake_photo_bytes()

    from backend.ai import replicate_client as rc
    with pytest.raises(ValueError) as exc_info:
        rc.generate_sprite(fake_photo_bytes, "unknown_key", "#ff0000")

    logger.info(f"[BeliefState][IMP:9][test_invalid_prompt_key_raises_value_error][Assert][Exception] ValueError raised: {exc_info.value!r} [SUCCESS]")
    assert "unknown_key" in str(exc_info.value)
# END_FUNCTION_test_invalid_prompt_key_raises_value_error
