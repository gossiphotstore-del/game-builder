# FILE: backend/services/redis_client.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT:
# PURPOSE: Async Redis wrapper для хранения игровых сессий с фиксированным TTL 72ч (тест-версия).
#          JSON-сериализация/десериализация сессий. Единственная точка доступа к Redis.
# SCOPE: CRUD операции над сессиями: get / save / delete.
# INPUT: session_id (str) + session_data (dict) для сохранения.
# OUTPUT: dict | None для get; None для save/delete.
# KEYWORDS: DOMAIN(9): SessionStorage; CONCEPT(9): AsyncRedis; TECH(8): RedisJSON; PATTERN(7): Repository
# LINKS: USES_API(10): redis.asyncio
# END_MODULE_CONTRACT
#
# START_RATIONALE:
# Q: Почему TTL фиксирован на 259200 сек (72ч) в тест-версии?
# A: В тест-версии убраны оплата и дифференциация TTL. Все сессии живут 72ч.
#    Это упрощает логику и достаточно для тестирования game builder + publisher.
# Q: Почему redis.asyncio, а не sync-клиент?
# A: FastAPI использует async event loop. Sync Redis заблокирует весь сервер.
# END_RATIONALE
#
# START_INVARIANTS:
# - get_session ВСЕГДА возвращает dict или None (никогда не поднимает RedisError наружу).
# - save_session ВСЕГДА применяет TTL=259200 (72ч).
# END_INVARIANTS
#
# START_CHANGE_SUMMARY:
# LAST_CHANGE: [v1.0.0 - Создание Redis wrapper (FS-4, тест-версия без payment_id и TTL-апгрейда)]
# END_CHANGE_SUMMARY
#
# START_MODULE_MAP:
# CLASS 10[Async Redis wrapper с JSON-сериализацией] => RedisClient
# END_MODULE_MAP
#
# START_USE_CASES:
# - get_session: API -> LoadSession -> SessionDictOrNone
# - save_session: API -> PersistSession -> TTLApplied
# - delete_session: API -> RemoveSession -> KeyDeleted
# END_USE_CASES

import json
import logging
from typing import Optional

import redis.asyncio as aioredis

logger = logging.getLogger(__name__)

# Тест-версия: фиксированный TTL 72ч
SESSION_TTL_SECONDS = 259200


# START_FUNCTION_RedisClient
# START_CONTRACT:
# PURPOSE: Инкапсулирует подключение к Redis и операции с сессиями.
# INPUTS: redis_url (str) — URL для подключения
# OUTPUTS: Экземпляр с методами get/save/delete
# SIDE_EFFECTS: Создаёт connection pool при инициализации
# KEYWORDS: PATTERN(9): Repository; CONCEPT(8): ConnectionPool
# COMPLEXITY_SCORE: 5
# END_CONTRACT
class RedisClient:
    """
    Async Redis wrapper для хранения сессий в виде JSON. Использует redis.asyncio
    для неблокирующей работы в FastAPI event loop. TTL фиксирован — 72ч для всех
    сессий (тест-версия без дифференциации по статусу оплаты).
    """

    def __init__(self, redis_url: str):
        """Инициализирует connection pool через from_url."""
        self._client: aioredis.Redis = aioredis.from_url(
            redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
        logger.info(
            f"[Flow][IMP:6][RedisClient][__init__][Init] "
            f"RedisClient инициализирован, url={redis_url} [OK]"
        )

    # START_FUNCTION_get_session
    # START_CONTRACT:
    # PURPOSE: Загружает сессию из Redis по session_id.
    # INPUTS:
    # - идентификатор сессии => session_id: str
    # OUTPUTS:
    # - dict | None — словарь сессии или None если ключ не найден
    # SIDE_EFFECTS: Обращение к Redis (IMP:7)
    # KEYWORDS: PATTERN(7): Repository.Read; CONCEPT(8): JSONDeserialize
    # COMPLEXITY_SCORE: 4
    # END_CONTRACT
    async def get_session(self, session_id: str) -> Optional[dict]:
        """
        Читает JSON-строку из Redis по ключу session_id и десериализует её в dict.
        Возвращает None если ключ не найден или произошла ошибка Redis.
        """
        # START_BLOCK_REDIS_GET: Чтение ключа из Redis
        try:
            raw = await self._client.get(session_id)
            logger.debug(
                f"[IO][IMP:7][get_session][REDIS_GET][Query] "
                f"key={session_id}, found={raw is not None} [{'HIT' if raw else 'MISS'}]"
            )
            if raw is None:
                return None
            session_data = json.loads(raw)
            logger.info(
                f"[BeliefState][IMP:9][get_session][REDIS_GET][ReturnData] "
                f"session_id={session_id}, keys={list(session_data.keys())} [OK]"
            )
            return session_data
        except Exception as e:
            logger.error(
                f"[SystemError][IMP:10][get_session][REDIS_GET][ExceptionEnrichment] "
                f"session_id={session_id}, err={e!r} [FAIL]"
            )
            return None
        # END_BLOCK_REDIS_GET

    # END_FUNCTION_get_session

    # START_FUNCTION_save_session
    # START_CONTRACT:
    # PURPOSE: Сериализует dict в JSON и сохраняет в Redis с TTL 259200 сек (72ч).
    # INPUTS:
    # - идентификатор сессии => session_id: str
    # - словарь данных сессии => data: dict
    # OUTPUTS:
    # - None
    # SIDE_EFFECTS: Запись в Redis (IMP:7); применяет TTL 259200 сек
    # KEYWORDS: PATTERN(7): Repository.Write; CONCEPT(8): JSONSerialize
    # COMPLEXITY_SCORE: 4
    # END_CONTRACT
    async def save_session(self, session_id: str, data: dict) -> None:
        """
        Сериализует data в JSON и сохраняет под ключом session_id с TTL 72ч.
        В тест-версии TTL всегда фиксирован — 259200 секунд.
        """
        # START_BLOCK_REDIS_SET: Сохранение сессии с TTL
        try:
            json_data = json.dumps(data, ensure_ascii=False)
            await self._client.set(session_id, json_data, ex=SESSION_TTL_SECONDS)
            logger.info(
                f"[IO][IMP:7][save_session][REDIS_SET][Write] "
                f"session_id={session_id}, ttl={SESSION_TTL_SECONDS}s [OK]"
            )
        except Exception as e:
            logger.error(
                f"[SystemError][IMP:10][save_session][REDIS_SET][ExceptionEnrichment] "
                f"session_id={session_id}, err={e!r} [FAIL]"
            )
            raise
        # END_BLOCK_REDIS_SET

    # END_FUNCTION_save_session

    # START_FUNCTION_delete_session
    # START_CONTRACT:
    # PURPOSE: Удаляет ключ сессии из Redis.
    # INPUTS:
    # - идентификатор сессии => session_id: str
    # OUTPUTS:
    # - None
    # SIDE_EFFECTS: Удаление ключа из Redis (IMP:7)
    # KEYWORDS: PATTERN(7): Repository.Delete
    # COMPLEXITY_SCORE: 3
    # END_CONTRACT
    async def delete_session(self, session_id: str) -> None:
        """
        Удаляет ключ session_id из Redis. Используется при очистке сессий
        или отмене заказа. Не поднимает исключение если ключ не найден.
        """
        # START_BLOCK_REDIS_DEL: Удаление ключа
        try:
            await self._client.delete(session_id)
            logger.info(
                f"[IO][IMP:7][delete_session][REDIS_DEL][Delete] "
                f"session_id={session_id} [OK]"
            )
        except Exception as e:
            logger.error(
                f"[SystemError][IMP:10][delete_session][REDIS_DEL][ExceptionEnrichment] "
                f"session_id={session_id}, err={e!r} [FAIL]"
            )
        # END_BLOCK_REDIS_DEL

    # END_FUNCTION_delete_session

    async def close(self) -> None:
        """Закрывает соединение с Redis. Вызывается в lifespan shutdown."""
        await self._client.aclose()
        logger.info("[Flow][IMP:6][RedisClient][close][Shutdown] Redis connection closed [OK]")

# END_FUNCTION_RedisClient
