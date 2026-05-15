# FILE: backend/api/games.py
# VERSION: 2.0.0
# START_MODULE_CONTRACT:
# PURPOSE: FastAPI роутер для запуска AI-генерации и публикации игры.
#          POST /games/build — fire-and-forget: принимает session_id, запускает пайплайн
#          в BackgroundTasks, немедленно возвращает 202. Результат (game_url) сохраняется
#          в Redis и доступен через GET /sessions/{id} (polling из бота).
# SCOPE: Оркестрация всех сервисов для сборки и публикации персонализированной игры.
# INPUT: {"session_id": str}
# OUTPUT: {"status": "accepted"} — немедленно (202)
# KEYWORDS: DOMAIN(10): GameBuild; CONCEPT(10): Orchestration; TECH(9): AsyncFastAPI
#           PATTERN(9): FireAndForget; CONCEPT(9): BackgroundTask
# LINKS: CALLS_METHOD(10): RedisClient; CALLS_METHOD(10): ai_pipeline;
#        CALLS_METHOD(10): game_builder; CALLS_METHOD(10): GitHubPublisher
# END_MODULE_CONTRACT
#
# START_RATIONALE:
# Q: Почему BackgroundTasks вместо синхронного выполнения?
# A: AI pipeline (Gemini image gen) занимает 60-120+ сек. Бот имеет таймаут 10 сек на
#    HTTP запрос. Синхронный endpoint → гарантированный TimeoutError в боте.
#    BackgroundTasks: бот получает 202 немедленно, опрашивает GET /sessions/{id} пока
#    пайплайн работает в фоне и сохраняет game_url в Redis по завершении.
# BUG_FIX_CONTEXT: v1.0.0 выполнял пайплайн синхронно — бот получал TimeoutError(10s)
#    до завершения генерации. Переведён на BackgroundTasks + polling архитектуру.
# Q: Почему фото скачивается здесь, а не в боте?
# A: Telegram file_id временный. Скачивание в момент генерации — надёжнее.
#    Бот хранит только file_id, backend скачивает по запросу.
# END_RATIONALE
#
# START_CHANGE_SUMMARY:
# LAST_CHANGE: [v2.0.0 - Переход на BackgroundTasks: POST /games/build возвращает 202 немедленно.
#               Пайплайн запускается в фоне, game_url сохраняется в Redis по завершении.]
# PREV_CHANGE_SUMMARY: [v1.0.0 - Создание games router (FS-4, тест-версия без refund)]
# END_CHANGE_SUMMARY
#
# START_MODULE_MAP:
# FUNC 10[POST /games/build — полный цикл генерации и публикации игры] => build_game
# FUNC  8[Скачивание фото с Telegram File API по file_id]              => _download_telegram_photo
# END_MODULE_MAP
#
# START_USE_CASES:
# - build_game: BotClient -> TriggerGameBuild -> GameURLReturned
# - _download_telegram_photo: build_game -> FetchTelegramPhoto -> PhotoBytesReturned
# END_USE_CASES

import asyncio
import logging
from typing import Optional

import aiohttp
from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from pydantic import BaseModel

from backend.services import game_builder as game_builder_module

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/games", tags=["games"])

BUILD_TIMEOUT_SECONDS = 300


class BuildGameRequest(BaseModel):
    session_id: str


class BuildGameResponse(BaseModel):
    status: str


# START_FUNCTION__download_telegram_photo
# START_CONTRACT:
# PURPOSE: Скачивает байты фото с Telegram File API по file_id.
# INPUTS:
# - идентификатор файла в Telegram => file_id: str
# - токен бота Telegram => bot_token: str
# OUTPUTS:
# - bytes — байты изображения
# SIDE_EFFECTS: 2 HTTP запроса к Telegram API (IMP:8)
# KEYWORDS: PATTERN(7): TelegramFileAPI; CONCEPT(8): AsyncHTTP
# COMPLEXITY_SCORE: 6
# END_CONTRACT
async def _download_telegram_photo(file_id: str, bot_token: str) -> bytes:
    """
    Скачивает фото из Telegram по file_id в два этапа:
    1. GET getFile → получить file_path
    2. GET /file/bot{token}/{file_path} → скачать байты

    Поднимает RuntimeError если Telegram возвращает ошибку.
    """
    # START_BLOCK_GET_FILE_PATH: Получение file_path через getFile
    get_file_url = f"https://api.telegram.org/bot{bot_token}/getFile?file_id={file_id}"

    # BUG_FIX_CONTEXT: macOS Python SSL не верифицирует api.telegram.org (self-signed chain).
    #   ssl=False отключает проверку сертификата для внутренних вызовов Telegram API.
    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False)) as session:
        async with session.get(get_file_url) as resp:
            if resp.status != 200:
                text = await resp.text()
                logger.error(
                    f"[SystemError][IMP:10][_download_telegram_photo][GET_FILE_PATH][Error] "
                    f"file_id={file_id}, status={resp.status}, body={text[:200]!r} [FAIL]"
                )
                raise RuntimeError(f"Telegram getFile failed: status={resp.status}")
            data = await resp.json()

    if not data.get("ok"):
        raise RuntimeError(f"Telegram getFile error: {data}")

    file_path = data["result"]["file_path"]
    logger.info(
        f"[IO][IMP:8][_download_telegram_photo][GET_FILE_PATH][Result] "
        f"file_id={file_id}, file_path={file_path!r} [OK]"
    )
    # END_BLOCK_GET_FILE_PATH

    # START_BLOCK_DOWNLOAD_PHOTO: Скачивание байтов файла
    download_url = f"https://api.telegram.org/file/bot{bot_token}/{file_path}"

    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False)) as session:
        async with session.get(download_url) as resp:
            if resp.status != 200:
                raise RuntimeError(f"Telegram file download failed: status={resp.status}")
            photo_bytes = await resp.read()

    logger.info(
        f"[IO][IMP:8][_download_telegram_photo][DOWNLOAD_PHOTO][Result] "
        f"file_id={file_id}, size={len(photo_bytes)} bytes [OK]"
    )
    return photo_bytes
    # END_BLOCK_DOWNLOAD_PHOTO

# END_FUNCTION__download_telegram_photo


# START_FUNCTION__run_pipeline_bg
# START_CONTRACT:
# PURPOSE: Фоновая корутина полного цикла генерации: фото → AI pipeline → спрайты → HTML → публикация.
#          При завершении сохраняет game_url в Redis. При ошибке — сохраняет pipeline_error.
# INPUTS:
# - UUID сессии => session_id: str
# - dict данных сессии из Redis => session: dict
# - RedisClient для записи результата => redis
# - GitHubPublisher для загрузки спрайтов и HTML => publisher
# - Settings с BOT_TOKEN => settings
# OUTPUTS:
# - None (сайд-эффект: запись game_url в Redis)
# SIDE_EFFECTS: Telegram API, Gemini image API, GitHub API, Redis write.
# KEYWORDS: PATTERN(10): BackgroundTask; CONCEPT(9): AsyncPipeline; PATTERN(9): FireAndForget
# COMPLEXITY_SCORE: 9
# END_CONTRACT
async def _run_pipeline_bg(session_id: str, session: dict, redis, publisher, settings) -> None:
    """
    Фоновая корутина, запускаемая через FastAPI BackgroundTasks после ответа 202.
    Выполняет полный цикл:
      1. Скачать фото героя (и компаньона) с Telegram API
      2. Запустить AI pipeline (Gemini image gen)
      3. Загрузить PNG-спрайты на GitHub Pages
      4. Собрать HTML из шаблона
      5. Опубликовать HTML на GitHub Pages
      6. Сохранить game_url в Redis (бот найдёт его при polling GET /sessions/{id})
    При ошибке — сохраняет pipeline_error в Redis для диагностики.
    """

    # START_BLOCK_DOWNLOAD_PHOTOS: Скачивание фото с Telegram API
    logger.info(
        f"[Flow][IMP:8][_run_pipeline_bg][DOWNLOAD_PHOTOS][Start] "
        f"session_id={session_id} [START]"
    )
    try:
        hero_file_id = session.get("hero_photo_file_id")
        hero_photo_bytes: Optional[bytes] = None
        if hero_file_id:
            hero_photo_bytes = await _download_telegram_photo(
                file_id=hero_file_id,
                bot_token=settings.BOT_TOKEN,
            )
            logger.info(
                f"[IO][IMP:8][_run_pipeline_bg][DOWNLOAD_PHOTOS][Hero] "
                f"file_id={hero_file_id!r}, size={len(hero_photo_bytes)} bytes [OK]"
            )

        companion_photo_bytes: Optional[bytes] = None
        companion_file_id = session.get("companion_photo_file_id")
        if companion_file_id and session.get("char_count") == 2:
            companion_photo_bytes = await _download_telegram_photo(
                file_id=companion_file_id,
                bot_token=settings.BOT_TOKEN,
            )
            logger.info(
                f"[IO][IMP:8][_run_pipeline_bg][DOWNLOAD_PHOTOS][Companion] "
                f"file_id={companion_file_id!r}, size={len(companion_photo_bytes)} bytes [OK]"
            )
    except Exception as e:
        logger.error(
            f"[SystemError][IMP:10][_run_pipeline_bg][DOWNLOAD_PHOTOS][Error] "
            f"session_id={session_id}, err={e!r} [FAIL]"
        )
        session["pipeline_error"] = f"Photo download failed: {e}"
        await redis.save_session(session_id, session)
        return
    # END_BLOCK_DOWNLOAD_PHOTOS

    # START_BLOCK_AI_PIPELINE: Запуск AI генерации
    try:
        from backend.ai.pipeline import run_pipeline

        session_for_pipeline = dict(session)
        session_for_pipeline["hero_photo_bytes"] = hero_photo_bytes
        session_for_pipeline["companion_photo_bytes"] = companion_photo_bytes

        logger.info(
            f"[IO][IMP:9][_run_pipeline_bg][AI_PIPELINE][Run] "
            f"session_id={session_id} [START]"
        )
        sprites = await asyncio.wait_for(
            run_pipeline(session_for_pipeline),
            timeout=BUILD_TIMEOUT_SECONDS,
        )
        logger.info(
            f"[BeliefState][IMP:9][_run_pipeline_bg][AI_PIPELINE][Result] "
            f"session_id={session_id}, "
            f"hero={len(sprites.get('hero_sprite', b''))}B, "
            f"companion={'present' if sprites.get('companion_sprite') else 'none'} [OK]"
        )
    except asyncio.TimeoutError:
        logger.error(
            f"[SystemError][IMP:10][_run_pipeline_bg][AI_PIPELINE][Timeout] "
            f"session_id={session_id}, timeout={BUILD_TIMEOUT_SECONDS}s [FAIL]"
        )
        session["pipeline_error"] = f"AI pipeline timeout after {BUILD_TIMEOUT_SECONDS}s"
        await redis.save_session(session_id, session)
        return
    except Exception as e:
        logger.error(
            f"[SystemError][IMP:10][_run_pipeline_bg][AI_PIPELINE][Error] "
            f"session_id={session_id}, err={e!r} [FAIL]"
        )
        session["pipeline_error"] = f"AI pipeline error: {e}"
        await redis.save_session(session_id, session)
        return
    # END_BLOCK_AI_PIPELINE

    # START_BLOCK_PUBLISH: Загрузка спрайтов и HTML на GitHub Pages
    try:
        hero_sprite_url = await publisher.upload_sprite(
            session_id=session_id,
            filename="hero.png",
            image_bytes=sprites["hero_sprite"],
        )
        companion_sprite_url: Optional[str] = None
        if sprites.get("companion_sprite"):
            companion_sprite_url = await publisher.upload_sprite(
                session_id=session_id,
                filename="companion.png",
                image_bytes=sprites["companion_sprite"],
            )

        session["hero_sprite_url"] = hero_sprite_url
        session["companion_sprite_url"] = companion_sprite_url

        logger.info(
            f"[Flow][IMP:7][_run_pipeline_bg][PUBLISH][BuildHTML] "
            f"session_id={session_id} [START]"
        )
        html = game_builder_module.build(session)

        game_url = await publisher.upload_game(
            session_id=session_id,
            html=html,
        )
    except Exception as e:
        logger.error(
            f"[SystemError][IMP:10][_run_pipeline_bg][PUBLISH][Error] "
            f"session_id={session_id}, err={e!r} [FAIL]"
        )
        session["pipeline_error"] = f"Publish error: {e}"
        await redis.save_session(session_id, session)
        return
    # END_BLOCK_PUBLISH

    # START_BLOCK_SAVE_RESULT: Сохранение game_url в Redis — бот найдёт его при polling
    # BUG_FIX_CONTEXT: Ранее перед сохранением ждали CDN (до 180s). Бот таймаутился за 180s
    # раньше, чем game_url попадал в Redis — ссылка никогда не доходила. CDN wait убран:
    # GitHub Pages обычно готов за 30-60s, к моменту клика пользователя страница уже доступна.
    session["hero_sprite_url"] = hero_sprite_url
    session["companion_sprite_url"] = companion_sprite_url
    session["game_url"] = game_url
    await redis.save_session(session_id, session)

    logger.info(
        f"[BeliefState][IMP:9][_run_pipeline_bg][SAVE_RESULT][Done] "
        f"session_id={session_id}, game_url={game_url!r} [SUCCESS]"
    )
    # END_BLOCK_SAVE_RESULT

# END_FUNCTION__run_pipeline_bg


# START_FUNCTION_build_game
# START_CONTRACT:
# PURPOSE: POST /games/build — принимает session_id, валидирует сессию, запускает пайплайн
#          в BackgroundTasks, немедленно возвращает 202 Accepted.
#          Результат (game_url) доступен позже через GET /sessions/{id} (polling из бота).
# INPUTS:
# - тело запроса с session_id => body: BuildGameRequest
# - FastAPI BackgroundTasks для фоновой задачи => background_tasks: BackgroundTasks
# - объект запроса FastAPI => request: Request
# OUTPUTS:
# - BuildGameResponse — {"status": "accepted"} (202)
# SIDE_EFFECTS: Запускает _run_pipeline_bg как фоновую задачу.
# KEYWORDS: PATTERN(9): FireAndForget; CONCEPT(9): BackgroundTask; TECH(9): FastAPIEndpoint
# COMPLEXITY_SCORE: 4
# END_CONTRACT
@router.post("/build", response_model=BuildGameResponse, status_code=202)
async def build_game(body: BuildGameRequest, background_tasks: BackgroundTasks, request: Request):
    """
    POST /games/build — fire-and-forget запуск генерации игры.

    Шаги:
    1. Загрузить сессию из Redis (404 если нет)
    2. Запустить _run_pipeline_bg как BackgroundTask
    3. Немедленно вернуть {"status": "accepted"} (202)

    Бот получает 202, затем опрашивает GET /sessions/{id} каждые 5 сек.
    Когда pipeline завершится — game_url появится в сессии.
    """
    session_id = body.session_id
    redis = request.app.state.redis
    publisher = request.app.state.github_publisher
    settings = request.app.state.settings

    # START_BLOCK_VALIDATE_SESSION: Валидация сессии перед запуском фона
    session = await redis.get_session(session_id)
    if session is None:
        logger.warning(
            f"[Flow][IMP:8][build_game][VALIDATE_SESSION][NotFound] "
            f"session_id={session_id} [404]"
        )
        raise HTTPException(status_code=404, detail=f"Session {session_id!r} not found")

    logger.info(
        f"[Flow][IMP:7][build_game][VALIDATE_SESSION][OK] "
        f"session_id={session_id}, char_count={session.get('char_count')}, "
        f"scenario={session.get('scenario')!r} [OK]"
    )
    # END_BLOCK_VALIDATE_SESSION

    # START_BLOCK_LAUNCH_BACKGROUND: Запуск фонового пайплайна
    background_tasks.add_task(
        _run_pipeline_bg,
        session_id=session_id,
        session=session,
        redis=redis,
        publisher=publisher,
        settings=settings,
    )

    logger.info(
        f"[BeliefState][IMP:9][build_game][LAUNCH_BACKGROUND][Accepted] "
        f"session_id={session_id} — pipeline запущен в фоне [202]"
    )
    # END_BLOCK_LAUNCH_BACKGROUND

    return BuildGameResponse(status="accepted")

# END_FUNCTION_build_game
