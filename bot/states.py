# FILE: bot/states.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT:
# PURPOSE: FSMContext OrderState — 8 состояний диалога (тест-версия без оплаты).
# SCOPE: Определение состояний машины состояний для FSM-диалога сбора параметров игры.
# INPUT: Используется aiogram FSMContext для управления состояниями пользователя.
# OUTPUT: Класс OrderState с 8 состояниями для регистрации хендлеров.
# KEYWORDS: DOMAIN(9): FSM; CONCEPT(9): StateGraph; TECH(8): AiogramFSM
# LINKS: USES_API(9): aiogram.fsm
# END_MODULE_CONTRACT
#
# START_RATIONALE:
# Q: Почему 8 состояний вместо 10 из полного плана?
# A: FS-1 — тестовая версия БЕЗ оплаты. Исключены состояния PAYING и WAITING_REGEN_PAYMENT.
#    Кнопка "💳 Оплатить" заменена на "🚀 Создать игру" → прямой вызов trigger_generation.
#    WAITING_COMPANION_GENDER и WAITING_COMPANION_PHOTO — условные (только при char_count=2).
# END_RATIONALE
#
# START_CHANGE_SUMMARY:
# LAST_CHANGE: [v1.0.0 - FS-1 тест-версия: 8 состояний без PAYING и WAITING_REGEN_PAYMENT]
# END_CHANGE_SUMMARY
#
# START_MODULE_MAP:
# CLASS [10][FSM состояния диалога заказа игры] => OrderState
# END_MODULE_MAP

from aiogram.fsm.state import State, StatesGroup


# START_FUNCTION_OrderState
# START_CONTRACT:
# PURPOSE: Группа FSM-состояний для диалога сбора параметров игры.
# INPUTS: Нет (декларативное определение состояний)
# OUTPUTS:
# - StatesGroup - Набор именованных состояний для регистрации хендлеров aiogram
# SIDE_EFFECTS: Отсутствуют.
# KEYWORDS: PATTERN(9): StateMachine; CONCEPT(9): DialogFlow
# COMPLEXITY_SCORE: 2
# END_CONTRACT
class OrderState(StatesGroup):
    """
    FSM-состояния диалога создания персонализированной игры (тест-версия без оплаты).

    Линейный поток:
    WAITING_SCENARIO → WAITING_CHAR_COUNT → WAITING_HERO_GENDER
    → [WAITING_COMPANION_GENDER] → WAITING_NAME → WAITING_HERO_PHOTO
    → [WAITING_COMPANION_PHOTO] → CONFIRM

    Состояния в скобках активируются только при char_count=2.
    """

    # Шаг 1: Выбор сценария (3 варианта: birthday / love / surprise)
    WAITING_SCENARIO = State()

    # Шаг 2: Количество персонажей (1 или 2)
    WAITING_CHAR_COUNT = State()

    # Шаг 3: Пол главного героя (m / f)
    WAITING_HERO_GENDER = State()

    # Шаг 4 (условный, только char_count=2): Пол компаньона (m / f)
    WAITING_COMPANION_GENDER = State()

    # Шаг 5: Имя главного героя (1-30 символов, кириллица и/или латиница)
    WAITING_NAME = State()

    # Шаг 6: Фото главного героя (JPEG/PNG, ≥300×300px)
    WAITING_HERO_PHOTO = State()

    # Шаг 7 (условный, только char_count=2): Фото компаньона (JPEG/PNG, ≥300×300px)
    WAITING_COMPANION_PHOTO = State()

    # Шаг 8: Подтверждение и запуск генерации
    CONFIRM = State()
# END_FUNCTION_OrderState
