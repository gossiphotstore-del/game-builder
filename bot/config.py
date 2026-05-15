# FILE: bot/config.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT:
# PURPOSE: Pydantic Settings — загрузка конфигурации бота из переменных окружения.
# SCOPE: Единственный источник истины для всех переменных конфигурации бота.
# INPUT: .env файл или переменные окружения системы.
# OUTPUT: Синглтон settings с типизированными полями конфигурации.
# KEYWORDS: DOMAIN(8): Configuration; CONCEPT(9): PydanticSettings; TECH(8): DotEnv
# LINKS: USES_API(9): pydantic_settings
# END_MODULE_CONTRACT
#
# START_CHANGE_SUMMARY:
# LAST_CHANGE: [v1.0.0 - Первичное создание конфигурации бота, FS-1]
# END_CHANGE_SUMMARY
#
# START_MODULE_MAP:
# VAR [10][Глобальный синглтон конфигурации] => settings
# END_MODULE_MAP

from pydantic_settings import BaseSettings
from pydantic import Field


# START_FUNCTION_Settings
# START_CONTRACT:
# PURPOSE: Pydantic BaseSettings — автоматическая загрузка и валидация конфигурации из .env.
# INPUTS: Переменные окружения или .env файл
# OUTPUTS:
# - Settings - Типизированный объект конфигурации
# SIDE_EFFECTS: Читает файл .env из корневой директории при инициализации.
# KEYWORDS: PATTERN(9): ConfigObject; CONCEPT(9): EnvironmentVariables
# COMPLEXITY_SCORE: 2
# END_CONTRACT
class Settings(BaseSettings):
    """
    Класс конфигурации бота на основе pydantic BaseSettings.
    Автоматически загружает значения из переменных окружения или .env файла.
    BOT_TOKEN обязателен — бот не запустится без него.
    BACKEND_URL опционален с дефолтным значением localhost.
    """

    BOT_TOKEN: str = Field(..., description="Telegram Bot API token from @BotFather")
    BACKEND_URL: str = Field(
        default="http://localhost:8000",
        description="Base URL of the FastAPI backend service"
    )

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}
# END_FUNCTION_Settings


settings = Settings()
