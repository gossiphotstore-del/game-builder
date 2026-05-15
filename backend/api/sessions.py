# FILE: backend/api/sessions.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT:
# PURPOSE: FastAPI роутер для управления игровыми сессиями.
#          POST /sessions — создание, GET /sessions/{id} — чтение, PATCH /sessions/{id} — обновление.
# SCOPE: CRUD сессий через Redis. Без оплаты (тест-версия).
# INPUT: HTTP запросы с JSON body.
# OUTPUT: JSON ответы с данными сессии или статусом.
# KEYWORDS: DOMAIN(9): SessionManagement; CONCEPT(9): RESTful; TECH(8): FastAPIRouter
# LINKS: CALLS_METHOD(10): RedisClient.get_session; CALLS_METHOD(10): RedisClient.save_session
# END_MODULE_CONTRACT
#
# START_RATIONALE:
# Q: Почему PATCH принимает dict вместо строгой Pydantic модели?
# A: Сессия обновляется частично (любые поля). Strict model потребует перечисления
#    Optional-поля — избыточно. Dict + merge в Redis достаточно для тест-версии.
# END_RATIONALE
#
# START_CHANGE_SUMMARY:
# LAST_CHANGE: [v1.0.0 - Создание sessions router (FS-4, тест-версия без payment_id)]
# END_CHANGE_SUMMARY
#
# START_MODULE_MAP:
# FUNC 9[POST /sessions — создание новой сессии с UUID] => create_session
# FUNC 8[GET /sessions/{id} — получение сессии по ID]  => get_session
# FUNC 8[PATCH /sessions/{id} — обновление полей]      => update_session
# END_MODULE_MAP
#
# START_USE_CASES:
# - create_session: BotClient -> CreateSession -> SessionIDReturned
# - get_session: BotClient -> LoadSession -> SessionDataReturned
# - update_session: BotClient -> UpdateSessionFields -> OkReturned
# END_USE_CASES

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sessions", tags=["sessions"])


# --- Request/Response models ---

class CreateSessionRequest(BaseModel):
    user_id: int


class CreateSessionResponse(BaseModel):
    session_id: str


class UpdateSessionResponse(BaseModel):
    ok: bool


# START_FUNCTION_create_session
# START_CONTRACT:
# PURPOSE: Создаёт новую сессию с UUID4, сохраняет в Redis с TTL 72ч.
# INPUTS:
# - тело запроса с user_id => body: CreateSessionRequest
# - объект запроса FastAPI => request: Request
# OUTPUTS:
# - CreateSessionResponse — {"session_id": "uuid4-string"}
# SIDE_EFFECTS: Запись в Redis (TTL 259200)
# KEYWORDS: PATTERN(8): Factory; CONCEPT(9): UUID; TECH(8): FastAPI
# COMPLEXITY_SCORE: 5
# END_CONTRACT
@router.post("", response_model=CreateSessionResponse, status_code=201)
async def create_session(body: CreateSessionRequest, request: Request):
    """
    Создаёт новую игровую сессию с уникальным UUID4.
    Инициализирует все поля сессии дефолтными значениями и сохраняет в Redis.
    Возвращает session_id для дальнейшего использования в боте.
    """
    redis = request.app.state.redis

    # START_BLOCK_BUILD_SESSION: Формирование структуры новой сессии
    session_id = str(uuid.uuid4())
    session_data = {
        "session_id": session_id,
        "user_id": body.user_id,
        "scenario": None,
        "char_count": None,
        "hero_gender": None,
        "companion_gender": None,
        "name": None,
        "hero_photo_file_id": None,
        "companion_photo_file_id": None,
        "hero_sprite_url": None,
        "companion_sprite_url": None,
        "game_url": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    logger.info(
        f"[Flow][IMP:7][create_session][BUILD_SESSION][Create] "
        f"session_id={session_id}, user_id={body.user_id} [START]"
    )
    # END_BLOCK_BUILD_SESSION

    # START_BLOCK_SAVE_TO_REDIS: Сохранение в Redis
    await redis.save_session(session_id, session_data)
    logger.info(
        f"[BeliefState][IMP:9][create_session][SAVE_TO_REDIS][Result] "
        f"session_id={session_id} saved to Redis [OK]"
    )
    # END_BLOCK_SAVE_TO_REDIS

    return CreateSessionResponse(session_id=session_id)

# END_FUNCTION_create_session


# START_FUNCTION_get_session
# START_CONTRACT:
# PURPOSE: Возвращает данные сессии по session_id или 404 если не найдена.
# INPUTS:
# - идентификатор сессии => session_id: str (path param)
# - объект запроса FastAPI => request: Request
# OUTPUTS:
# - dict — данные сессии
# SIDE_EFFECTS: Чтение из Redis (IMP:7)
# KEYWORDS: PATTERN(7): Repository.Read; CONCEPT(8): HTTPException
# COMPLEXITY_SCORE: 4
# END_CONTRACT
@router.get("/{session_id}")
async def get_session(session_id: str, request: Request):
    """
    Загружает сессию из Redis по session_id.
    Если ключ не найден (сессия истекла или не существует) — возвращает HTTP 404.
    """
    redis = request.app.state.redis

    session = await redis.get_session(session_id)
    if session is None:
        logger.warning(
            f"[Flow][IMP:8][get_session][LOAD][NotFound] "
            f"session_id={session_id} not found in Redis [404]"
        )
        raise HTTPException(status_code=404, detail=f"Session {session_id!r} not found")

    logger.info(
        f"[BeliefState][IMP:9][get_session][LOAD][Result] "
        f"session_id={session_id}, user_id={session.get('user_id')} [OK]"
    )
    return session

# END_FUNCTION_get_session


# START_FUNCTION_update_session
# START_CONTRACT:
# PURPOSE: Обновляет произвольные поля сессии (partial update, merge-семантика).
# INPUTS:
# - идентификатор сессии => session_id: str (path param)
# - словарь с обновляемыми полями => body: dict
# - объект запроса FastAPI => request: Request
# OUTPUTS:
# - UpdateSessionResponse — {"ok": true}
# SIDE_EFFECTS: Чтение + запись в Redis (IMP:7)
# KEYWORDS: PATTERN(8): PartialUpdate; CONCEPT(8): MergeSemantics
# COMPLEXITY_SCORE: 5
# END_CONTRACT
@router.patch("/{session_id}", response_model=UpdateSessionResponse)
async def update_session(session_id: str, body: dict[str, Any], request: Request):
    """
    Частичное обновление сессии. Загружает существующую сессию из Redis,
    применяет переданные поля через dict.update() и сохраняет обратно.
    Только переданные поля изменяются — остальные не трогаются.
    """
    redis = request.app.state.redis

    # START_BLOCK_LOAD_SESSION: Загрузка текущей сессии
    session = await redis.get_session(session_id)
    if session is None:
        logger.warning(
            f"[Flow][IMP:8][update_session][LOAD_SESSION][NotFound] "
            f"session_id={session_id} [404]"
        )
        raise HTTPException(status_code=404, detail=f"Session {session_id!r} not found")
    # END_BLOCK_LOAD_SESSION

    # START_BLOCK_APPLY_UPDATE: Применение обновлений
    updated_fields = list(body.keys())
    session.update(body)
    logger.info(
        f"[Flow][IMP:7][update_session][APPLY_UPDATE][Merge] "
        f"session_id={session_id}, updated_fields={updated_fields} [OK]"
    )
    # END_BLOCK_APPLY_UPDATE

    # START_BLOCK_SAVE_SESSION: Сохранение обновлённой сессии
    await redis.save_session(session_id, session)
    logger.info(
        f"[BeliefState][IMP:9][update_session][SAVE_SESSION][Result] "
        f"session_id={session_id} updated [OK]"
    )
    # END_BLOCK_SAVE_SESSION

    return UpdateSessionResponse(ok=True)

# END_FUNCTION_update_session
