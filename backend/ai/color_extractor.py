# FILE: backend/ai/color_extractor.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT:
# PURPOSE: Извлечение акцентного цвета из фотографии персонажа (цвет одежды).
# SCOPE: K-Means кластеризация нижней половины изображения с фильтрацией нерелевантных цветов.
# INPUT: PNG/JPEG bytes изображения.
# OUTPUT: Hex-строка акцентного цвета (#rrggbb) или fallback синий (#1a6fd4).
# KEYWORDS: DOMAIN(9): ImageProcessing; CONCEPT(8): ColorClustering; TECH(9): KMeans
# LINKS: USES_API(9): sklearn.cluster.KMeans; USES_API(8): PIL.Image; USES_API(8): colorsys
# END_MODULE_CONTRACT
#
# START_RATIONALE:
# Q: Почему берётся нижняя половина изображения?
# A: Верхняя половина содержит лицо и кожный тон, которые должны быть исключены.
#    Нижняя половина (≈ одежда) даёт наиболее релевантный акцентный цвет.
# Q: Почему k=5 кластеров?
# A: 5 кластеров достаточно для охвата основных цветов одежды без избыточных вычислений.
#    Из них фильтруются кожный, белый и чёрный — остаётся 1-3 реальных цвета одежды.
# END_RATIONALE
#
# START_INVARIANTS:
# - Функция ВСЕГДА возвращает строку формата #rrggbb.
# - При отсутствии подходящего кластера ВСЕГДА возвращается fallback "#1a6fd4".
# END_INVARIANTS
#
# START_CHANGE_SUMMARY:
# LAST_CHANGE: [v1.0.0 - Первичная реализация color_extractor с K-Means и фильтрацией.]
# END_CHANGE_SUMMARY
#
# START_MODULE_MAP:
# FUNC 10[Основная функция: извлекает hex акцентного цвета из bytes изображения] => extract_accent_color
# FUNC  5[Вспомогательная: проверяет, является ли RGB-цвет нерелевантным] => _is_excluded_color
# END_MODULE_MAP
#
# START_USE_CASES:
# - extract_accent_color: AI Pipeline -> ExtractClothingColor -> AccentColorHexReturned
# END_USE_CASES

import io
import logging
import colorsys

import numpy as np
from PIL import Image
from sklearn.cluster import KMeans

logger = logging.getLogger(__name__)

# Fallback colour when all clusters are excluded
FALLBACK_COLOR = "#1a6fd4"

# START_FUNCTION__is_excluded_color
# START_CONTRACT:
# PURPOSE: Определяет, попадает ли RGB-цвет в исключённые диапазоны (кожный, белый, чёрный).
# INPUTS:
# - RGB-триплет => r: int, g: int, b: int
# OUTPUTS:
# - bool - True если цвет должен быть исключён
# SIDE_EFFECTS: Нет.
# KEYWORDS: CONCEPT(7): ColorFilter; PATTERN(6): ThresholdCheck
# COMPLEXITY_SCORE: 3
# END_CONTRACT
def _is_excluded_color(r: int, g: int, b: int) -> bool:
    """
    Проверяет три условия исключения:
    1. Кожный тон: R∈[170-255], G∈[120-200], B∈[90-170] — приближённый диапазон.
    2. Белый: R>220 И G>220 И B>220.
    3. Чёрный: R<40 И G<40 И B<40.
    Возвращает True если хотя бы одно условие выполнено.
    """
    is_skin = (170 <= r <= 255) and (120 <= g <= 200) and (90 <= b <= 170)
    is_white = r > 220 and g > 220 and b > 220
    is_black = r < 40 and g < 40 and b < 40
    return is_skin or is_white or is_black
# END_FUNCTION__is_excluded_color


# START_FUNCTION_extract_accent_color
# START_CONTRACT:
# PURPOSE: Выполняет K-Means кластеризацию нижней половины изображения и возвращает
#          наиболее насыщенный акцентный цвет, исключая кожный, белый и чёрный.
# INPUTS:
# - PNG/JPEG bytes изображения => image_bytes: bytes
# OUTPUTS:
# - str - Hex-строка "#rrggbb" акцентного цвета
# SIDE_EFFECTS: Нет (чистая функция).
# KEYWORDS: PATTERN(9): KMeansClustering; CONCEPT(8): ColorSaturationRanking; TECH(9): SKLearn
# COMPLEXITY_SCORE: 7
# END_CONTRACT
def extract_accent_color(image_bytes: bytes) -> str:
    """
    Функция извлекает акцентный цвет одежды из фотографии персонажа.
    Алгоритм: декодирует изображение → берёт нижние 50% по высоте (зона одежды) →
    применяет K-Means с k=5 → фильтрует нерелевантные кластеры (кожа, белый, чёрный) →
    из оставшихся выбирает наиболее насыщенный по HSV → возвращает hex.
    При отсутствии подходящих кластеров — возвращает fallback "#1a6fd4".
    """

    # START_BLOCK_DECODE_IMAGE: Декодирование bytes в PIL Image
    logger.debug(f"[Flow][IMP:4][extract_accent_color][DECODE_IMAGE][Init] Декодирование image_bytes размером {len(image_bytes)} байт [START]")
    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        width, height = img.size
        logger.debug(f"[VarCheck][IMP:4][extract_accent_color][DECODE_IMAGE][Params] Размер изображения: {width}x{height} [INFO]")
    except Exception as e:
        logger.error(f"[SystemError][IMP:10][extract_accent_color][DECODE_IMAGE][Exception] Не удалось декодировать изображение: {e} [FATAL]")
        return FALLBACK_COLOR
    # END_BLOCK_DECODE_IMAGE

    # START_BLOCK_CROP_LOWER_HALF: Вырезание нижней половины изображения (зона одежды)
    lower_half_top = height // 2
    img_crop = img.crop((0, lower_half_top, width, height))
    pixels = np.array(img_crop).reshape(-1, 3).astype(np.float32)
    logger.debug(f"[VarCheck][IMP:4][extract_accent_color][CROP_LOWER_HALF][Params] Пикселей в нижней половине: {len(pixels)} [INFO]")
    # END_BLOCK_CROP_LOWER_HALF

    # START_BLOCK_KMEANS_CLUSTERING: K-Means кластеризация (k=5)
    logger.info(f"[Flow][IMP:7][extract_accent_color][KMEANS_CLUSTERING][APICall] Запуск KMeans k=5 на {len(pixels)} пикселях [START]")
    try:
        n_clusters = min(5, len(pixels))
        kmeans = KMeans(n_clusters=n_clusters, n_init=10, random_state=42)
        kmeans.fit(pixels)
        centers = kmeans.cluster_centers_  # shape: (k, 3), float32 RGB
        logger.info(f"[BeliefState][IMP:8][extract_accent_color][KMEANS_CLUSTERING][Result] Кластеры найдены: {len(centers)} [SUCCESS]")
    except Exception as e:
        logger.error(f"[SystemError][IMP:10][extract_accent_color][KMEANS_CLUSTERING][Exception] KMeans failed: {e} [FATAL]")
        return FALLBACK_COLOR
    # END_BLOCK_KMEANS_CLUSTERING

    # START_BLOCK_FILTER_AND_RANK: Фильтрация нерелевантных цветов + ранжирование по насыщенности
    candidates = []
    for center in centers:
        r, g, b = int(center[0]), int(center[1]), int(center[2])
        if _is_excluded_color(r, g, b):
            logger.debug(f"[VarCheck][IMP:3][extract_accent_color][FILTER_AND_RANK][ConditionCheck] Кластер RGB({r},{g},{b}) исключён [FILTERED]")
            continue
        # Перевод в HSV для оценки насыщенности
        h, s, v = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
        candidates.append((s, r, g, b))
        logger.debug(f"[VarCheck][IMP:3][extract_accent_color][FILTER_AND_RANK][ConditionCheck] Кандидат RGB({r},{g},{b}), saturation={s:.3f} [CANDIDATE]")

    logger.info(f"[BeliefState][IMP:9][extract_accent_color][FILTER_AND_RANK][Result] Кандидатов после фильтрации: {len(candidates)} из {len(centers)} [VALUE]")
    # END_BLOCK_FILTER_AND_RANK

    # START_BLOCK_SELECT_AND_RETURN: Выбор наиболее насыщенного цвета и возврат hex
    if not candidates:
        logger.warning(f"[BeliefState][IMP:9][extract_accent_color][SELECT_AND_RETURN][Fallback] Все кластеры исключены, возвращаем fallback {FALLBACK_COLOR} [FALLBACK]")
        return FALLBACK_COLOR

    # Сортируем по насыщенности (убывание), берём первый
    candidates.sort(key=lambda x: x[0], reverse=True)
    _, r, g, b = candidates[0]
    hex_color = f"#{r:02x}{g:02x}{b:02x}"

    logger.info(f"[BeliefState][IMP:9][extract_accent_color][SELECT_AND_RETURN][ReturnData] Акцентный цвет: {hex_color} (saturation={candidates[0][0]:.3f}) [VALUE]")
    return hex_color
    # END_BLOCK_SELECT_AND_RETURN
# END_FUNCTION_extract_accent_color
