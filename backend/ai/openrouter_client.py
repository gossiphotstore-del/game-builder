# FILE: backend/ai/openrouter_client.py
# VERSION: 2.0.0
# START_MODULE_CONTRACT:
# PURPOSE: Клиент к OpenRouter API для генерации спрайтов персонажей через Gemini image.
#          Один вызов: фото + промпт → Gemini генерирует мультяшный спрайт напрямую.
# SCOPE: Один вызов google/gemini-2.5-flash-image с vision-input (фото) + текстовым промптом.
#        Сохраняет ту же сигнатуру generate_sprite(), что была в replicate_client.py.
# INPUT: image_bytes фотографии, prompt_key ("hero"|"companion_m"|"companion_f"), accent_color hex.
# OUTPUT: PNG bytes результата генерации.
# KEYWORDS: DOMAIN(9): AIGeneration; CONCEPT(9): VisionToImage; TECH(9): OpenRouter;
#           PATTERN(7): SingleStepGeneration; TECH(8): GeminiImage
# LINKS: USES_API(10): openrouter.ai/api/v1; READS_DATA_FROM(8): backend.config.get_settings
# END_MODULE_CONTRACT
#
# START_RATIONALE:
# Q: Почему один вызов вместо двух (vision + generation)?
# A: google/gemini-2.5-flash-image принимает изображение на вход и генерирует картинку.
#    Один вызов проще, дешевле и быстрее чем GPT-4o vision + отдельная генерация.
# Q: Почему httpx.Client(verify=False)?
# A: macOS Python SSL не верифицирует openrouter.ai (self-signed chain в dev-окружении).
# END_RATIONALE
#
# START_INVARIANTS:
# - PROMPTS содержит ровно 3 ключа: "hero", "companion_m", "companion_f".
# - generate_sprite ВСЕГДА возвращает bytes или кидает исключение.
# END_INVARIANTS
#
# START_CHANGE_SUMMARY:
# LAST_CHANGE: [v2.1.0 - FIX: добавлен extra_body={"modalities":["image","text"]} чтобы Gemini генерировал
#               изображение, а не текстовый ответ. Расширен _extract_image_bytes для Gemini native format.]
# PREV_CHANGE_SUMMARY: [v2.0.0 - Упрощение до одного вызова Gemini image (vision+generation).]
# END_CHANGE_SUMMARY
#
# START_MODULE_MAP:
# FUNC 10[Генерирует спрайт: фото+промпт → Gemini image → PNG bytes] => generate_sprite
# FUNC  7[Парсит URL или base64 из ответа Gemini и возвращает bytes] => _extract_image_bytes
# END_MODULE_MAP
#
# START_USE_CASES:
# - generate_sprite: AI Pipeline -> CallGeminiImage -> PNGSpriteReturned
# END_USE_CASES

import re
import base64
import logging
import urllib.request

logger = logging.getLogger(__name__)

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
IMAGE_MODEL = "google/gemini-2.5-flash-image"

# START_BLOCK_PROMPTS_DICT: Словарь gender-specific промптов
PROMPTS = {
    "hero": (
        "Using the reference photo, draw a cartoon caricature bobblehead of this exact person. "
        "Head occupies 50% of body height. Preserve facial features so the character is recognizable. "
        "Character seated in a Can-Am Commander UTV. "
        "Suit color: {accent_color}. Pixar/Disney quality. Blue gradient background (#1a6fd4 to #0a3a8a). "
        "Full body visible. Style: fun cartoon caricature, NOT photorealistic, NOT anime."
    ),
    "companion_f": (
        "Using the reference photo, draw a cartoon caricature bobblehead of this exact person. "
        "Head occupies 50% of body height. Preserve facial features so the character is recognizable. "
        "Standing in celebratory pose: waving, big smile. Rally suit, feminine silhouette. "
        "Suit color: {accent_color}. Pixar/Disney quality. Blue gradient background. "
        "Style: fun cartoon caricature, NOT photorealistic, NOT anime."
    ),
    "companion_m": (
        "Using the reference photo, draw a cartoon caricature bobblehead of this exact person. "
        "Head occupies 50% of body height. Preserve facial features so the character is recognizable. "
        "Standing in celebratory pose: waving, big smile. Rally suit, masculine build, broad shoulders. "
        "Suit color: {accent_color}. Pixar/Disney quality. Blue gradient background. "
        "Style: fun cartoon caricature, NOT photorealistic, NOT anime."
    ),
}
# END_BLOCK_PROMPTS_DICT


# START_FUNCTION__extract_image_bytes
# START_CONTRACT:
# PURPOSE: Извлекает байты изображения из ответа Gemini. Обрабатывает три формата:
#          base64 data URL, markdown image, обычный URL.
# INPUTS:
# - Объект ответа от OpenAI SDK => response: ChatCompletion
# OUTPUTS:
# - bytes - PNG bytes изображения
# SIDE_EFFECTS: HTTP-запрос если ответ содержит URL (не base64).
# KEYWORDS: PATTERN(7): ResponseParsing; CONCEPT(8): MultiFormatDecoding
# COMPLEXITY_SCORE: 6
# END_CONTRACT
def _extract_image_bytes(response) -> bytes:
    """
    Gemini через OpenRouter возвращает изображение в одном из трёх форматов:
    1. base64 data URL в content: "data:image/png;base64,..."
    2. Markdown: "![...](https://...)"
    3. Прямой URL: "https://..."
    Функция обрабатывает все три варианта и возвращает PNG bytes.
    """

    # START_BLOCK_PARSE_CONTENT: Извлечение content из ответа — поддержка всех форматов OpenRouter/Gemini
    content = None
    image_b64 = None  # base64 строка если ответ содержит image_data часть (formат Gemini multimodal)

    msg = response.choices[0].message

    # Лог полной структуры сообщения для диагностики
    logger.info(
        f"[Flow][IMP:7][_extract_image_bytes][PARSE_CONTENT][MsgType] "
        f"content_type={type(msg.content).__name__}, "
        f"has_model_fields={hasattr(msg, 'model_fields_set')} [INFO]"
    )

    # BUG_FIX_CONTEXT: OpenRouter Gemini возвращает изображение в нестандартном поле
    # message.images[0].image_url.url (content=null при этом). Стандартные проверки
    # по content пропускали этот случай → "пустой content и нет image_data".
    # Приоритет 0: проверяем message.images через model_dump() до разбора content.
    try:
        raw_msg = response.model_dump()["choices"][0]["message"]
        for img_item in raw_msg.get("images") or []:
            if not isinstance(img_item, dict):
                continue
            if img_item.get("type") == "image_url":
                url = (img_item.get("image_url") or {}).get("url", "")
                if url.startswith("data:image"):
                    _, b64data = url.split(",", 1)
                    img_bytes = base64.b64decode(b64data)
                    logger.info(
                        f"[BeliefState][IMP:9][_extract_image_bytes][PARSE_CONTENT][ImagesField] "
                        f"decoded {len(img_bytes)} bytes from message.images[].image_url [SUCCESS]"
                    )
                    return img_bytes
                elif url.startswith("http"):
                    content = url
    except Exception as _e:
        logger.debug(f"[Flow][IMP:3][_extract_image_bytes][PARSE_CONTENT][ImagesCheck] skip: {_e!r}")

    if isinstance(msg.content, list):
        for part in msg.content:
            # Формат dict: {"type": "image_url", "image_url": {"url": ...}}
            if isinstance(part, dict):
                ptype = part.get('type', '')
                if ptype == 'image_url':
                    content = part.get('image_url', {}).get('url', '')
                    logger.info(f"[Flow][IMP:7][_extract_image_bytes][PARSE_CONTENT][FoundImageUrl] url[:60]={str(content)[:60]!r} [INFO]")
                    break
                elif ptype == 'image' and 'image' in part:
                    # Gemini native format: {"type": "image", "image": {"data": "base64...", "mime_type": ...}}
                    img_data = part.get('image', {})
                    image_b64 = img_data.get('data') or img_data.get('image_data')
                    if image_b64:
                        logger.info(f"[Flow][IMP:7][_extract_image_bytes][PARSE_CONTENT][FoundImageData] b64_len={len(image_b64)} [INFO]")
                        break
                elif ptype == 'text':
                    content = part.get('text', '')
            # Формат объект с атрибутами
            elif hasattr(part, 'type'):
                if part.type == 'image_url':
                    content = part.image_url.url
                    logger.info(f"[Flow][IMP:7][_extract_image_bytes][PARSE_CONTENT][ObjImageUrl] url[:60]={str(content)[:60]!r} [INFO]")
                    break
                elif part.type == 'text':
                    content = getattr(part, 'text', '')
    else:
        content = msg.content

    # Проверка raw response dict на случай нестандартного ответа
    if not content and not image_b64:
        try:
            raw = response.model_dump() if hasattr(response, 'model_dump') else {}
            msg_raw = raw.get('choices', [{}])[0].get('message', {})
            raw_content = msg_raw.get('content', '')
            logger.info(f"[Flow][IMP:7][_extract_image_bytes][PARSE_CONTENT][RawDump] content_preview={str(raw_content)[:120]!r} [INFO]")
            if raw_content and raw_content != content:
                content = raw_content
        except Exception:
            pass

    logger.info(f"[Flow][IMP:7][_extract_image_bytes][PARSE_CONTENT][Result] image_b64={'yes' if image_b64 else 'no'}, content_preview={str(content)[:80]!r} [INFO]")
    # END_BLOCK_PARSE_CONTENT

    # START_BLOCK_DECODE_IMAGE: Декодирование изображения из разных форматов
    # Приоритет 1: base64 image data (Gemini native multimodal format)
    if image_b64:
        img_bytes = base64.b64decode(image_b64)
        logger.info(f"[BeliefState][IMP:9][_extract_image_bytes][DECODE_IMAGE][ImageData] decoded {len(img_bytes)} bytes [SUCCESS]")
        return img_bytes

    if not content:
        raise RuntimeError("Gemini вернул пустой content и нет image_data")

    # Приоритет 2: base64 data URL ("data:image/png;base64,...")
    if isinstance(content, str) and content.startswith("data:image"):
        header, b64data = content.split(",", 1)
        img_bytes = base64.b64decode(b64data)
        logger.info(f"[BeliefState][IMP:9][_extract_image_bytes][DECODE_IMAGE][Base64URL] decoded {len(img_bytes)} bytes [SUCCESS]")
        return img_bytes

    # Приоритет 3: URL — прямой или в markdown
    if isinstance(content, str):
        md_match = re.search(r'!\[.*?\]\((https?://\S+)\)', content)
        if md_match:
            image_url = md_match.group(1)
        elif content.strip().startswith("http"):
            image_url = content.strip()
        else:
            # Текст без изображения — полный дамп для диагностики
            logger.error(
                f"[SystemError][IMP:10][_extract_image_bytes][DECODE_IMAGE][ParseFail] "
                f"Gemini вернул текст без изображения. content={content!r} [FATAL]"
            )
            raise RuntimeError(
                f"Gemini вернул текст вместо изображения. Ответ: {content[:300]!r}"
            )

        logger.info(f"[Flow][IMP:8][_extract_image_bytes][DECODE_IMAGE][URLDownload] url={image_url[:80]} [START]")
        with urllib.request.urlopen(image_url, timeout=60) as resp:
            img_bytes = resp.read()
        logger.info(f"[BeliefState][IMP:9][_extract_image_bytes][DECODE_IMAGE][Downloaded] {len(img_bytes)} bytes [SUCCESS]")
        return img_bytes
    # END_BLOCK_DECODE_IMAGE

    raise RuntimeError(f"Неизвестный тип content от Gemini: {type(content)}")

# END_FUNCTION__extract_image_bytes


# START_FUNCTION_generate_sprite
# START_CONTRACT:
# PURPOSE: Генерирует мультяшный спрайт через google/gemini-2.5-flash-image (OpenRouter).
#          Передаёт фото + промпт в одном вызове, получает PNG bytes.
#          Сигнатура идентична replicate_client.generate_sprite() для совместимости.
# INPUTS:
# - PNG/JPEG bytes фотографии персонажа => image_bytes: bytes
# - Ключ промпта из PROMPTS => prompt_key: str ("hero"|"companion_m"|"companion_f")
# - Hex-строка акцентного цвета => accent_color: str
# OUTPUTS:
# - bytes - PNG bytes сгенерированного спрайта
# SIDE_EFFECTS: 1 сетевой вызов к OpenRouter (Gemini image). Читает OPENROUTER_API_KEY из Settings.
# KEYWORDS: PATTERN(8): SingleStepVisionGeneration; CONCEPT(9): GeminiImageGen; TECH(9): OpenRouter
# COMPLEXITY_SCORE: 6
# END_CONTRACT
def generate_sprite(image_bytes: bytes, prompt_key: str, accent_color: str) -> bytes:
    """
    Генерирует cartoon-спрайт персонажа через OpenRouter (Gemini image gen).
    Отправляет фото + промпт в один вызов — Gemini видит лицо и рисует мультяшного персонажа.
    Алгоритм:
    1. Валидация prompt_key, получение api_key из Settings.
    2. Сборка промпта с подстановкой accent_color.
    3. Кодирование фото в base64 data URI.
    4. Один вызов Gemini image через chat.completions (vision-input + image-output).
    5. Парсинг и возврат PNG bytes.
    """

    # START_BLOCK_VALIDATE_AND_INIT: Валидация и инициализация клиента
    if prompt_key not in PROMPTS:
        raise ValueError(
            f"[generate_sprite] Неизвестный prompt_key: {prompt_key!r}. "
            f"Допустимые: {list(PROMPTS.keys())}"
        )

    from backend.config import get_settings
    import httpx
    from openai import OpenAI

    settings = get_settings()
    api_key = settings.OPENROUTER_API_KEY

    client = OpenAI(
        base_url=OPENROUTER_BASE_URL,
        api_key=api_key,
        http_client=httpx.Client(verify=False),
    )

    prompt = PROMPTS[prompt_key].format(accent_color=accent_color)
    img_b64 = base64.b64encode(image_bytes).decode("utf-8")
    img_data_uri = f"data:image/jpeg;base64,{img_b64}"

    logger.info(
        f"[Flow][IMP:7][generate_sprite][VALIDATE_AND_INIT][Params] "
        f"prompt_key={prompt_key!r}, accent_color={accent_color!r}, "
        f"image_size={len(image_bytes)} bytes, model={IMAGE_MODEL!r} [START]"
    )
    # END_BLOCK_VALIDATE_AND_INIT

    # START_BLOCK_GEMINI_CALL: Вызов Gemini image gen с фото на входе
    logger.info(f"[APICall][IMP:8][generate_sprite][GEMINI_CALL][Request] Отправка фото + промпта в Gemini [START]")
    try:
        response = client.chat.completions.create(
            model=IMAGE_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": img_data_uri},
                        },
                        {
                            "type": "text",
                            "text": prompt,
                        },
                    ],
                }
            ],
            # BUG_FIX_CONTEXT: Без modalities Gemini отвечал текстом вместо изображения.
            # extra_body передаёт дополнительные поля напрямую в тело запроса OpenRouter.
            extra_body={"modalities": ["image", "text"]},
        )
        logger.info(f"[APICall][IMP:8][generate_sprite][GEMINI_CALL][Response] Ответ получен [SUCCESS]")

    except Exception as e:
        logger.error(f"[SystemError][IMP:10][generate_sprite][GEMINI_CALL][Exception] Gemini ошибка: {e!r} [FATAL]")
        raise RuntimeError(f"Gemini image API error: {e}") from e
    # END_BLOCK_GEMINI_CALL

    # START_BLOCK_EXTRACT_AND_RETURN: Извлечение PNG bytes из ответа
    try:
        png_bytes = _extract_image_bytes(response)
    except Exception as extract_err:
        # Дамп полного ответа в файл для диагностики формата Gemini
        try:
            import json as _json
            raw_dump = response.model_dump() if hasattr(response, 'model_dump') else {}
            with open("/tmp/gemini_debug.json", "w") as _f:
                _json.dump(raw_dump, _f, indent=2, default=str)
            logger.error(
                f"[SystemError][IMP:10][generate_sprite][EXTRACT_AND_RETURN][ParseFail] "
                f"Ошибка парсинга: {extract_err!r}. Дамп сохранён в /tmp/gemini_debug.json [FAIL]"
            )
        except Exception:
            pass
        raise
    logger.info(f"[BeliefState][IMP:9][generate_sprite][EXTRACT_AND_RETURN][ReturnData] Спрайт готов: {len(png_bytes)} байт [SUCCESS]")
    return png_bytes
    # END_BLOCK_EXTRACT_AND_RETURN

# END_FUNCTION_generate_sprite
