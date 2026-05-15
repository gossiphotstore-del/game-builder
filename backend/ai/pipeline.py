# FILE: backend/ai/pipeline.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT:
# PURPOSE: Оркестратор AI-пайплайна генерации персонажей: цвет → генерация → постобработка.
# SCOPE: Последовательный вызов color_extractor, replicate_client, postprocessor для героя
#        и (опционально) компаньона. Asyncio-совместимость через asyncio.to_thread.
# INPUT: session_data dict с полями hero_photo_bytes, hero_gender, companion_photo_bytes,
#        companion_gender, char_count.
# OUTPUT: dict {"hero_sprite": bytes, "companion_sprite": bytes | None}
# KEYWORDS: DOMAIN(9): AIPipeline; CONCEPT(9): Orchestration; TECH(8): AsyncIO; PATTERN(8): Pipeline
# LINKS: CALLS_METHOD(10): color_extractor.extract_accent_color;
#        CALLS_METHOD(10): openrouter_client.generate_sprite;
#        CALLS_METHOD(10): postprocessor.process_sprite
# END_MODULE_CONTRACT
#
# START_RATIONALE:
# Q: Почему используется asyncio.to_thread для sync-операций?
# A: FastAPI backend работает в async event loop. Все три этапа пайплайна синхронны
#    (KMeans, Replicate polling, rembg ONNX). asyncio.to_thread делегирует их в thread pool,
#    не блокируя event loop.
# Q: Почему pipeline принимает dict, а не отдельные параметры?
# A: Сессия Redis хранится как dict. Прямая передача session_data минимизирует маршалинг.
# END_RATIONALE
#
# START_INVARIANTS:
# - run_pipeline ВСЕГДА возвращает dict с ключом "hero_sprite" (bytes).
# - "companion_sprite" присутствует и не None только при char_count==2.
# END_INVARIANTS
#
# START_CHANGE_SUMMARY:
# LAST_CHANGE: [v1.1.0 - Параллельная генерация героя и компаньона через asyncio.gather (экономия 60-120s при char_count=2).]
# PREV_CHANGE_SUMMARY: [v1.0.0 - Первичная реализация оркестратора AI Pipeline.]
# END_CHANGE_SUMMARY
#
# START_MODULE_MAP:
# FUNC 10[Асинхронный оркестратор генерации спрайтов для 1-2 персонажей] => run_pipeline
# FUNC  6[Синхронная реализация пайплайна для одного персонажа] => _generate_single_character
# END_MODULE_MAP
#
# START_USE_CASES:
# - run_pipeline: Backend API -> OrchestrateAIGeneration -> SpriteDictReturned
# END_USE_CASES

import asyncio
import logging
from typing import Optional

from backend.ai.color_extractor import extract_accent_color
from backend.ai.openrouter_client import generate_sprite
from backend.ai.postprocessor import process_sprite

logger = logging.getLogger(__name__)


# START_FUNCTION__generate_single_character
# START_CONTRACT:
# PURPOSE: Синхронная генерация одного персонажа: извлечение цвета → генерация → постобработка.
# INPUTS:
# - bytes фото персонажа => photo_bytes: bytes
# - Ключ промпта => prompt_key: str
# - Имя персонажа для логирования => character_name: str
# OUTPUTS:
# - bytes - готовый PNG спрайт с прозрачным фоном
# SIDE_EFFECTS: Сетевой вызов к Replicate API.
# KEYWORDS: PATTERN(8): PipelineStep; CONCEPT(7): SyncOrchestration
# COMPLEXITY_SCORE: 5
# END_CONTRACT
def _generate_single_character(photo_bytes: bytes, prompt_key: str, character_name: str) -> bytes:
    """
    Синхронная реализация полного цикла генерации одного персонажа.
    Шаги: extract_accent_color → generate_sprite → process_sprite.
    Используется как аргумент asyncio.to_thread в run_pipeline.
    """

    # START_BLOCK_EXTRACT_COLOR: Извлечение акцентного цвета
    logger.info(f"[Flow][IMP:7][_generate_single_character][EXTRACT_COLOR][Step1] Извлечение цвета для '{character_name}', prompt_key={prompt_key!r} [START]")
    accent_color = extract_accent_color(photo_bytes)
    logger.info(f"[BeliefState][IMP:8][_generate_single_character][EXTRACT_COLOR][Result] accent_color={accent_color!r} для '{character_name}' [SUCCESS]")
    # END_BLOCK_EXTRACT_COLOR

    # START_BLOCK_GENERATE_SPRITE: Генерация спрайта через Replicate
    logger.info(f"[APICall][IMP:8][_generate_single_character][GENERATE_SPRITE][Step2] Генерация спрайта для '{character_name}' [START]")
    raw_png_bytes = generate_sprite(photo_bytes, prompt_key, accent_color)
    logger.info(f"[BeliefState][IMP:8][_generate_single_character][GENERATE_SPRITE][Result] raw PNG: {len(raw_png_bytes)} байт для '{character_name}' [SUCCESS]")
    # END_BLOCK_GENERATE_SPRITE

    # START_BLOCK_POSTPROCESS: Постобработка (rembg + resize)
    logger.info(f"[Flow][IMP:7][_generate_single_character][POSTPROCESS][Step3] Постобработка для '{character_name}' [START]")
    sprite_bytes = process_sprite(raw_png_bytes)
    logger.info(f"[BeliefState][IMP:9][_generate_single_character][POSTPROCESS][ReturnData] Спрайт готов: {len(sprite_bytes)} байт для '{character_name}' [SUCCESS]")
    # END_BLOCK_POSTPROCESS

    return sprite_bytes
# END_FUNCTION__generate_single_character


# START_FUNCTION_run_pipeline
# START_CONTRACT:
# PURPOSE: Асинхронный оркестратор AI-пайплайна для генерации спрайтов героя и (опционально) компаньона.
# INPUTS:
# - Словарь данных сессии => session_data: dict
#   Ожидаемые ключи:
#     hero_photo_bytes: bytes            — фото героя
#     hero_gender: str                   — "m" | "f" (не используется в prompt_key для hero)
#     companion_photo_bytes: bytes|None  — фото компаньона (только при char_count=2)
#     companion_gender: str|None         — "m" | "f" (только при char_count=2)
#     char_count: int                    — 1 | 2
# OUTPUTS:
# - dict - {"hero_sprite": bytes, "companion_sprite": bytes | None}
# SIDE_EFFECTS: Сетевой вызов к Replicate API (через _generate_single_character в thread pool).
# KEYWORDS: PATTERN(9): AsyncPipeline; CONCEPT(9): Orchestration; TECH(8): asyncio.to_thread
# COMPLEXITY_SCORE: 6
# END_CONTRACT
async def run_pipeline(session_data: dict) -> dict:
    """
    Асинхронный оркестратор пайплайна генерации спрайтов персонажей.
    Для каждого персонажа выполняет: extract_accent_color → generate_sprite → process_sprite.
    Sync-операции делегируются в thread pool через asyncio.to_thread, чтобы не блокировать event loop.
    При char_count==2 обрабатывает компаньона последовательно после героя.
    Возвращает dict с готовыми PNG bytes.
    """

    # START_BLOCK_EXTRACT_PARAMS: Извлечение параметров из session_data
    hero_photo_bytes: bytes = session_data["hero_photo_bytes"]
    char_count: int = session_data.get("char_count", 1)
    companion_photo_bytes: Optional[bytes] = session_data.get("companion_photo_bytes")
    companion_gender: Optional[str] = session_data.get("companion_gender")

    logger.info(f"[Flow][IMP:7][run_pipeline][EXTRACT_PARAMS][Init] Запуск AI Pipeline: char_count={char_count}, companion_gender={companion_gender!r} [START]")
    # END_BLOCK_EXTRACT_PARAMS

    # START_BLOCK_GENERATE_SPRITES: Генерация спрайтов (герой + компаньон параллельно)
    companion_sprite_bytes: Optional[bytes] = None

    if char_count == 2:
        if companion_photo_bytes is None:
            logger.error(f"[SystemError][IMP:10][run_pipeline][GENERATE_SPRITES][Validation] char_count=2 но companion_photo_bytes=None [FATAL]")
            raise ValueError("companion_photo_bytes is required when char_count=2")

        companion_prompt_key = "companion_m" if companion_gender == "m" else "companion_f"
        logger.info(
            f"[Flow][IMP:8][run_pipeline][GENERATE_SPRITES][Parallel] "
            f"Запуск параллельной генерации героя и компаньона, companion_key={companion_prompt_key!r} [START]"
        )
        # BUG_FIX_CONTEXT: Ранее герой и компаньон генерировались последовательно, удваивая время.
        # asyncio.gather запускает оба to_thread одновременно, экономя 60-120 сек при char_count=2.
        hero_sprite_bytes, companion_sprite_bytes = await asyncio.gather(
            asyncio.to_thread(_generate_single_character, hero_photo_bytes, "hero", "hero"),
            asyncio.to_thread(_generate_single_character, companion_photo_bytes, companion_prompt_key, "companion"),
        )
        logger.info(
            f"[BeliefState][IMP:9][run_pipeline][GENERATE_SPRITES][Result] "
            f"Герой: {len(hero_sprite_bytes)}B, компаньон: {len(companion_sprite_bytes)}B [SUCCESS]"
        )
    else:
        logger.info(f"[Flow][IMP:8][run_pipeline][GENERATE_SPRITES][Single] Генерация одного героя [START]")
        hero_sprite_bytes = await asyncio.to_thread(
            _generate_single_character, hero_photo_bytes, "hero", "hero"
        )
        logger.info(f"[BeliefState][IMP:9][run_pipeline][GENERATE_SPRITES][Result] Герой: {len(hero_sprite_bytes)}B [SUCCESS]")
    # END_BLOCK_GENERATE_SPRITES

    # START_BLOCK_RETURN_RESULT: Формирование и возврат результирующего dict
    result = {
        "hero_sprite": hero_sprite_bytes,
        "companion_sprite": companion_sprite_bytes,
    }
    logger.info(f"[BeliefState][IMP:9][run_pipeline][RETURN_RESULT][ReturnData] Pipeline завершён. hero_sprite={len(hero_sprite_bytes)}B, companion_sprite={len(companion_sprite_bytes) if companion_sprite_bytes else None}B [VALUE]")
    return result
    # END_BLOCK_RETURN_RESULT
# END_FUNCTION_run_pipeline
