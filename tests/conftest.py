# FILE: tests/conftest.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT:
# PURPOSE: Конфигурация pytest — хуки, фикстуры, маркировки для всех тестов.
# SCOPE: Общие настройки pytest-asyncio, патч переменных окружения для bot/config.py.
# KEYWORDS: DOMAIN(8): Testing; CONCEPT(8): PytestConfig; TECH(8): PytestAsyncio
# END_MODULE_CONTRACT

import os
import pytest

# Выставляем переменные окружения ДО импорта модулей бота.
# bot/config.py (Pydantic Settings) читает BOT_TOKEN при импорте.
# Без этого pytest упадёт с ValidationError "BOT_TOKEN required".
os.environ.setdefault("BOT_TOKEN", "1234567890:AATestBotTokenForPytestMocking")
os.environ.setdefault("BACKEND_URL", "http://localhost:8000")
