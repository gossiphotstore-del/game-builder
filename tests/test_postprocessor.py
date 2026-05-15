# FILE: tests/test_postprocessor.py
# VERSION: 1.1.0
# START_MODULE_CONTRACT:
# PURPOSE: Тесты функции process_sprite: удаление фона и проверка размера результата.
# SCOPE: Unit-тесты: белый PNG → RGBA output, height==512 после resize.
#        rembg.remove мокируется через unittest.mock.patch (зависимость от llvmlite/numba
#        недоступна в данной среде — rembg устанавливается без транзитивных зависимостей).
# KEYWORDS: DOMAIN(9): Testing; CONCEPT(8): PostProcessing; TECH(8): pytest; TECH(7): rembg; PATTERN(8): MockRembg
# END_MODULE_CONTRACT
#
# START_RATIONALE:
# Q: Почему rembg мокируется, а не вызывается реально?
# A: rembg требует pymatting → numba → llvmlite, которые не могут быть скомпилированы в
#    текущей среде macOS (сбой llvmlite build). Mock корректно изолирует тестируемую логику:
#    Pillow resize, RGBA conversion, PNG encoding — всё это тестируется по-настоящему.
#    Мок возвращает валидный RGBA PNG — семантически верно: rembg OUTPUT есть RGBA PNG.
# BUG_FIX_CONTEXT: rembg модуль импортируется lazily внутри функции, поэтому патчим
#    sys.modules["rembg"] ДО вызова process_sprite, чтобы перехватить lazy import.
# END_RATIONALE
#
# START_CHANGE_SUMMARY:
# LAST_CHANGE: [v1.1.0 - Добавлен mock rembg через sys.modules patch из-за недоступности numba/llvmlite.]
# PREV_CHANGE_SUMMARY: [v1.0.0 - Первичная реализация тестов postprocessor.]
# END_CHANGE_SUMMARY

import io
import sys
import logging
import types
import pytest
from unittest.mock import patch, MagicMock
from PIL import Image

logging.basicConfig(level=logging.DEBUG, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def _make_rgba_png_bytes(width: int = 200, height: int = 300, color=(100, 150, 200, 255)) -> bytes:
    """Создаёт RGBA PNG, который имитирует output rembg.remove (PNG с alpha-каналом)."""
    img = Image.new("RGBA", (width, height), color=color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _make_rgb_png_bytes(width: int = 200, height: int = 300, color=(255, 255, 255)) -> bytes:
    """Создаёт RGB PNG — входное изображение для process_sprite."""
    img = Image.new("RGB", (width, height), color=color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _create_rembg_mock(output_width: int, output_height: int):
    """
    Создаёт mock-модуль rembg, чей remove() возвращает RGBA PNG заданного размера.
    Это имитирует реальное поведение rembg: принимает bytes → возвращает RGBA PNG bytes.
    """
    fake_rgba_bytes = _make_rgba_png_bytes(width=output_width, height=output_height)

    mock_rembg = types.ModuleType("rembg")
    mock_rembg.remove = MagicMock(return_value=fake_rgba_bytes)
    return mock_rembg, fake_rgba_bytes


# START_FUNCTION_test_process_sprite_returns_png_with_alpha
def test_process_sprite_returns_png_with_alpha():
    """
    Передаём PNG с белым фоном.
    rembg.remove мокируется и возвращает RGBA PNG 200x300.
    Ожидаем: результат — PNG bytes с RGBA mode (наличие alpha-канала).
    """
    logger.info("[BeliefState][IMP:9][test_process_sprite_returns_png_with_alpha][Setup][Init] Тест: PNG с белым фоном → RGBA output [START]")

    input_bytes = _make_rgb_png_bytes(width=200, height=300)
    logger.info(f"[BeliefState][IMP:8][test_process_sprite_returns_png_with_alpha][Input][Size] Входной PNG: {len(input_bytes)} байт, 200x300 [INFO]")

    mock_rembg, _ = _create_rembg_mock(output_width=200, output_height=300)

    with patch.dict(sys.modules, {"rembg": mock_rembg}):
        # Сбрасываем закешированный модуль postprocessor чтобы lazy import применил mock
        if "backend.ai.postprocessor" in sys.modules:
            del sys.modules["backend.ai.postprocessor"]

        from backend.ai.postprocessor import process_sprite
        result_bytes = process_sprite(input_bytes)

    logger.info(f"[BeliefState][IMP:9][test_process_sprite_returns_png_with_alpha][Assert][Output] Выходной PNG: {len(result_bytes)} байт [VALUE]")

    assert isinstance(result_bytes, bytes), f"Ожидался bytes, получен {type(result_bytes)}"
    assert len(result_bytes) > 0, "PNG bytes не должны быть пустыми"

    result_img = Image.open(io.BytesIO(result_bytes))
    logger.info(f"[BeliefState][IMP:9][test_process_sprite_returns_png_with_alpha][Assert][Mode] mode={result_img.mode}, size={result_img.size} [VALUE]")

    assert result_img.mode == "RGBA", f"Ожидался режим RGBA, получен {result_img.mode!r}"
# END_FUNCTION_test_process_sprite_returns_png_with_alpha


# START_FUNCTION_test_process_sprite_height_is_512
def test_process_sprite_height_is_512():
    """
    Передаём PNG произвольного размера (150x400).
    rembg.remove мокируется, возвращает RGBA PNG 150x400.
    Ожидаем: высота результата == 512px (целевая высота спрайта).
    """
    logger.info("[BeliefState][IMP:9][test_process_sprite_height_is_512][Setup][Init] Тест: высота результата == 512px [START]")

    input_bytes = _make_rgb_png_bytes(width=150, height=400, color=(50, 100, 200))
    logger.info(f"[BeliefState][IMP:8][test_process_sprite_height_is_512][Input][Size] Входной PNG: {len(input_bytes)} байт, 150x400 [INFO]")

    mock_rembg, _ = _create_rembg_mock(output_width=150, output_height=400)

    with patch.dict(sys.modules, {"rembg": mock_rembg}):
        if "backend.ai.postprocessor" in sys.modules:
            del sys.modules["backend.ai.postprocessor"]

        from backend.ai.postprocessor import process_sprite, TARGET_HEIGHT
        result_bytes = process_sprite(input_bytes)

    result_img = Image.open(io.BytesIO(result_bytes))
    result_w, result_h = result_img.size
    logger.info(f"[BeliefState][IMP:9][test_process_sprite_height_is_512][Assert][Dimensions] Размер результата: {result_w}x{result_h}, ожидается высота {TARGET_HEIGHT} [VALUE]")

    assert result_h == TARGET_HEIGHT, (
        f"Ожидалась высота {TARGET_HEIGHT}px, получена {result_h}px"
    )
    assert result_w > 0, "Ширина должна быть > 0"
# END_FUNCTION_test_process_sprite_height_is_512


# START_FUNCTION_test_process_sprite_preserves_aspect_ratio
def test_process_sprite_preserves_aspect_ratio():
    """
    Передаём PNG 200x400 (AR = 0.5).
    rembg.remove мокируется, возвращает RGBA PNG 200x400.
    Ожидаем: в результате h=512, w≈256 (AR сохранён пропорционально).
    """
    logger.info("[BeliefState][IMP:9][test_process_sprite_preserves_aspect_ratio][Setup][Init] Тест: сохранение aspect ratio [START]")

    orig_w, orig_h = 200, 400
    input_bytes = _make_rgb_png_bytes(width=orig_w, height=orig_h, color=(200, 50, 50))

    mock_rembg, _ = _create_rembg_mock(output_width=orig_w, output_height=orig_h)

    with patch.dict(sys.modules, {"rembg": mock_rembg}):
        if "backend.ai.postprocessor" in sys.modules:
            del sys.modules["backend.ai.postprocessor"]

        from backend.ai.postprocessor import process_sprite, TARGET_HEIGHT
        result_bytes = process_sprite(input_bytes)

    result_img = Image.open(io.BytesIO(result_bytes))
    result_w, result_h = result_img.size

    expected_w = int(orig_w * TARGET_HEIGHT / orig_h)  # 200 * 512 / 400 = 256
    logger.info(f"[BeliefState][IMP:9][test_process_sprite_preserves_aspect_ratio][Assert][AspectRatio] result={result_w}x{result_h}, expected_w={expected_w} [VALUE]")

    assert result_h == TARGET_HEIGHT, f"h должна быть {TARGET_HEIGHT}, получена {result_h}"
    # Допускаем отклонение ±2px из-за округления
    assert abs(result_w - expected_w) <= 2, (
        f"Ширина должна быть ≈{expected_w}, получена {result_w}"
    )
# END_FUNCTION_test_process_sprite_preserves_aspect_ratio


# START_FUNCTION_test_process_sprite_output_is_valid_png
def test_process_sprite_output_is_valid_png():
    """
    Проверяем, что output корректно декодируется как PNG (не повреждён).
    rembg.remove мокируется, возвращает RGBA PNG 100x100.
    """
    logger.info("[BeliefState][IMP:9][test_process_sprite_output_is_valid_png][Setup][Init] Тест: валидность выходного PNG [START]")

    input_bytes = _make_rgb_png_bytes(width=100, height=100, color=(0, 128, 64))

    mock_rembg, _ = _create_rembg_mock(output_width=100, output_height=100)

    with patch.dict(sys.modules, {"rembg": mock_rembg}):
        if "backend.ai.postprocessor" in sys.modules:
            del sys.modules["backend.ai.postprocessor"]

        from backend.ai.postprocessor import process_sprite
        result_bytes = process_sprite(input_bytes)

    logger.info(f"[BeliefState][IMP:8][test_process_sprite_output_is_valid_png][Assert][Size] output size={len(result_bytes)} байт [VALUE]")

    assert isinstance(result_bytes, bytes)
    assert len(result_bytes) > 0

    # Проверяем что PNG декодируется корректно (не verify() — он требует повторного open)
    result_img = Image.open(io.BytesIO(result_bytes))
    result_img.load()  # Полная загрузка для проверки целостности
    logger.info(f"[BeliefState][IMP:9][test_process_sprite_output_is_valid_png][Assert][Valid] PNG валиден, format={result_img.format}, size={result_img.size} [SUCCESS]")

    assert result_img.format == "PNG", f"Ожидался формат PNG, получен {result_img.format!r}"
# END_FUNCTION_test_process_sprite_output_is_valid_png


# START_FUNCTION_test_rembg_is_called_with_input_bytes
def test_rembg_is_called_with_input_bytes():
    """
    Проверяем, что process_sprite передаёт входные bytes в rembg.remove (контракт вызова).
    """
    logger.info("[BeliefState][IMP:9][test_rembg_is_called_with_input_bytes][Setup][Init] Тест: rembg.remove вызывается с входными bytes [START]")

    input_bytes = _make_rgb_png_bytes(width=80, height=120, color=(128, 64, 32))

    mock_rembg, _ = _create_rembg_mock(output_width=80, output_height=120)

    with patch.dict(sys.modules, {"rembg": mock_rembg}):
        if "backend.ai.postprocessor" in sys.modules:
            del sys.modules["backend.ai.postprocessor"]

        from backend.ai.postprocessor import process_sprite
        process_sprite(input_bytes)

    # Проверяем что rembg.remove был вызван ровно один раз с входными bytes
    mock_rembg.remove.assert_called_once_with(input_bytes)
    logger.info(f"[BeliefState][IMP:9][test_rembg_is_called_with_input_bytes][Assert][CallVerify] rembg.remove вызван корректно [SUCCESS]")
# END_FUNCTION_test_rembg_is_called_with_input_bytes
