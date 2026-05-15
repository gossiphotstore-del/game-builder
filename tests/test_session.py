# FILE: tests/test_session.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT:
# PURPOSE: Тесты эндпоинтов /sessions: создание, чтение, обновление сессий + проверка Redis TTL.
# SCOPE: POST /sessions, GET /sessions/{id}, PATCH /sessions/{id}, 404, TTL.
# KEYWORDS: DOMAIN(9): Testing; CONCEPT(9): FastAPITestClient; TECH(8): FakeRedis
# LINKS: USES_API(10): backend.api.sessions; USES_API(9): fakeredis.aioredis
# END_MODULE_CONTRACT
#
# START_RATIONALE:
# Q: Почему используется fakeredis.aioredis, а не реальный Redis?
# A: fakeredis — полная in-memory эмуляция Redis с поддержкой asyncio. Нет зависимости
#    от внешнего сервера. Идентичное поведение TTL, GET/SET/DEL.
# Q: Почему override app.state.redis вместо dependency injection?
# A: RedisClient создаётся в lifespan. Подменить app.state напрямую в тесте проще,
#    чем переопределять lifespan.
# END_RATIONALE
#
# START_CHANGE_SUMMARY:
# LAST_CHANGE: [v1.0.0 - Создание тестов sessions (FS-4)]
# END_CHANGE_SUMMARY

import logging
import os
import uuid

import pytest
import pytest_asyncio

# Устанавливаем env-переменные ДО импорта модулей backend
os.environ.setdefault("REDIS_URL", "redis://localhost:6379")
os.environ.setdefault("REPLICATE_API_TOKEN", "test_token")
os.environ.setdefault("GITHUB_TOKEN", "test_github_token")
os.environ.setdefault("GITHUB_REPO", "testuser/testrepo")
os.environ.setdefault("GAME_BASE_URL", "https://testuser.github.io/testrepo")
os.environ.setdefault("BOT_TOKEN", "1234567890:AATestBotToken")

logger = logging.getLogger(__name__)

# === Фикстуры ===

@pytest_asyncio.fixture
async def fake_redis():
    """
    Создаёт изолированный экземпляр fakeredis для каждого теста.
    Полностью эмулирует redis.asyncio с поддержкой TTL.
    """
    import fakeredis.aioredis as fakeredis_aio
    redis = fakeredis_aio.FakeRedis(decode_responses=True)
    logger.info("[Flow][IMP:8][fake_redis][FIXTURE][Init] FakeRedis создан [OK]")
    yield redis
    await redis.aclose()
    logger.info("[Flow][IMP:7][fake_redis][FIXTURE][Teardown] FakeRedis закрыт [OK]")


@pytest_asyncio.fixture
async def redis_client(fake_redis):
    """
    RedisClient, обёрнутый вокруг fakeredis.
    Патчим внутренний _client для использования fake_redis.
    """
    from backend.services.redis_client import RedisClient
    client = RedisClient.__new__(RedisClient)
    client._client = fake_redis
    logger.info("[Flow][IMP:8][redis_client][FIXTURE][Init] RedisClient с fake backend [OK]")
    return client


@pytest_asyncio.fixture
async def test_app(redis_client):
    """
    FastAPI TestClient с подменённым Redis.
    Создаёт app без lifespan (чтобы не подключаться к реальному Redis).
    """
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    from backend.api import sessions as sessions_router
    from backend.config import get_settings

    # Создаём минимальный app без lifespan
    app = FastAPI(title="Test App")
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
    app.include_router(sessions_router.router)

    # Подключаем fake redis и settings в app.state
    app.state.redis = redis_client
    app.state.settings = get_settings()

    return app


@pytest_asyncio.fixture
async def client(test_app):
    """
    Async HTTP test client для FastAPI app.
    Используем httpx.AsyncClient напрямую.
    """
    import httpx
    from httpx import AsyncClient, ASGITransport
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as c:
        logger.info("[Flow][IMP:7][client][FIXTURE][Init] AsyncClient создан [OK]")
        yield c


# === Тесты ===

# START_FUNCTION_test_create_session_returns_uuid
# START_CONTRACT:
# PURPOSE: Проверяет, что POST /sessions возвращает session_id в формате UUID4.
# COMPLEXITY_SCORE: 3
# END_CONTRACT
@pytest.mark.asyncio
async def test_create_session_returns_uuid(client):
    """
    POST /sessions с user_id должен вернуть HTTP 201 и session_id в формате UUID4.
    UUID4 имеет формат xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx.
    """
    logger.info("[Flow][IMP:7][test_create_session_returns_uuid][RUN][Start] [TEST]")

    response = await client.post("/sessions", json={"user_id": 12345})

    assert response.status_code == 201, f"Expected 201, got {response.status_code}"
    data = response.json()
    assert "session_id" in data, f"No session_id in response: {data}"

    session_id = data["session_id"]
    # Проверяем формат UUID
    parsed = uuid.UUID(session_id)
    assert parsed.version == 4, f"Expected UUID4, got version={parsed.version}"

    logger.info(
        f"[BeliefState][IMP:9][test_create_session_returns_uuid][RESULT][Pass] "
        f"session_id={session_id!r} is valid UUID4 [PASS]"
    )
# END_FUNCTION_test_create_session_returns_uuid


# START_FUNCTION_test_get_session_returns_data
# START_CONTRACT:
# PURPOSE: Проверяет, что GET /sessions/{id} возвращает данные созданной сессии.
# COMPLEXITY_SCORE: 3
# END_CONTRACT
@pytest.mark.asyncio
async def test_get_session_returns_data(client):
    """
    После POST /sessions, GET /sessions/{session_id} должен вернуть HTTP 200
    со словарём, содержащим session_id и user_id.
    """
    logger.info("[Flow][IMP:7][test_get_session_returns_data][RUN][Start] [TEST]")

    # Создаём сессию
    create_resp = await client.post("/sessions", json={"user_id": 42})
    assert create_resp.status_code == 201
    session_id = create_resp.json()["session_id"]

    # Получаем сессию
    get_resp = await client.get(f"/sessions/{session_id}")

    assert get_resp.status_code == 200, f"Expected 200, got {get_resp.status_code}"
    data = get_resp.json()

    assert data["session_id"] == session_id
    assert data["user_id"] == 42

    logger.info(
        f"[BeliefState][IMP:9][test_get_session_returns_data][RESULT][Pass] "
        f"session_id={session_id!r}, user_id={data['user_id']} [PASS]"
    )
# END_FUNCTION_test_get_session_returns_data


# START_FUNCTION_test_get_nonexistent_session_returns_404
# START_CONTRACT:
# PURPOSE: Проверяет, что GET несуществующей сессии возвращает 404.
# COMPLEXITY_SCORE: 2
# END_CONTRACT
@pytest.mark.asyncio
async def test_get_nonexistent_session_returns_404(client):
    """
    GET /sessions/{несуществующий_id} должен вернуть HTTP 404.
    """
    logger.info("[Flow][IMP:7][test_get_nonexistent_session_returns_404][RUN][Start] [TEST]")

    fake_id = str(uuid.uuid4())
    response = await client.get(f"/sessions/{fake_id}")

    assert response.status_code == 404, f"Expected 404, got {response.status_code}"

    logger.info(
        f"[BeliefState][IMP:9][test_get_nonexistent_session_returns_404][RESULT][Pass] "
        f"id={fake_id!r} → 404 as expected [PASS]"
    )
# END_FUNCTION_test_get_nonexistent_session_returns_404


# START_FUNCTION_test_patch_session_updates_only_given_fields
# START_CONTRACT:
# PURPOSE: Проверяет, что PATCH обновляет только переданные поля, не трогая остальные.
# COMPLEXITY_SCORE: 4
# END_CONTRACT
@pytest.mark.asyncio
async def test_patch_session_updates_only_given_fields(client):
    """
    PATCH /sessions/{id} должен обновить только переданные поля.
    Поля, не переданные в теле, должны остаться неизменными.
    """
    logger.info("[Flow][IMP:7][test_patch_session_updates_only_given_fields][RUN][Start] [TEST]")

    # Создаём сессию
    create_resp = await client.post("/sessions", json={"user_id": 999})
    assert create_resp.status_code == 201
    session_id = create_resp.json()["session_id"]

    # Патчим: устанавливаем scenario и name
    patch_resp = await client.patch(
        f"/sessions/{session_id}",
        json={"scenario": "birthday", "name": "Александр"},
    )
    assert patch_resp.status_code == 200, f"Expected 200, got {patch_resp.status_code}"
    patch_data = patch_resp.json()
    assert patch_data["ok"] is True, f"Expected ok=true, got {patch_data}"

    # Проверяем обновление
    get_resp = await client.get(f"/sessions/{session_id}")
    assert get_resp.status_code == 200
    session = get_resp.json()

    assert session["scenario"] == "birthday", f"scenario не обновлён: {session['scenario']!r}"
    assert session["name"] == "Александр", f"name не обновлён: {session['name']!r}"
    # user_id не должен измениться
    assert session["user_id"] == 999, f"user_id изменился: {session['user_id']}"
    # hero_gender остался None (не передавали)
    assert session["hero_gender"] is None, f"hero_gender должен быть None: {session['hero_gender']!r}"

    logger.info(
        f"[BeliefState][IMP:9][test_patch_session_updates_only_given_fields][RESULT][Pass] "
        f"scenario={session['scenario']!r}, name={session['name']!r}, "
        f"user_id={session['user_id']} (unchanged) [PASS]"
    )
# END_FUNCTION_test_patch_session_updates_only_given_fields


# START_FUNCTION_test_session_redis_ttl
# START_CONTRACT:
# PURPOSE: Проверяет, что TTL сессии после создания ≈ 259200 сек (±10).
# COMPLEXITY_SCORE: 4
# END_CONTRACT
@pytest.mark.asyncio
async def test_session_redis_ttl(client, fake_redis):
    """
    После POST /sessions сессия должна иметь TTL ≈ 259200 сек (72ч).
    Допустимое отклонение ±10 сек.
    """
    logger.info("[Flow][IMP:7][test_session_redis_ttl][RUN][Start] [TEST]")

    create_resp = await client.post("/sessions", json={"user_id": 77})
    assert create_resp.status_code == 201
    session_id = create_resp.json()["session_id"]

    # Проверяем TTL напрямую в Redis
    ttl = await fake_redis.ttl(session_id)

    logger.info(
        f"[BeliefState][IMP:9][test_session_redis_ttl][CHECK_TTL][Value] "
        f"session_id={session_id!r}, ttl={ttl}s (expected≈259200) [CHECK]"
    )

    assert ttl > 0, f"TTL должен быть > 0, получен {ttl}"
    assert abs(ttl - 259200) <= 10, (
        f"TTL={ttl} далеко от 259200. Ожидается ±10 сек."
    )

    logger.info(
        f"[BeliefState][IMP:9][test_session_redis_ttl][RESULT][Pass] "
        f"ttl={ttl}s ≈ 259200 [PASS]"
    )
# END_FUNCTION_test_session_redis_ttl


# START_FUNCTION_test_patch_nonexistent_session_returns_404
# START_CONTRACT:
# PURPOSE: Проверяет, что PATCH несуществующей сессии возвращает 404.
# COMPLEXITY_SCORE: 2
# END_CONTRACT
@pytest.mark.asyncio
async def test_patch_nonexistent_session_returns_404(client):
    """
    PATCH /sessions/{несуществующий_id} должен вернуть HTTP 404.
    """
    logger.info("[Flow][IMP:7][test_patch_nonexistent_session_returns_404][RUN][Start] [TEST]")

    fake_id = str(uuid.uuid4())
    response = await client.patch(f"/sessions/{fake_id}", json={"name": "Test"})

    assert response.status_code == 404, f"Expected 404, got {response.status_code}"

    logger.info(
        f"[BeliefState][IMP:9][test_patch_nonexistent_session_returns_404][RESULT][Pass] "
        f"id={fake_id!r} → 404 [PASS]"
    )
# END_FUNCTION_test_patch_nonexistent_session_returns_404
