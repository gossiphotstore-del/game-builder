# FILE: backend/main.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT:
# PURPOSE: Точка входа FastAPI бэкенда. Инициализирует Redis, регистрирует роутеры,
#          настраивает CORS и lifespan. Запускается через uvicorn.
# SCOPE: FastAPI app creation, lifespan (startup/shutdown), CORS middleware, routers.
# INPUT: Конфигурация из backend/config.py (env-переменные).
# OUTPUT: Работающий HTTP-сервер на порту 8000.
# KEYWORDS: DOMAIN(10): BackendEntry; CONCEPT(9): FastAPILifespan; TECH(9): Uvicorn; PATTERN(8): AppFactory
# LINKS: CALLS_METHOD(10): backend.api.sessions; CALLS_METHOD(10): backend.api.games;
#        CALLS_METHOD(10): backend.services.redis_client.RedisClient
# END_MODULE_CONTRACT
#
# START_RATIONALE:
# Q: Почему Redis инициализируется в lifespan, а не в startup event?
# A: lifespan (contextmanager) — рекомендованный подход в FastAPI >= 0.93.
#    startup/shutdown events устарели. lifespan гарантирует атомарность init/teardown.
# Q: Почему GitHub publisher создаётся здесь?
# A: Singleton — один экземпляр на всё приложение. Создаётся при старте с конфигом.
# END_RATIONALE
#
# START_CHANGE_SUMMARY:
# LAST_CHANGE: [v1.1.0 - Прогрев rembg ONNX модели при старте (устраняет холодный старт +30-90s на первой генерации).]
# PREV_CHANGE_SUMMARY: [v1.0.0 - Создание FastAPI app с lifespan + CORS + routers (FS-4)]
# END_CHANGE_SUMMARY
#
# START_MODULE_MAP:
# FUNC 10[FastAPI lifespan: init/teardown Redis и publisher] => lifespan
# FUNC  9[Создание и конфигурация FastAPI app]               => create_app
# END_MODULE_MAP
#
# START_USE_CASES:
# - lifespan: System(Startup) -> InitializeRedisAndPublisher -> ServicesReady
# - create_app: System -> BuildFastAPIApp -> AppReady
# END_USE_CASES

import asyncio
import io
import logging
import sys
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Настройка логгирования в stdout + файл
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


def _warm_rembg() -> None:
    """
    Предзагружает ONNX-модель rembg (u2net, ~50MB) при старте бэкенда.
    Без прогрева первая генерация тратит 30-90 сек на загрузку модели.
    """
    # BUG_FIX_CONTEXT: rembg lazy-загружает ONNX модель при первом вызове remove().
    # Это добавляло 30-90 сек к первой генерации и вызывало timeout в боте (POLL_TIMEOUT=180s).
    # Прогрев на dummy 10x10 PNG устраняет холодный старт без влияния на результат.
    try:
        from PIL import Image
        from rembg import remove as rembg_remove
        img = Image.new("RGB", (10, 10), color=(255, 255, 255))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        rembg_remove(buf.getvalue())
        logger.info("[BeliefState][IMP:9][_warm_rembg][WARMUP][Done] rembg ONNX model pre-loaded [OK]")
    except Exception as e:
        logger.warning(f"[Flow][IMP:7][_warm_rembg][WARMUP][Skipped] rembg warmup failed (non-fatal): {e!r} [WARN]")


# START_FUNCTION_lifespan
# START_CONTRACT:
# PURPOSE: Async context manager для FastAPI lifespan: инициализирует Redis и GitHubPublisher
#          при старте; закрывает соединения при завершении.
# INPUTS:
# - FastAPI приложение => app: FastAPI
# OUTPUTS: AsyncGenerator (yield)
# SIDE_EFFECTS: Создаёт Redis connection pool (IMP:9); сохраняет в app.state
# KEYWORDS: PATTERN(9): LifespanContextManager; CONCEPT(8): DependencyInjection via app.state
# COMPLEXITY_SCORE: 5
# END_CONTRACT
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Инициализирует сервисы при старте FastAPI:
    - RedisClient с конфигурацией из Settings
    - GitHubPublisher с токеном и репозиторием
    Сохраняет в app.state для передачи в роутеры через request.app.state.

    При shutdown — закрывает Redis соединение.
    """
    # START_BLOCK_STARTUP: Инициализация сервисов
    from backend.config import get_settings
    from backend.services.redis_client import RedisClient
    from backend.services.github_publisher import GitHubPublisher

    settings = get_settings()
    app.state.settings = settings

    logger.info(
        f"[Flow][IMP:9][lifespan][STARTUP][Init] "
        f"Initializing backend services [START]"
    )

    redis_client = RedisClient(redis_url=settings.REDIS_URL)
    app.state.redis = redis_client
    logger.info(
        f"[Flow][IMP:8][lifespan][STARTUP][RedisReady] "
        f"Redis connected: {settings.REDIS_URL} [OK]"
    )

    # START_BLOCK_WARMUP_REMBG: Прогрев rembg ONNX модели в фоне (не блокирует старт)
    asyncio.create_task(asyncio.to_thread(_warm_rembg))
    logger.info("[Flow][IMP:7][lifespan][STARTUP][RembgWarmup] rembg warmup task scheduled [OK]")
    # END_BLOCK_WARMUP_REMBG

    github_publisher = GitHubPublisher(
        github_token=settings.GITHUB_TOKEN,
        github_repo=settings.GITHUB_REPO,
        game_base_url=settings.GAME_BASE_URL,
    )
    app.state.github_publisher = github_publisher

    # START_BLOCK_DEPLOY_STATIC: Публикация статических ассетов (src/, assets/) на gh-pages
    # BUG_FIX_CONTEXT: HTML игры в games/{id}/index.html ссылается на ../../src/ и ../../assets/.
    # Эти файлы должны лежать в корне gh-pages. Загружаем при старте в фоне (не блокирует).
    # BUG_FIX_CONTEXT: Ранее _game_dir указывал на /project/game/ → upload_static_assets искал
    # /project/game/src/ которой не существует. Правильный путь: /project/ (корень проекта),
    # тогда src_dir = /project/src/ ✓ и rel-путь = 'src/constants.js' совпадает с template.html.
    from pathlib import Path
    _game_dir   = Path(__file__).resolve().parents[1]
    _assets_dir = Path(__file__).resolve().parents[1] / "assets"
    asyncio.create_task(github_publisher.upload_static_assets(_game_dir, _assets_dir))
    logger.info("[Flow][IMP:7][lifespan][STARTUP][StaticDeploy] static assets upload task scheduled [OK]")
    # END_BLOCK_DEPLOY_STATIC

    logger.info(
        f"[BeliefState][IMP:9][lifespan][STARTUP][ServicesReady] "
        f"All backend services initialized [OK]"
    )
    # END_BLOCK_STARTUP

    yield  # Приложение работает

    # START_BLOCK_SHUTDOWN: Завершение работы
    await redis_client.close()
    logger.info(
        f"[Flow][IMP:8][lifespan][SHUTDOWN][Cleanup] "
        f"Backend services shut down [OK]"
    )
    # END_BLOCK_SHUTDOWN

# END_FUNCTION_lifespan


# START_FUNCTION_create_app
# START_CONTRACT:
# PURPOSE: Создаёт и конфигурирует FastAPI приложение с CORS, lifespan и роутерами.
# INPUTS: Нет
# OUTPUTS: FastAPI — готовое приложение
# SIDE_EFFECTS: Нет при создании (все side effects в lifespan)
# KEYWORDS: PATTERN(8): AppFactory; CONCEPT(8): CORS
# COMPLEXITY_SCORE: 4
# END_CONTRACT
def create_app() -> FastAPI:
    """
    Фабрика FastAPI приложения. Регистрирует lifespan, CORS middleware и роутеры.
    CORS настроен разрешать все origins (для GitHub Pages).
    """
    from backend.api import sessions as sessions_router
    from backend.api import games as games_router

    app = FastAPI(
        title="Roma Game Backend",
        version="1.0.0",
        description="Backend API для персонализированных игр",
        lifespan=lifespan,
    )

    # START_BLOCK_CORS: CORS для GitHub Pages
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    logger.debug("[Flow][IMP:4][create_app][CORS][Config] CORS configured: allow_origins=* [OK]")
    # END_BLOCK_CORS

    # START_BLOCK_ROUTERS: Регистрация роутеров
    app.include_router(sessions_router.router)
    app.include_router(games_router.router)
    logger.info(
        "[Flow][IMP:7][create_app][ROUTERS][Register] "
        "Routers registered: /sessions, /games [OK]"
    )
    # END_BLOCK_ROUTERS

    return app

# END_FUNCTION_create_app


app = create_app()


if __name__ == "__main__":
    try:
        import uvicorn
        logger.info("[Flow][IMP:9][main][LAUNCH][Start] Starting uvicorn on 0.0.0.0:8000 [OK]")
        uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=False)
    except KeyboardInterrupt:
        logger.info("[Flow][IMP:8][main][LAUNCH][Stop] Server stopped by KeyboardInterrupt [OK]")
