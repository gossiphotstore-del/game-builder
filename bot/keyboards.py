# FILE: bot/keyboards.py
# VERSION: 1.1.0
# START_MODULE_CONTRACT:
# PURPOSE: InlineKeyboard builders для всех шагов FSM-диалога.
# SCOPE: Фабрики клавиатур — welcome, сценарий, кол-во персонажей, пол, подтверждение, регенерация.
# INPUT: Параметры для динамического формирования кнопок (если требуются).
# OUTPUT: InlineKeyboardMarkup объекты для отправки вместе с сообщениями бота.
# KEYWORDS: DOMAIN(8): UI; CONCEPT(8): InlineKeyboard; TECH(9): AiogramTypes
# LINKS: USES_API(9): aiogram.types.InlineKeyboardMarkup
# END_MODULE_CONTRACT
#
# START_CHANGE_SUMMARY:
# LAST_CHANGE: [v1.1.0 - Добавлена welcome_keyboard (CTA-кнопка входа в диалог)]
# PREV_CHANGE_SUMMARY: [v1.0.0 - FS-1: все клавиатуры диалога без оплаты]
# END_CHANGE_SUMMARY
#
# START_MODULE_MAP:
# FUNC [8][CTA-кнопка "Создать игру" для welcome-экрана] => welcome_keyboard
# FUNC [7][Клавиатура выбора сценария] => scenario_keyboard
# FUNC [6][Клавиатура выбора кол-ва персонажей] => char_count_keyboard
# FUNC [6][Клавиатура выбора пола героя] => hero_gender_keyboard
# FUNC [6][Клавиатура выбора пола компаньона] => companion_gender_keyboard
# FUNC [7][Клавиатура подтверждения с кнопкой Создать] => confirm_keyboard
# FUNC [6][Клавиатура после генерации] => post_generation_keyboard
# END_MODULE_MAP

import logging
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

logger = logging.getLogger(__name__)


# START_FUNCTION_welcome_keyboard
# START_CONTRACT:
# PURPOSE: CTA-кнопка "Создать игру" для welcome-экрана. Входная точка в FSM-диалог.
# INPUTS: Нет
# OUTPUTS:
# - InlineKeyboardMarkup - Клавиатура с единственной CTA-кнопкой
# SIDE_EFFECTS: Отсутствуют.
# KEYWORDS: PATTERN(8): CTA; CONCEPT(8): EntryPoint; CONCEPT(7): InlineKeyboard
# COMPLEXITY_SCORE: 2
# END_CONTRACT
def welcome_keyboard() -> InlineKeyboardMarkup:
    """
    Единственная CTA-кнопка на welcome-экране.
    Нажатие запускает on_start_game: создаёт сессию и переводит в диалог выбора сценария.
    callback_data "action:start_game" обрабатывается в handlers/start.py.
    """
    builder = InlineKeyboardBuilder()
    builder.button(text="🎮 Создать игру", callback_data="action:start_game")
    logger.debug(
        "[UI][IMP:3][welcome_keyboard][BUILD][Created] "
        "Welcome CTA-кнопка создана [SUCCESS]"
    )
    return builder.as_markup()
# END_FUNCTION_welcome_keyboard


# START_FUNCTION_scenario_keyboard
# START_CONTRACT:
# PURPOSE: Строит клавиатуру выбора типа сценария игры (3 кнопки).
# INPUTS: Нет
# OUTPUTS:
# - InlineKeyboardMarkup - Клавиатура с 3 кнопками сценариев
# SIDE_EFFECTS: Отсутствуют.
# KEYWORDS: PATTERN(7): Factory; CONCEPT(8): InlineKeyboard
# COMPLEXITY_SCORE: 3
# END_CONTRACT
def scenario_keyboard() -> InlineKeyboardMarkup:
    """
    Создаёт клавиатуру выбора сценария игры.
    Три кнопки: День рождения, Признание в любви, Сюрприз.
    callback_data используется в dialog.py для обработки выбора.
    """
    builder = InlineKeyboardBuilder()
    builder.button(text="🎉 С днём рождения", callback_data="scenario:birthday")
    builder.button(text="❤️ Признание в любви", callback_data="scenario:love")
    builder.button(text="💫 Сюрприз", callback_data="scenario:surprise")
    builder.adjust(1)

    logger.debug(
        "[UI][IMP:3][scenario_keyboard][BUILD][Created] "
        "Клавиатура сценариев создана [SUCCESS]"
    )
    return builder.as_markup()
# END_FUNCTION_scenario_keyboard


# START_FUNCTION_char_count_keyboard
# START_CONTRACT:
# PURPOSE: Строит клавиатуру выбора количества персонажей (1 или 2).
# INPUTS: Нет
# OUTPUTS:
# - InlineKeyboardMarkup - Клавиатура с 2 кнопками выбора кол-ва
# SIDE_EFFECTS: Отсутствуют.
# KEYWORDS: PATTERN(7): Factory; CONCEPT(8): InlineKeyboard
# COMPLEXITY_SCORE: 2
# END_CONTRACT
def char_count_keyboard() -> InlineKeyboardMarkup:
    """
    Создаёт клавиатуру выбора количества персонажей.
    Два варианта: Только герой (1) или Два персонажа (2).
    """
    builder = InlineKeyboardBuilder()
    builder.button(text="🧑 Только герой", callback_data="char_count:1")
    builder.button(text="👥 Два персонажа", callback_data="char_count:2")
    builder.adjust(1)
    return builder.as_markup()
# END_FUNCTION_char_count_keyboard


# START_FUNCTION_hero_gender_keyboard
# START_CONTRACT:
# PURPOSE: Строит клавиатуру выбора пола главного героя.
# INPUTS: Нет
# OUTPUTS:
# - InlineKeyboardMarkup - Клавиатура с 2 кнопками пола
# SIDE_EFFECTS: Отсутствуют.
# KEYWORDS: PATTERN(7): Factory; CONCEPT(8): InlineKeyboard
# COMPLEXITY_SCORE: 2
# END_CONTRACT
def hero_gender_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура выбора пола главного героя.
    callback_data "hero_gender:m" / "hero_gender:f".
    """
    builder = InlineKeyboardBuilder()
    builder.button(text="👨 Мужской", callback_data="hero_gender:m")
    builder.button(text="👩 Женский", callback_data="hero_gender:f")
    builder.adjust(2)
    return builder.as_markup()
# END_FUNCTION_hero_gender_keyboard


# START_FUNCTION_companion_gender_keyboard
# START_CONTRACT:
# PURPOSE: Строит клавиатуру выбора пола компаньона (только при char_count=2).
# INPUTS: Нет
# OUTPUTS:
# - InlineKeyboardMarkup - Клавиатура с 2 кнопками пола
# SIDE_EFFECTS: Отсутствуют.
# KEYWORDS: PATTERN(7): Factory; CONCEPT(8): InlineKeyboard
# COMPLEXITY_SCORE: 2
# END_CONTRACT
def companion_gender_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура выбора пола компаньона.
    callback_data "companion_gender:m" / "companion_gender:f".
    """
    builder = InlineKeyboardBuilder()
    builder.button(text="👨 Мужской", callback_data="companion_gender:m")
    builder.button(text="👩 Женский", callback_data="companion_gender:f")
    builder.adjust(2)
    return builder.as_markup()
# END_FUNCTION_companion_gender_keyboard


# START_FUNCTION_confirm_keyboard
# START_CONTRACT:
# PURPOSE: Строит клавиатуру подтверждения с кнопками "Создать игру" и "Изменить".
# INPUTS: Нет
# OUTPUTS:
# - InlineKeyboardMarkup - Клавиатура с кнопками запуска и редактирования
# SIDE_EFFECTS: Отсутствуют.
# KEYWORDS: PATTERN(7): Factory; CONCEPT(8): ConfirmationDialog
# COMPLEXITY_SCORE: 3
# END_CONTRACT
def confirm_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура подтверждения сводки данных перед запуском генерации.
    Тест-версия: кнопка "🚀 Создать игру" вместо "💳 Оплатить".
    При нажатии сразу вызывает trigger_generation (без оплаты).
    """
    builder = InlineKeyboardBuilder()
    builder.button(text="🚀 Создать игру", callback_data="action:create_game")
    builder.button(text="✏️ Изменить", callback_data="action:edit")
    builder.adjust(1)
    return builder.as_markup()
# END_FUNCTION_confirm_keyboard


# START_FUNCTION_post_generation_keyboard
# START_CONTRACT:
# PURPOSE: Строит клавиатуру после завершения генерации с кнопками запуска и перегенерации.
# INPUTS: Нет
# OUTPUTS:
# - InlineKeyboardMarkup - Клавиатура после получения результатов AI
# SIDE_EFFECTS: Отсутствуют.
# KEYWORDS: PATTERN(7): Factory; CONCEPT(8): PostGenerationUI
# COMPLEXITY_SCORE: 2
# END_CONTRACT
def post_generation_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура после завершения AI-генерации.
    Кнопки: "✅ Запустить игру" (отправляет game_url) и "🔄 Перегенерировать".
    В тест-версии регенерация всегда бесплатна.
    """
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Запустить игру", callback_data="action:launch_game")
    builder.button(text="🔄 Перегенерировать", callback_data="action:regenerate")
    builder.adjust(1)
    return builder.as_markup()
# END_FUNCTION_post_generation_keyboard
