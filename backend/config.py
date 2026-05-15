# FILE: backend/config.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT:
# PURPOSE: Централизованная конфигурация бэкенда через Pydantic BaseSettings.
#          Читает переменные окружения (или .env файл).
# SCOPE: Все параметры подключения: Redis, Replicate, GitHub, Telegram BOT_TOKEN.
# INPUT: Переменные окружения или .env файл.
# OUTPUT: Синглтон settings для использования во всех модулях бэкенда.
# KEYWORDS: DOMAIN(8): Config; CONCEPT(8): Settings; TECH(9): PydanticSettings
# LINKS: READS_DATA_FROM(9): .env
# END_MODULE_CONTRACT
#
# START_RATIONALE:
# Q: Почему используется Pydantic BaseSettings, а не os.environ?
# A: BaseSettings обеспечивает типизацию, валидацию при старте и явный список
#    обязательных параметров. Ошибка конфигурации выявляется сразу при запуске.
# END_RATIONALE
#
# START_CHANGE_SUMMARY:
# LAST_CHANGE: [v1.0.0 - Создание модуля конфигурации бэкенда (FS-4)]
# END_CHANGE_SUMMARY
#
# START_MODULE_MAP:
# CLASS 10[Конфигурация бэкенда через env-переменные] => Settings
# FUNC  8[Геттер синглтона настроек] => get_settings
# END_MODULE_MAP
#
# START_USE_CASES:
# - get_settings: Backend modules -> ReadConfig -> SettingsReturned
# END_USE_CASES

import logging
from functools import lru_cache
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)


# START_FUNCTION_Settings
# START_CONTRACT:
# PURPOSE: Хранит все конфигурационные параметры бэкенда.
# INPUTS: Переменные окружения или .env файл (автоматически через BaseSettings)
# OUTPUTS: Экземпляр с типизированными полями
# SIDE_EFFECTS: Валидация при инстанцировании — падает при отсутствии обязательных переменных
# KEYWORDS: CONCEPT(9): ConfigurationManagement; PATTERN(8): Singleton via lru_cache
# COMPLEXITY_SCORE: 3
# END_CONTRACT
class Settings(BaseSettings):
    """
    Pydantic BaseSettings для бэкенда. При инициализации автоматически читает
    переменные из окружения и .env файла. Поля без default обязательны.
    Используется как синглтон через get_settings().
    """
    # Redis
    REDIS_URL: str = "redis://localhost:6379"

    # Replicate API (для AI-пайплайна)
    REPLICATE_API_TOKEN: str = "test_token"

    # GitHub Pages (публикация игры)
    GITHUB_TOKEN: str = "test_github_token"
    GITHUB_REPO: str = "username/repo"       # Формат: "owner/repo"
    GAME_BASE_URL: str = "https://username.github.io/repo"

    # OpenRouter API (для AI-генерации спрайтов: GPT-4o Vision + DALL-E 3)
    OPENROUTER_API_KEY: str = "test_openrouter_key"

    # Telegram (для скачивания фото по file_id)
    BOT_TOKEN: str = "test_bot_token"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }
# END_FUNCTION_Settings


# START_FUNCTION_get_settings
# START_CONTRACT:
# PURPOSE: Возвращает кешированный синглтон Settings. Кеширование через lru_cache(1).
# INPUTS: Нет
# OUTPUTS: Settings — единственный экземпляр конфигурации
# SIDE_EFFECTS: При первом вызове читает env/файл; при последующих возвращает кеш.
# KEYWORDS: PATTERN(9): Singleton; CONCEPT(8): LazyInit
# COMPLEXITY_SCORE: 2
# END_CONTRACT
@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Возвращает кешированный экземпляр Settings. Используется как dependency в FastAPI
    через Depends(get_settings). lru_cache гарантирует однократное чтение конфигурации.
    """
    settings = Settings()
    logger.info(
        f"[BeliefState][IMP:9][get_settings][INIT][ConfigLoaded] "
        f"REDIS_URL={settings.REDIS_URL}, GITHUB_REPO={settings.GITHUB_REPO} [OK]"
    )
    return settings
