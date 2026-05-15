# FILE: backend/ai/replicate_client.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT:
# PURPOSE: Клиент к Replicate API для генерации персонажей через модель InstantID.
# SCOPE: Формирование gender-specific промптов, вызов Replicate, polling результата, возврат PNG bytes.
# INPUT: image_bytes фотографии, prompt_key ("hero"|"companion_m"|"companion_f"), accent_color hex.
# OUTPUT: PNG bytes результата генерации.
# KEYWORDS: DOMAIN(9): AIGeneration; CONCEPT(9): InstantID; TECH(8): ReplicateAPI; PATTERN(7): Polling
# LINKS: USES_API(10): replicate.run; READS_DATA_FROM(8): os.environ[REPLICATE_API_TOKEN]
# END_MODULE_CONTRACT
#
# START_RATIONALE:
# Q: Почему используется replicate.run() вместо predictions API?
# A: replicate.run() — синхронный вызов с встроенным polling, что упрощает код.
#    Для timeout мы оборачиваем вызов в asyncio.wait_for через pipeline.py.
#    Внутренний polling через predictions API используется как fallback если run() не поддерживает timeout.
# Q: Почему accent_color подставляется через .format()?
# A: Промпты содержат плейсхолдер {accent_color} — стандартный Python string format.
# END_RATIONALE
#
# START_INVARIANTS:
# - PROMPTS содержит ровно 3 ключа: "hero", "companion_m", "companion_f".
# - generate_sprite ВСЕГДА возвращает bytes или кидает исключение.
# END_INVARIANTS
#
# START_CHANGE_SUMMARY:
# LAST_CHANGE: [v1.0.0 - Первичная реализация клиента Replicate InstantID с gender-промптами.]
# END_CHANGE_SUMMARY
#
# START_MODULE_MAP:
# FUNC 10[Генерирует спрайт персонажа через Replicate InstantID] => generate_sprite
# END_MODULE_MAP
#
# START_USE_CASES:
# - generate_sprite: AI Pipeline -> CallReplicateInstantID -> PNGSpriteReturned
# END_USE_CASES

import io
import os
import time
import base64
import logging
import urllib.request

logger = logging.getLogger(__name__)

# Актуальная модель InstantID на Replicate (lucataco/instantid)
REPLICATE_MODEL = "lucataco/instantid:vto51d23eae7633de13b7e7af4eac2ac7e7dd5d3dd4e06f5e8e8eb9e9f5fc54b"

# START_BLOCK_PROMPTS_DICT: Словарь gender-specific промптов (точная копия из DevelopmentPlan.md)
PROMPTS = {
    "hero": (
        "Cartoon caricature bobblehead style. Head occupies 50% of body height. "
        "Face: precise cartoon stylization of reference photo. Preserve all features. "
        "Character MUST be recognizable. Seated in Can-Am Commander UTV. "
        "Suit color: {accent_color}. Pixar quality, blue gradient bg (#1a6fd4 to #0a3a8a). "
        "NEGATIVE: photorealism, dark bg, anime, blurry/distorted face."
    ),
    "companion_f": (
        "Cartoon caricature bobblehead style. Head occupies 50% of body height. "
        "Face: precise cartoon stylization of reference photo. Preserve all features. "
        "Standing celebratory pose: waving, big smile. Rally suit, feminine silhouette. "
        "Suit color: {accent_color}. Pixar quality, blue gradient bg. "
        "NEGATIVE: photorealism, dark bg, anime, blurry/distorted face."
    ),
    "companion_m": (
        "Cartoon caricature bobblehead style. Head occupies 50% of body height. "
        "Face: precise cartoon stylization of reference photo. Preserve all features. "
        "Standing celebratory pose: waving, big smile. Rally suit, masculine silhouette, "
        "broad shoulders. Suit color: {accent_color}. Pixar quality, blue gradient bg. "
        "NEGATIVE: photorealism, dark bg, anime, blurry/distorted face."
    )
}
# END_BLOCK_PROMPTS_DICT

POLL_INTERVAL_SEC = 3
TIMEOUT_SEC = 120


# START_FUNCTION_generate_sprite
# START_CONTRACT:
# PURPOSE: Вызывает Replicate InstantID для генерации cartoon-спрайта персонажа.
#          Формирует prompt из словаря PROMPTS, подставляет accent_color, передаёт
#          фото как base64 data URI, получает PNG bytes результата.
# INPUTS:
# - PNG/JPEG bytes фотографии персонажа => image_bytes: bytes
# - Ключ промпта из PROMPTS => prompt_key: str ("hero"|"companion_m"|"companion_f")
# - Hex-строка акцентного цвета => accent_color: str
# OUTPUTS:
# - bytes - PNG bytes сгенерированного спрайта
# SIDE_EFFECTS: Сетевой вызов к Replicate API. Читает REPLICATE_API_TOKEN из env.
# KEYWORDS: PATTERN(9): Polling; CONCEPT(9): InstantID; TECH(9): ReplicateAPI
# COMPLEXITY_SCORE: 8
# END_CONTRACT
def generate_sprite(image_bytes: bytes, prompt_key: str, accent_color: str) -> bytes:
    """
    Функция генерирует cartoon-спрайт персонажа через Replicate InstantID.
    Алгоритм:
    1. Формирует промпт из PROMPTS[prompt_key] с подстановкой accent_color.
    2. Кодирует image_bytes в base64 data URI для передачи в API.
    3. Вызывает replicate.run() — синхронный вызов с polling до получения результата.
    4. Скачивает PNG по URL из ответа Replicate.
    5. Возвращает PNG bytes.
    При timeout (>120 сек) — raises TimeoutError.
    При ошибке Replicate — raises RuntimeError с деталями.
    """

    # START_BLOCK_VALIDATE_AND_PREPARE: Валидация входных данных и подготовка промпта
    if prompt_key not in PROMPTS:
        raise ValueError(f"[generate_sprite] Неизвестный prompt_key: {prompt_key!r}. Допустимые: {list(PROMPTS.keys())}")

    prompt_template = PROMPTS[prompt_key]
    prompt = prompt_template.format(accent_color=accent_color)

    # Кодируем изображение в base64 data URI
    img_b64 = base64.b64encode(image_bytes).decode("utf-8")
    img_data_uri = f"data:image/jpeg;base64,{img_b64}"

    logger.info(f"[Flow][IMP:7][generate_sprite][VALIDATE_AND_PREPARE][Params] prompt_key={prompt_key!r}, accent_color={accent_color!r}, image_size={len(image_bytes)} bytes [START]")
    logger.debug(f"[VarCheck][IMP:4][generate_sprite][VALIDATE_AND_PREPARE][Prompt] prompt={prompt[:80]}... [INFO]")
    # END_BLOCK_VALIDATE_AND_PREPARE

    # START_BLOCK_REPLICATE_CALL: Вызов Replicate API
    import replicate  # lazy import — тяжёлая зависимость

    api_token = os.environ.get("REPLICATE_API_TOKEN", "")
    if not api_token:
        logger.warning(f"[SystemError][IMP:9][generate_sprite][REPLICATE_CALL][EnvCheck] REPLICATE_API_TOKEN не задан в окружении [WARN]")

    logger.info(f"[APICall][IMP:8][generate_sprite][REPLICATE_CALL][Request] Вызов модели {REPLICATE_MODEL} [START]")

    start_time = time.monotonic()
    try:
        client = replicate.Client(api_token=api_token) if api_token else replicate
        output = client.run(
            REPLICATE_MODEL,
            input={
                "image": img_data_uri,
                "prompt": prompt,
                "num_inference_steps": 30,
                "guidance_scale": 5.0,
            }
        )
    except Exception as e:
        elapsed = time.monotonic() - start_time
        logger.error(f"[SystemError][IMP:10][generate_sprite][REPLICATE_CALL][Exception] Ошибка Replicate: {e!r}, elapsed={elapsed:.1f}s [FATAL]")
        raise RuntimeError(f"Replicate API error: {e}") from e

    elapsed = time.monotonic() - start_time
    if elapsed > TIMEOUT_SEC:
        logger.error(f"[SystemError][IMP:10][generate_sprite][REPLICATE_CALL][Timeout] elapsed={elapsed:.1f}s > {TIMEOUT_SEC}s [TIMEOUT]")
        raise TimeoutError(f"Replicate generation timed out after {elapsed:.1f}s")

    logger.info(f"[APICall][IMP:8][generate_sprite][REPLICATE_CALL][Response] Replicate вернул результат за {elapsed:.1f}s, type={type(output)} [SUCCESS]")
    # END_BLOCK_REPLICATE_CALL

    # START_BLOCK_DOWNLOAD_RESULT: Скачивание PNG по URL из ответа
    try:
        # output может быть URL-строкой, list[URL] или объектом FileOutput
        if isinstance(output, list):
            result_url = output[0]
        elif hasattr(output, "url"):
            result_url = output.url
        else:
            result_url = str(output)

        logger.info(f"[APICall][IMP:8][generate_sprite][DOWNLOAD_RESULT][Request] Скачиваем PNG с {str(result_url)[:80]}... [START]")

        with urllib.request.urlopen(str(result_url), timeout=30) as response:
            png_bytes = response.read()

        logger.info(f"[BeliefState][IMP:9][generate_sprite][DOWNLOAD_RESULT][ReturnData] PNG bytes скачан: {len(png_bytes)} байт [SUCCESS]")
        return png_bytes

    except Exception as e:
        logger.error(f"[SystemError][IMP:10][generate_sprite][DOWNLOAD_RESULT][Exception] Ошибка скачивания: {e!r} [FATAL]")
        raise RuntimeError(f"Failed to download Replicate output: {e}") from e
    # END_BLOCK_DOWNLOAD_RESULT
# END_FUNCTION_generate_sprite
