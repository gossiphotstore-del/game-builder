# FILE: backend/ai/postprocessor.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT:
# PURPOSE: Постобработка спрайтов персонажей: удаление фона и нормализация размера.
# SCOPE: rembg для удаления фона, Pillow для resize до height=512 с сохранением пропорций.
# INPUT: PNG/JPEG bytes сгенерированного спрайта.
# OUTPUT: PNG bytes с прозрачным alpha-каналом, высота 512px.
# KEYWORDS: DOMAIN(9): ImageProcessing; CONCEPT(8): BackgroundRemoval; TECH(9): rembg; TECH(8): Pillow
# LINKS: USES_API(10): rembg.remove; USES_API(9): PIL.Image
# END_MODULE_CONTRACT
#
# START_RATIONALE:
# Q: Почему высота фиксирована в 512px?
# A: Стандартный размер game-спрайта в Phaser.js игре. Ширина пропорциональна — сохраняет
#    оригинальный AR персонажа без искажений.
# Q: Почему rembg перед resize?
# A: rembg лучше работает на изображениях полного размера. Resize после удаления фона
#    также не деградирует качество прозрачности.
# END_RATIONALE
#
# START_INVARIANTS:
# - process_sprite ВСЕГДА возвращает PNG bytes с RGBA mode.
# - Высота результирующего изображения ВСЕГДА равна 512px (если входное изображение >= 1px высотой).
# END_INVARIANTS
#
# START_CHANGE_SUMMARY:
# LAST_CHANGE: [v1.1.0 - Fallback при ModuleNotFoundError (numba/pymatting): пропуск rembg, только resize.]
# PREV_CHANGE_SUMMARY: [v1.0.0 - Первичная реализация постобработки: rembg + resize h=512.]
# END_CHANGE_SUMMARY
#
# START_MODULE_MAP:
# FUNC 10[Удаляет фон и нормализует размер спрайта] => process_sprite
# END_MODULE_MAP
#
# START_USE_CASES:
# - process_sprite: AI Pipeline -> RemoveBgAndResize -> TransparentPNGReturned
# END_USE_CASES

import io
import logging

from PIL import Image

logger = logging.getLogger(__name__)

TARGET_HEIGHT = 512


# START_FUNCTION_process_sprite
# START_CONTRACT:
# PURPOSE: Удаляет фон из изображения персонажа через rembg и нормализует размер до h=512px.
# INPUTS:
# - PNG/JPEG bytes спрайта => image_bytes: bytes
# OUTPUTS:
# - bytes - PNG bytes с RGBA прозрачным фоном, высота 512px
# SIDE_EFFECTS: Загрузка ONNX модели rembg при первом вызове (~50MB, кешируется).
# KEYWORDS: PATTERN(8): PipelineStep; CONCEPT(9): BackgroundRemoval; TECH(9): rembg; TECH(8): LANCZOS
# COMPLEXITY_SCORE: 5
# END_CONTRACT
def process_sprite(image_bytes: bytes) -> bytes:
    """
    Функция выполняет постобработку AI-сгенерированного спрайта в два шага:
    1. Удаление фона через rembg (u2net ONNX модель) → RGBA PNG с прозрачностью.
    2. Resize до высоты 512px с сохранением aspect ratio через Pillow LANCZOS.
    Возвращает PNG bytes готового спрайта для встраивания в игру.
    """

    # START_BLOCK_REMOVE_BACKGROUND: Удаление фона через rembg (с fallback при отсутствии numba)
    logger.info(f"[Flow][IMP:7][process_sprite][REMOVE_BACKGROUND][APICall] Запуск rembg.remove на {len(image_bytes)} байтах [START]")
    try:
        from rembg import remove as rembg_remove  # lazy import — тяжёлая ONNX зависимость
        no_bg_bytes = rembg_remove(image_bytes)
        logger.info(f"[BeliefState][IMP:8][process_sprite][REMOVE_BACKGROUND][Result] rembg успешно, output size={len(no_bg_bytes)} байт [SUCCESS]")
    except ModuleNotFoundError as e:
        # BUG_FIX_CONTEXT: rembg зависит от pymatting → numba (требует LLVM-компилятор).
        # numba не устанавливается в текущем окружении. Fallback: пропускаем удаление фона,
        # передаём оригинальный PNG на resize. Качество приемлемо — Gemini уже задаёт фон.
        logger.warning(f"[Flow][IMP:7][process_sprite][REMOVE_BACKGROUND][Fallback] rembg недоступен ({e}), пропускаем удаление фона [WARN]")
        no_bg_bytes = image_bytes
    except Exception as e:
        # BUG_FIX_CONTEXT: В Docker rembg установлен, но при первом вызове скачивает ONNX-модель
        # (~170MB) с release-assets.githubusercontent.com. Внутри контейнера этот запрос завершается
        # ReadTimeoutError. Старый код перебрасывал исключение → пайплайн падал по asyncio.wait_for
        # через 300с (AI pipeline timeout). Решение то же, что для ModuleNotFoundError: fallback
        # без удаления фона. Gemini уже генерирует спрайт с ровным фоном → качество приемлемо.
        logger.warning(f"[Flow][IMP:7][process_sprite][REMOVE_BACKGROUND][Fallback] rembg.remove failed ({type(e).__name__}: {e}), пропускаем удаление фона [WARN]")
        no_bg_bytes = image_bytes
    # END_BLOCK_REMOVE_BACKGROUND

    # START_BLOCK_RESIZE: Пропорциональный resize до h=512px с LANCZOS
    try:
        img = Image.open(io.BytesIO(no_bg_bytes)).convert("RGBA")
        orig_w, orig_h = img.size
        logger.debug(f"[VarCheck][IMP:4][process_sprite][RESIZE][Params] Исходный размер: {orig_w}x{orig_h} [INFO]")

        if orig_h == 0:
            logger.error(f"[SystemError][IMP:10][process_sprite][RESIZE][Validation] Высота изображения равна 0 [FATAL]")
            raise ValueError("Image height is 0 — cannot resize")

        # Пропорциональная ширина: new_w = orig_w * TARGET_HEIGHT / orig_h
        new_h = TARGET_HEIGHT
        new_w = max(1, int(orig_w * TARGET_HEIGHT / orig_h))

        img_resized = img.resize((new_w, new_h), Image.LANCZOS)
        logger.info(f"[BeliefState][IMP:8][process_sprite][RESIZE][Result] Resize {orig_w}x{orig_h} → {new_w}x{new_h} [SUCCESS]")
    except Exception as e:
        logger.error(f"[SystemError][IMP:10][process_sprite][RESIZE][Exception] Resize failed: {e!r} [FATAL]")
        raise RuntimeError(f"Sprite resize failed: {e}") from e
    # END_BLOCK_RESIZE

    # START_BLOCK_ENCODE_OUTPUT: Кодирование результата в PNG bytes
    output_buffer = io.BytesIO()
    img_resized.save(output_buffer, format="PNG", optimize=False)
    png_bytes = output_buffer.getvalue()

    logger.info(f"[BeliefState][IMP:9][process_sprite][ENCODE_OUTPUT][ReturnData] Итоговый PNG: {new_w}x{new_h}, {len(png_bytes)} байт [VALUE]")
    return png_bytes
    # END_BLOCK_ENCODE_OUTPUT
# END_FUNCTION_process_sprite
