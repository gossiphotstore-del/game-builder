# FILE: bot/services/backend_client.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT:
# PURPOSE: Async HTTP-клиент к FastAPI бэкенду. Инкапсулирует все обращения к REST API.
# SCOPE: CRUD сессий, запуск генерации, получение game_url. Без бизнес-логики.
# INPUT: session_id (str), user_id (int), произвольные поля для PATCH-обновлений.
# OUTPUT: Типизированные ответы: session_id строкой, game_url строкой или None.
# KEYWORDS: DOMAIN(8): HTTP; CONCEPT(9): AsyncClient; TECH(9): aiohttp; PATTERN(8): Repository
# LINKS: USES_API(9): aiohttp.ClientSession; CALLS_BACKEND(9): /sessions, /games/build
# END_MODULE_CONTRACT
#
# START_RATIONALE:
# Q: Почему aiohttp, а не httpx?
# A: aiohttp — стандартный async HTTP клиент для aiogram-проектов, минимум зависимостей.
#    ClientSession создаётся при первом обращении и кешируется в модуле (_session singleton).
#    Это избегает overhead на создание сессии при каждом запросе.
# Q: Почему таймауты проставлены явно?
# A: Backend ещё не готов — нужна явная защита от зависания polling-процесса бота.
# END_RATIONALE
#
# START_INVARIANTS:
# - Все публичные методы — async корутины.
# - Исключения HTTPError и aiohttp.ClientError логируются на IMP:9 и пробрасываются.
# - session_id — строка (UUID4).
# END_INVARIANTS
#
# START_CHANGE_SUMMARY:
# LAST_CHANGE: [v1.0.0 - FS-1: базовые операции CRUD + trigger_generation + get_game_url]
# END_CHANGE_SUMMARY
#
# START_MODULE_MAP:
# FUNC [9][Создаёт сессию пользователя, возвращает session_id] => create_session
# FUNC [8][Обновляет поля сессии PATCH-запросом] => patch_session
# FUNC [9][Запускает AI-генерацию для сессии] => trigger_generation
# FUNC [8][Получает game_url из сессии если готов] => get_game_url
# END_MODULE_MAP
#
# START_USE_CASES:
# - create_session: Bot(/start) -> CreateSession -> SessionIdReturned
# - patch_session: Bot(dialog_step) -> UpdateSessionField -> SessionUpdated
# - trigger_generation: Bot(confirm) -> TriggerAIPipeline -> GenerationStarted
# - get_game_url: Bot(polling) -> FetchGameUrl -> GameUrlOrNone
# END_USE_CASES

import logging
import aiohttp

from bot.config import settings

logger = logging.getLogger(__name__)

# Singleton aiohttp session — создаётся при первом вызове get_session()
_session: aiohttp.ClientSession | None = None

# Таймаут по умолчанию для HTTP-запросов (секунды)
DEFAULT_TIMEOUT_SECONDS = 10


# START_FUNCTION_get_session
# START_CONTRACT:
# PURPOSE: Lazy-инициализация синглтона aiohttp.ClientSession с базовым URL бэкенда.
# INPUTS: Нет
# OUTPUTS:
# - aiohttp.ClientSession - Готовая к использованию HTTP-сессия
# SIDE_EFFECTS: Создаёт глобальный _session при первом вызове.
# KEYWORDS: PATTERN(9): Singleton; CONCEPT(8): LazyInit
# COMPLEXITY_SCORE: 3
# END_CONTRACT
async def get_session() -> aiohttp.ClientSession:
    """
    Возвращает синглтон aiohttp.ClientSession для обращений к бэкенду.
    Создаёт сессию при первом вызове. Последующие вызовы возвращают кешированный экземпляр.
    Базовый URL берётся из settings.BACKEND_URL.
    """
    global _session

    # START_BLOCK_LAZY_INIT: Создание сессии при первом вызове
    if _session is None or _session.closed:
        _session = aiohttp.ClientSession(
            base_url=settings.BACKEND_URL,
            timeout=aiohttp.ClientTimeout(total=DEFAULT_TIMEOUT_SECONDS),
        )
        logger.info(
            f"[HTTP][IMP:7][get_session][LAZY_INIT][SessionCreated] "
            f"aiohttp.ClientSession создана. base_url={settings.BACKEND_URL} [SUCCESS]"
        )
    # END_BLOCK_LAZY_INIT

    return _session
# END_FUNCTION_get_session


# START_FUNCTION_create_session
# START_CONTRACT:
# PURPOSE: POST /sessions — создаёт новую сессию для пользователя на бэкенде.
# INPUTS:
# - user_id Telegram ID пользователя => user_id: int
# OUTPUTS:
# - str - UUID4 строка session_id для дальнейших операций
# SIDE_EFFECTS: Создаёт запись в Redis на бэкенде с TTL 24ч.
# KEYWORDS: PATTERN(8): Repository; CONCEPT(9): SessionInit
# COMPLEXITY_SCORE: 5
# END_CONTRACT
async def create_session(user_id: int) -> str:
    """
    Создаёт новую игровую сессию для пользователя.
    Отправляет POST /sessions с user_id, получает обратно session_id (UUID4).
    При ошибке сети или не-2xx ответе — логирует критическую ошибку и пробрасывает исключение.
    """
    session = await get_session()

    # START_BLOCK_POST_SESSION: HTTP запрос создания сессии
    try:
        async with session.post("/sessions", json={"user_id": user_id}) as resp:
            logger.info(
                f"[HTTP][IMP:7][create_session][POST_SESSION][Request] "
                f"POST /sessions user_id={user_id} status={resp.status} [INFO]"
            )
            resp.raise_for_status()
            data = await resp.json()
            session_id = data["session_id"]

            logger.info(
                f"[BeliefState][IMP:9][create_session][POST_SESSION][Result] "
                f"Сессия создана. user_id={user_id} session_id={session_id} [SUCCESS]"
            )
            return session_id

    except aiohttp.ClientError as exc:
        logger.critical(
            f"[SystemError][IMP:10][create_session][POST_SESSION][NetworkError] "
            f"Сбой создания сессии. user_id={user_id} err={exc!r} [FATAL]"
        )
        raise
    # END_BLOCK_POST_SESSION
# END_FUNCTION_create_session


# START_FUNCTION_patch_session
# START_CONTRACT:
# PURPOSE: PATCH /sessions/{session_id} — обновляет произвольные поля сессии.
# INPUTS:
# - session_id UUID сессии => session_id: str
# - Произвольные поля сессии для обновления => **fields
# OUTPUTS:
# - None (успех) / raise при ошибке
# SIDE_EFFECTS: Обновляет Redis-запись на бэкенде.
# KEYWORDS: PATTERN(8): Repository; CONCEPT(8): PartialUpdate
# COMPLEXITY_SCORE: 5
# END_CONTRACT
async def patch_session(session_id: str, **fields) -> None:
    """
    Частичное обновление сессии на бэкенде.
    Принимает именованные аргументы: scenario, char_count, hero_gender, companion_gender,
    name, hero_photo_file_id, companion_photo_file_id — любой их набор.
    Отправляет PATCH /sessions/{session_id} с JSON телом.
    """
    session = await get_session()

    # START_BLOCK_PATCH_SESSION: HTTP запрос обновления сессии
    try:
        async with session.patch(f"/sessions/{session_id}", json=fields) as resp:
            logger.info(
                f"[HTTP][IMP:7][patch_session][PATCH_SESSION][Request] "
                f"PATCH /sessions/{session_id} fields={list(fields.keys())} "
                f"status={resp.status} [INFO]"
            )
            resp.raise_for_status()

            logger.info(
                f"[BeliefState][IMP:9][patch_session][PATCH_SESSION][Updated] "
                f"Сессия обновлена. session_id={session_id} fields={list(fields.keys())} [SUCCESS]"
            )

    except aiohttp.ClientError as exc:
        logger.critical(
            f"[SystemError][IMP:10][patch_session][PATCH_SESSION][NetworkError] "
            f"Сбой обновления сессии. session_id={session_id} err={exc!r} [FATAL]"
        )
        raise
    # END_BLOCK_PATCH_SESSION
# END_FUNCTION_patch_session


# START_FUNCTION_trigger_generation
# START_CONTRACT:
# PURPOSE: POST /games/build — запускает асинхронную AI-генерацию для сессии.
# INPUTS:
# - session_id UUID сессии => session_id: str
# OUTPUTS:
# - None (запуск async pipeline на бэкенде, ответ немедленный)
# SIDE_EFFECTS: Запускает background task AI pipeline на бэкенде.
# KEYWORDS: CONCEPT(9): AsyncTrigger; PATTERN(8): FireAndForget
# COMPLEXITY_SCORE: 5
# END_CONTRACT
async def trigger_generation(session_id: str) -> None:
    """
    Запускает AI-генерацию персонажей для сессии.
    POST /games/build — бэкенд запускает pipeline асинхронно и отвечает немедленно (202).
    Не ждёт завершения генерации. Результат будет доступен через get_game_url().
    """
    session = await get_session()

    # START_BLOCK_TRIGGER_GEN: HTTP запрос запуска генерации
    try:
        async with session.post("/games/build", json={"session_id": session_id}) as resp:
            logger.info(
                f"[HTTP][IMP:7][trigger_generation][TRIGGER_GEN][Request] "
                f"POST /games/build session_id={session_id} status={resp.status} [INFO]"
            )
            resp.raise_for_status()

            logger.info(
                f"[BeliefState][IMP:9][trigger_generation][TRIGGER_GEN][Started] "
                f"Генерация запущена. session_id={session_id} [SUCCESS]"
            )

    except aiohttp.ClientError as exc:
        logger.critical(
            f"[SystemError][IMP:10][trigger_generation][TRIGGER_GEN][NetworkError] "
            f"Сбой запуска генерации. session_id={session_id} err={exc!r} [FATAL]"
        )
        raise
    # END_BLOCK_TRIGGER_GEN
# END_FUNCTION_trigger_generation


# START_FUNCTION_get_game_url
# START_CONTRACT:
# PURPOSE: GET /sessions/{session_id} — получает game_url и pipeline_error из сессии.
# INPUTS:
# - session_id UUID сессии => session_id: str
# OUTPUTS:
# - tuple[str | None, str | None] - (game_url, pipeline_error)
#   game_url — URL если генерация завершена успешно
#   pipeline_error — строка ошибки если пайплайн упал, None если ещё в процессе
# SIDE_EFFECTS: Только чтение Redis на бэкенде.
# KEYWORDS: CONCEPT(8): Polling; PATTERN(8): OptionalResult
# COMPLEXITY_SCORE: 5
# END_CONTRACT
# BUG_FIX_CONTEXT: Ранее возвращал только game_url, не проверял pipeline_error.
# Бот ждал 180 сек даже когда бэкенд уже упал через 5 сек (Gemini error).
# Теперь возвращает (game_url, error) — _poll_game_url останавливается сразу при ошибке.
async def get_game_url(session_id: str) -> tuple[str | None, str | None]:
    """
    Получает статус генерации для сессии из бэкенда.
    Возвращает (game_url, pipeline_error). Одно из двух будет None.
    При ошибке сети — возвращает (None, None) чтобы polling продолжился.
    """
    session = await get_session()

    # START_BLOCK_GET_URL: HTTP запрос получения статуса сессии
    try:
        async with session.get(f"/sessions/{session_id}") as resp:
            if resp.status == 404:
                logger.warning(
                    f"[HTTP][IMP:8][get_game_url][GET_URL][NotFound] "
                    f"Сессия не найдена. session_id={session_id} [WARN]"
                )
                return None, None

            resp.raise_for_status()
            data = await resp.json()
            game_url = data.get("game_url")
            pipeline_error = data.get("pipeline_error")

            logger.info(
                f"[BeliefState][IMP:9][get_game_url][GET_URL][Result] "
                f"session_id={session_id} game_url={game_url!r} pipeline_error={pipeline_error!r} [VALUE]"
            )
            return game_url, pipeline_error

    except aiohttp.ClientError as exc:
        logger.warning(
            f"[HTTP][IMP:8][get_game_url][GET_URL][NetworkError] "
            f"Ошибка получения game_url. session_id={session_id} err={exc!r} [WARN]"
        )
        return None, None
    # END_BLOCK_GET_URL
# END_FUNCTION_get_game_url
