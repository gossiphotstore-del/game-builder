# FILE: backend/services/game_builder.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT:
# PURPOSE: Сборка персонализированного HTML игры путём подстановки 6 плейсхолдеров
#          в game/template.html из данных сессии.
# SCOPE: Чтение шаблона, замена плейсхолдеров, возврат готовой HTML-строки.
# INPUT: session_data dict с полями name, hero_sprite_url, companion_sprite_url,
#        char_count, scenario, hero_gender.
# OUTPUT: str — полный HTML игры с подставленными значениями.
# KEYWORDS: DOMAIN(8): GameBuilder; CONCEPT(8): TemplateSubstitution; TECH(7): StringReplace
# LINKS: READS_DATA_FROM(10): game/template.html
# END_MODULE_CONTRACT
#
# START_RATIONALE:
# Q: Почему str.replace, а не Jinja2?
# A: Шаблон уже существует с конвенцией {{PLACEHOLDER}}. str.replace — нулевая зависимость,
#    предсказуемое поведение, нет конфликтов с синтаксисом JS в HTML.
# END_RATIONALE
#
# START_INVARIANTS:
# - build ВСЕГДА возвращает str.
# - Все 6 плейсхолдеров ВСЕГДА заменяются (даже если значение — пустая строка).
# END_INVARIANTS
#
# START_CHANGE_SUMMARY:
# LAST_CHANGE: [v1.0.0 - Создание game_builder (FS-4)]
# END_CHANGE_SUMMARY
#
# START_MODULE_MAP:
# FUNC 10[Читает template.html и заменяет 6 плейсхолдеров данными сессии] => build
# END_MODULE_MAP
#
# START_USE_CASES:
# - build: BackendAPI -> BuildGameHTML -> PersonalizedHTMLReturned
# END_USE_CASES

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

# Путь к шаблону игры относительно корня проекта
TEMPLATE_PATH = Path(__file__).resolve().parents[2] / "game" / "template.html"

# Список всех 6 плейсхолдеров шаблона
PLACEHOLDERS = [
    "{{PLAYER_NAME}}",
    "{{HERO_SPRITE_URL}}",
    "{{COMPANION_SPRITE_URL}}",
    "{{HAS_COMPANION}}",
    "{{SCENARIO}}",
    "{{HERO_GENDER}}",
]


# START_FUNCTION_build
# START_CONTRACT:
# PURPOSE: Читает game/template.html и подставляет 6 плейсхолдеров из session_data.
# INPUTS:
# - словарь данных сессии => session_data: dict
# OUTPUTS:
# - str — готовый HTML с подставленными значениями
# SIDE_EFFECTS: Чтение файла с диска (IMP:7)
# KEYWORDS: PATTERN(8): TemplateMethod; CONCEPT(7): StringSubstitution
# COMPLEXITY_SCORE: 5
# END_CONTRACT
def build(session_data: dict) -> str:
    """
    Считывает game/template.html с диска и последовательно заменяет все 6 плейсхолдеров
    значениями из session_data. Если companion_sprite_url отсутствует — подставляет
    пустую строку. HAS_COMPANION зависит от char_count.

    Возвращает готовую HTML-строку для публикации на GitHub Pages.
    """

    # START_BLOCK_READ_TEMPLATE: Чтение HTML-шаблона с диска
    logger.info(
        f"[IO][IMP:7][build][READ_TEMPLATE][FileRead] "
        f"Читаем шаблон: {TEMPLATE_PATH} [START]"
    )
    template_html = TEMPLATE_PATH.read_text(encoding="utf-8")
    logger.debug(
        f"[Flow][IMP:4][build][READ_TEMPLATE][Params] "
        f"template_size={len(template_html)} chars [OK]"
    )
    # END_BLOCK_READ_TEMPLATE

    # START_BLOCK_EXTRACT_VALUES: Извлечение значений из session_data
    player_name = str(session_data.get("name", ""))
    hero_sprite_url = str(session_data.get("hero_sprite_url", ""))
    companion_sprite_url = str(session_data.get("companion_sprite_url", "") or "")
    char_count = session_data.get("char_count", 1)
    has_companion = "true" if char_count == 2 else "false"
    scenario = str(session_data.get("scenario", ""))
    hero_gender = str(session_data.get("hero_gender", ""))

    logger.debug(
        f"[Flow][IMP:5][build][EXTRACT_VALUES][Params] "
        f"name={player_name!r}, scenario={scenario!r}, "
        f"hero_gender={hero_gender!r}, has_companion={has_companion} [OK]"
    )
    # END_BLOCK_EXTRACT_VALUES

    # START_BLOCK_SUBSTITUTE_PLACEHOLDERS: Подстановка 6 плейсхолдеров
    html = template_html
    substitutions = {
        "{{PLAYER_NAME}}": player_name,
        "{{HERO_SPRITE_URL}}": hero_sprite_url,
        "{{COMPANION_SPRITE_URL}}": companion_sprite_url,
        "{{HAS_COMPANION}}": has_companion,
        "{{SCENARIO}}": scenario,
        "{{HERO_GENDER}}": hero_gender,
    }

    for placeholder, value in substitutions.items():
        count_before = html.count(placeholder)
        html = html.replace(placeholder, value)
        logger.debug(
            f"[Flow][IMP:3][build][SUBSTITUTE_PLACEHOLDERS][Replace] "
            f"placeholder={placeholder}, value={value!r}, occurrences={count_before} [OK]"
        )

    logger.info(
        f"[BeliefState][IMP:9][build][SUBSTITUTE_PLACEHOLDERS][Result] "
        f"HTML собран: {len(html)} chars, "
        f"player={player_name!r}, scenario={scenario!r}, has_companion={has_companion} [OK]"
    )
    # END_BLOCK_SUBSTITUTE_PLACEHOLDERS

    # START_BLOCK_RETURN: Возврат готового HTML
    return html
    # END_BLOCK_RETURN

# END_FUNCTION_build
