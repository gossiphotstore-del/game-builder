# FILE: tests/test_game_builder.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT:
# PURPOSE: Тесты game_builder.build(): проверка замены всех 6 плейсхолдеров в template.html.
# SCOPE: Подстановка PLAYER_NAME, HERO_SPRITE_URL, COMPANION_SPRITE_URL,
#        HAS_COMPANION, SCENARIO, HERO_GENDER.
# KEYWORDS: DOMAIN(9): Testing; CONCEPT(8): TemplateSubstitution; TECH(7): PytestSync
# LINKS: USES_API(10): backend.services.game_builder.build
# END_MODULE_CONTRACT
#
# START_RATIONALE:
# Q: Почему тесты синхронные (нет async)?
# A: game_builder.build() — синхронная функция чтения файла и строковых замен.
#    Нет async-операций. pytest без asyncio достаточен.
# END_RATIONALE
#
# START_CHANGE_SUMMARY:
# LAST_CHANGE: [v1.0.0 - Создание тестов game_builder (FS-4)]
# END_CHANGE_SUMMARY

import logging
import os

import pytest

logger = logging.getLogger(__name__)

# Env для config (если импортируется транзитивно)
os.environ.setdefault("REPLICATE_API_TOKEN", "test_token")
os.environ.setdefault("GITHUB_TOKEN", "test_github_token")
os.environ.setdefault("GITHUB_REPO", "testuser/testrepo")
os.environ.setdefault("GAME_BASE_URL", "https://testuser.github.io/testrepo")
os.environ.setdefault("BOT_TOKEN", "1234567890:AATestBotToken")


# === Вспомогательные фикстуры ===

@pytest.fixture
def session_single_char():
    """Сессия с одним персонажем (char_count=1)."""
    return {
        "session_id": "test-session-001",
        "name": "Александр",
        "hero_sprite_url": "https://example.github.io/repo/games/001/sprites/hero.png",
        "companion_sprite_url": None,
        "char_count": 1,
        "scenario": "birthday",
        "hero_gender": "m",
    }


@pytest.fixture
def session_two_chars():
    """Сессия с двумя персонажами (char_count=2)."""
    return {
        "session_id": "test-session-002",
        "name": "Мария",
        "hero_sprite_url": "https://example.github.io/repo/games/002/sprites/hero.png",
        "companion_sprite_url": "https://example.github.io/repo/games/002/sprites/companion.png",
        "char_count": 2,
        "scenario": "love",
        "hero_gender": "f",
    }


# === Тесты ===

# START_FUNCTION_test_all_placeholders_replaced
# START_CONTRACT:
# PURPOSE: Проверяет, что НИ ОДНОГО плейсхолдера не осталось в HTML после build().
# COMPLEXITY_SCORE: 4
# END_CONTRACT
def test_all_placeholders_replaced(session_single_char):
    """
    После build() в HTML не должно быть ни одного плейсхолдера
    вида {{PLACEHOLDER}}. Все 6 должны быть заменены.
    """
    from backend.services.game_builder import build, PLACEHOLDERS

    logger.info("[Flow][IMP:7][test_all_placeholders_replaced][RUN][Start] [TEST]")

    html = build(session_single_char)

    for placeholder in PLACEHOLDERS:
        assert placeholder not in html, (
            f"Плейсхолдер {placeholder!r} НЕ был заменён в HTML"
        )

    logger.info(
        f"[BeliefState][IMP:9][test_all_placeholders_replaced][RESULT][Pass] "
        f"Все {len(PLACEHOLDERS)} плейсхолдеров заменены [PASS]"
    )
# END_FUNCTION_test_all_placeholders_replaced


# START_FUNCTION_test_has_companion_true_when_char_count_2
# START_CONTRACT:
# PURPOSE: Проверяет, что HAS_COMPANION=true при char_count=2.
# COMPLEXITY_SCORE: 3
# END_CONTRACT
def test_has_companion_true_when_char_count_2(session_two_chars):
    """
    При char_count=2 в HTML должно присутствовать HAS_COMPANION: true.
    Это важно для JavaScript-логики в Phaser: отображение компаньона на финале.
    """
    from backend.services.game_builder import build

    logger.info("[Flow][IMP:7][test_has_companion_true_when_char_count_2][RUN][Start] [TEST]")

    html = build(session_two_chars)

    # В шаблоне: HAS_COMPANION: {{HAS_COMPANION}} → HAS_COMPANION: true
    assert "HAS_COMPANION:         true" in html or "true" in html, (
        "HAS_COMPANION должен быть true при char_count=2"
    )
    # Убедимся, что false не встречается в контексте HAS_COMPANION
    # Проверяем через window.GAME_CONFIG блок
    assert "HAS_COMPANION:         false" not in html, (
        "HAS_COMPANION не должен быть false при char_count=2"
    )

    logger.info(
        f"[BeliefState][IMP:9][test_has_companion_true_when_char_count_2][RESULT][Pass] "
        f"char_count=2 → HAS_COMPANION=true [PASS]"
    )
# END_FUNCTION_test_has_companion_true_when_char_count_2


# START_FUNCTION_test_has_companion_false_when_char_count_1
# START_CONTRACT:
# PURPOSE: Проверяет, что HAS_COMPANION=false при char_count=1.
# COMPLEXITY_SCORE: 3
# END_CONTRACT
def test_has_companion_false_when_char_count_1(session_single_char):
    """
    При char_count=1 в HTML должно присутствовать HAS_COMPANION: false.
    """
    from backend.services.game_builder import build

    logger.info("[Flow][IMP:7][test_has_companion_false_when_char_count_1][RUN][Start] [TEST]")

    html = build(session_single_char)

    assert "HAS_COMPANION:         false" in html, (
        "HAS_COMPANION должен быть false при char_count=1"
    )
    assert "HAS_COMPANION:         true" not in html, (
        "HAS_COMPANION не должен быть true при char_count=1"
    )

    logger.info(
        f"[BeliefState][IMP:9][test_has_companion_false_when_char_count_1][RESULT][Pass] "
        f"char_count=1 → HAS_COMPANION=false [PASS]"
    )
# END_FUNCTION_test_has_companion_false_when_char_count_1


# START_FUNCTION_test_player_name_substituted
# START_CONTRACT:
# PURPOSE: Проверяет, что PLAYER_NAME содержит имя из session_data в HTML.
# COMPLEXITY_SCORE: 3
# END_CONTRACT
def test_player_name_substituted(session_single_char):
    """
    После build() имя из session_data["name"] должно присутствовать в HTML.
    Плейсхолдер {{PLAYER_NAME}} должен быть заменён на "Александр".
    """
    from backend.services.game_builder import build

    logger.info("[Flow][IMP:7][test_player_name_substituted][RUN][Start] [TEST]")

    expected_name = session_single_char["name"]
    html = build(session_single_char)

    assert expected_name in html, (
        f"Имя {expected_name!r} не найдено в HTML после подстановки"
    )
    assert "{{PLAYER_NAME}}" not in html, (
        "Плейсхолдер {{PLAYER_NAME}} не был заменён"
    )

    logger.info(
        f"[BeliefState][IMP:9][test_player_name_substituted][RESULT][Pass] "
        f"name={expected_name!r} присутствует в HTML [PASS]"
    )
# END_FUNCTION_test_player_name_substituted


# START_FUNCTION_test_scenario_substituted
# START_CONTRACT:
# PURPOSE: Проверяет, что SCENARIO корректно подставлен в HTML.
# COMPLEXITY_SCORE: 3
# END_CONTRACT
def test_scenario_substituted(session_single_char, session_two_chars):
    """
    SCENARIO должен быть подставлен корректно: "birthday" и "love"
    для двух разных сессий.
    """
    from backend.services.game_builder import build

    logger.info("[Flow][IMP:7][test_scenario_substituted][RUN][Start] [TEST]")

    html_birthday = build(session_single_char)
    html_love = build(session_two_chars)

    assert '"birthday"' in html_birthday, (
        f"SCENARIO='birthday' не найден в HTML: {html_birthday[200:400]!r}"
    )
    assert '"love"' in html_love, (
        f"SCENARIO='love' не найден в HTML: {html_love[200:400]!r}"
    )

    assert "{{SCENARIO}}" not in html_birthday, "{{SCENARIO}} не заменён в html_birthday"
    assert "{{SCENARIO}}" not in html_love, "{{SCENARIO}} не заменён в html_love"

    logger.info(
        f"[BeliefState][IMP:9][test_scenario_substituted][RESULT][Pass] "
        f"SCENARIO: 'birthday' и 'love' подставлены корректно [PASS]"
    )
# END_FUNCTION_test_scenario_substituted


# START_FUNCTION_test_hero_gender_substituted
# START_CONTRACT:
# PURPOSE: Проверяет подстановку HERO_GENDER для мужского и женского вариантов.
# COMPLEXITY_SCORE: 3
# END_CONTRACT
def test_hero_gender_substituted(session_single_char, session_two_chars):
    """
    HERO_GENDER должен быть подставлен корректно: "m" и "f".
    """
    from backend.services.game_builder import build

    logger.info("[Flow][IMP:7][test_hero_gender_substituted][RUN][Start] [TEST]")

    html_m = build(session_single_char)   # hero_gender = "m"
    html_f = build(session_two_chars)     # hero_gender = "f"

    assert '"m"' in html_m, f"HERO_GENDER='m' не найден в HTML"
    assert '"f"' in html_f, f"HERO_GENDER='f' не найден в HTML"

    assert "{{HERO_GENDER}}" not in html_m, "{{HERO_GENDER}} не заменён"
    assert "{{HERO_GENDER}}" not in html_f, "{{HERO_GENDER}} не заменён"

    logger.info(
        f"[BeliefState][IMP:9][test_hero_gender_substituted][RESULT][Pass] "
        f"HERO_GENDER: 'm' и 'f' подставлены корректно [PASS]"
    )
# END_FUNCTION_test_hero_gender_substituted


# START_FUNCTION_test_sprite_urls_substituted
# START_CONTRACT:
# PURPOSE: Проверяет подстановку HERO_SPRITE_URL и COMPANION_SPRITE_URL.
# COMPLEXITY_SCORE: 4
# END_CONTRACT
def test_sprite_urls_substituted(session_single_char, session_two_chars):
    """
    HERO_SPRITE_URL должен присутствовать в HTML.
    COMPANION_SPRITE_URL должен быть подставлен (пустая строка при char_count=1).
    """
    from backend.services.game_builder import build

    logger.info("[Flow][IMP:7][test_sprite_urls_substituted][RUN][Start] [TEST]")

    html_single = build(session_single_char)
    html_two = build(session_two_chars)

    # Hero URL должен присутствовать
    hero_url = session_single_char["hero_sprite_url"]
    assert hero_url in html_single, f"HERO_SPRITE_URL {hero_url!r} не найден"

    # Companion URL при char_count=2
    companion_url = session_two_chars["companion_sprite_url"]
    assert companion_url in html_two, f"COMPANION_SPRITE_URL {companion_url!r} не найден"

    # Плейсхолдеры удалены
    assert "{{HERO_SPRITE_URL}}" not in html_single
    assert "{{COMPANION_SPRITE_URL}}" not in html_single
    assert "{{HERO_SPRITE_URL}}" not in html_two
    assert "{{COMPANION_SPRITE_URL}}" not in html_two

    logger.info(
        f"[BeliefState][IMP:9][test_sprite_urls_substituted][RESULT][Pass] "
        f"hero_url и companion_url подставлены корректно [PASS]"
    )
# END_FUNCTION_test_sprite_urls_substituted


# START_FUNCTION_test_build_returns_string
# START_CONTRACT:
# PURPOSE: Проверяет, что build() возвращает строку, а не None/bytes.
# COMPLEXITY_SCORE: 2
# END_CONTRACT
def test_build_returns_string(session_single_char):
    """
    build() всегда должна возвращать str.
    """
    from backend.services.game_builder import build

    logger.info("[Flow][IMP:7][test_build_returns_string][RUN][Start] [TEST]")

    result = build(session_single_char)

    assert isinstance(result, str), f"build() вернул {type(result)}, ожидался str"
    assert len(result) > 100, f"HTML слишком короткий: {len(result)} chars"

    logger.info(
        f"[BeliefState][IMP:9][test_build_returns_string][RESULT][Pass] "
        f"build() вернул str длиной {len(result)} chars [PASS]"
    )
# END_FUNCTION_test_build_returns_string
