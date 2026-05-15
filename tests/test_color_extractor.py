# FILE: tests/test_color_extractor.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT:
# PURPOSE: Тесты функции extract_accent_color: синтетические изображения с известными цветами.
# SCOPE: Unit-тесты: яркий красный, all-white (fallback), кожный тон (fallback).
# KEYWORDS: DOMAIN(9): Testing; CONCEPT(8): ColorExtraction; TECH(8): pytest; TECH(7): PIL.synthetic
# END_MODULE_CONTRACT
#
# START_CHANGE_SUMMARY:
# LAST_CHANGE: [v1.0.0 - Первичная реализация тестов color_extractor.]
# END_CHANGE_SUMMARY

import io
import logging
import pytest
from PIL import Image

# Настройка логирования для вывода IMP:7-10 в тесте
logging.basicConfig(level=logging.DEBUG, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def _make_image_bytes(top_color: tuple, bottom_color: tuple, width: int = 100, height: int = 100) -> bytes:
    """
    Создаёт синтетическое PNG изображение с двумя горизонтальными полосами.
    top_color    — верхняя половина (RGB tuple)
    bottom_color — нижняя половина (RGB tuple)
    Возвращает PNG bytes.
    """
    img = Image.new("RGB", (width, height), color=(255, 255, 255))
    pixels = img.load()
    mid = height // 2
    for y in range(height):
        color = top_color if y < mid else bottom_color
        for x in range(width):
            pixels[x, y] = color
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _make_solid_image_bytes(color: tuple, width: int = 100, height: int = 100) -> bytes:
    """Создаёт PNG изображение одного цвета."""
    img = Image.new("RGB", (width, height), color=color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# START_FUNCTION_test_bright_red_bottom_half
def test_bright_red_bottom_half():
    """
    Синтетическое изображение: верхняя половина — нейтральный серый (не одежда),
    нижняя половина — ярко-красный (255, 0, 0).
    Ожидаем hex, начинающийся с #ff (красный доминирует).
    """
    logger.info("[BeliefState][IMP:9][test_bright_red_bottom_half][Setup][Init] Создание синтетического изображения с красной нижней половиной [START]")

    # Верх: нейтральный серый (не кожный, не белый, не чёрный)
    # Низ: ярко-красный (R=255, G=0, B=0) — не исключается
    image_bytes = _make_image_bytes(
        top_color=(128, 128, 128),   # серый
        bottom_color=(255, 0, 0),    # красный
        width=100,
        height=100
    )

    from backend.ai.color_extractor import extract_accent_color
    result = extract_accent_color(image_bytes)

    logger.info(f"[BeliefState][IMP:9][test_bright_red_bottom_half][Assert][Result] extract_accent_color вернул: {result!r} [VALUE]")

    assert isinstance(result, str), f"Ожидался str, получен {type(result)}"
    assert result.startswith("#"), f"Hex должен начинаться с #, получен: {result!r}"
    assert len(result) == 7, f"Hex должен быть длиной 7, получен: {result!r}"

    # Красный цвет: R >= 200, G и B близко к 0
    r_val = int(result[1:3], 16)
    g_val = int(result[3:5], 16)
    b_val = int(result[5:7], 16)
    logger.info(f"[BeliefState][IMP:9][test_bright_red_bottom_half][Assert][ColorComponents] R={r_val}, G={g_val}, B={b_val} [VALUE]")
    assert r_val >= 200, f"Ожидался красный доминант (R>=200), получен R={r_val} ({result})"
    assert g_val < 100, f"Ожидался G<100 для красного, получен G={g_val} ({result})"
    assert b_val < 100, f"Ожидался B<100 для красного, получен B={b_val} ({result})"
# END_FUNCTION_test_bright_red_bottom_half


# START_FUNCTION_test_all_white_returns_fallback
def test_all_white_returns_fallback():
    """
    Изображение полностью белого цвета (R=255, G=255, B=255).
    Все кластеры должны быть исключены как белый → fallback "#1a6fd4".
    """
    logger.info("[BeliefState][IMP:9][test_all_white_returns_fallback][Setup][Init] Создание белого изображения [START]")

    image_bytes = _make_solid_image_bytes(color=(255, 255, 255))

    from backend.ai.color_extractor import extract_accent_color, FALLBACK_COLOR
    result = extract_accent_color(image_bytes)

    logger.info(f"[BeliefState][IMP:9][test_all_white_returns_fallback][Assert][Result] extract_accent_color вернул: {result!r}, ожидается fallback: {FALLBACK_COLOR!r} [VALUE]")

    assert result == FALLBACK_COLOR, f"Ожидался fallback {FALLBACK_COLOR!r}, получен {result!r}"
# END_FUNCTION_test_all_white_returns_fallback


# START_FUNCTION_test_skin_tone_returns_fallback
def test_skin_tone_returns_fallback():
    """
    Изображение полностью заполнено кожным тоном (R=200, G=160, B=130).
    Попадает в диапазон skin: R∈[170-255], G∈[120-200], B∈[90-170].
    Все кластеры исключены → fallback "#1a6fd4".
    """
    logger.info("[BeliefState][IMP:9][test_skin_tone_returns_fallback][Setup][Init] Создание изображения с кожным тоном [START]")

    # Кожный тон: R=200, G=160, B=130 — в исключённом диапазоне
    image_bytes = _make_solid_image_bytes(color=(200, 160, 130))

    from backend.ai.color_extractor import extract_accent_color, FALLBACK_COLOR
    result = extract_accent_color(image_bytes)

    logger.info(f"[BeliefState][IMP:9][test_skin_tone_returns_fallback][Assert][Result] extract_accent_color вернул: {result!r}, ожидается fallback: {FALLBACK_COLOR!r} [VALUE]")

    assert result == FALLBACK_COLOR, f"Ожидался fallback {FALLBACK_COLOR!r} для кожного тона, получен {result!r}"
# END_FUNCTION_test_skin_tone_returns_fallback


# START_FUNCTION_test_black_image_returns_fallback
def test_black_image_returns_fallback():
    """
    Изображение полностью чёрного цвета (R=0, G=0, B=0).
    Все кластеры исключены как чёрный → fallback "#1a6fd4".
    """
    logger.info("[BeliefState][IMP:9][test_black_image_returns_fallback][Setup][Init] Создание чёрного изображения [START]")

    image_bytes = _make_solid_image_bytes(color=(0, 0, 0))

    from backend.ai.color_extractor import extract_accent_color, FALLBACK_COLOR
    result = extract_accent_color(image_bytes)

    logger.info(f"[BeliefState][IMP:9][test_black_image_returns_fallback][Assert][Result] extract_accent_color вернул: {result!r}, ожидается fallback: {FALLBACK_COLOR!r} [VALUE]")

    assert result == FALLBACK_COLOR, f"Ожидался fallback {FALLBACK_COLOR!r} для чёрного, получен {result!r}"
# END_FUNCTION_test_black_image_returns_fallback


# START_FUNCTION_test_return_format_is_hex
def test_return_format_is_hex():
    """
    Проверка формата возвращаемого значения: всегда #rrggbb, нижний регистр.
    Используем ярко-синее изображение (не исключается).
    """
    logger.info("[BeliefState][IMP:9][test_return_format_is_hex][Setup][Init] Создание синего изображения для проверки формата [START]")

    # Ярко-синий (0, 0, 200) — не кожный, не белый, не чёрный
    image_bytes = _make_image_bytes(
        top_color=(128, 128, 128),
        bottom_color=(0, 0, 200),
    )

    from backend.ai.color_extractor import extract_accent_color
    result = extract_accent_color(image_bytes)

    logger.info(f"[BeliefState][IMP:9][test_return_format_is_hex][Assert][Result] Результат: {result!r} [VALUE]")

    assert isinstance(result, str)
    assert result.startswith("#")
    assert len(result) == 7
    # Нижний регистр
    assert result == result.lower(), f"Ожидался нижний регистр, получен {result!r}"
# END_FUNCTION_test_return_format_is_hex
