$START_DEV_PLAN

**PURPOSE:** Реализация платформы v2.1 — Telegram-бот собирает параметры (сценарий, кол-во персонажей, пол, имя, фото), берёт оплату, генерирует AI-спрайты через Replicate InstantID и выдаёт уникальный URL персонализированной Phaser.js игры на 72ч.

**БАЗА:** Существующая Phaser.js игра (src/ + index.html) переиспользуется как шаблон — хардкод заменяется плейсхолдерами и window.GAME_CONFIG.

---

## 0. Структура директорий

```
/project-root
├── bot/
│   ├── main.py                  # Bot + Dispatcher + polling
│   ├── config.py                # Pydantic Settings: токены, ключи, BACKEND_URL
│   ├── states.py                # FSMContext: OrderState (10 состояний)
│   ├── keyboards.py             # InlineKeyboard builders
│   ├── handlers/
│   │   ├── start.py             # /start, /new, /help
│   │   ├── dialog.py            # FSM: scenario→char_count→gender→name→photo
│   │   ├── payment.py           # Invoice → PreCheckout → SuccessfulPayment
│   │   └── generation.py        # Получение результата AI, превью спрайтов, кнопки запуска/реген
│   └── services/
│       └── backend_client.py    # aiohttp-клиент к FastAPI
│
├── backend/
│   ├── main.py                  # FastAPI + lifespan + routers
│   ├── config.py                # Pydantic Settings: Redis, Replicate, GitHub
│   ├── api/
│   │   ├── sessions.py          # POST/GET/PATCH /sessions
│   │   └── games.py             # POST /games/build
│   ├── services/
│   │   ├── redis_client.py      # Async Redis wrapper, TTL 24ч (до оплаты) / 72ч (после)
│   │   ├── game_builder.py      # Подстановка 6 плейсхолдеров + инжект texts.json
│   │   ├── github_publisher.py  # Публикация на GitHub Pages
│   │   └── refund_service.py    # ЮKassa Refund API: автовозврат при timeout/сбое AI
│   └── ai/
│       ├── pipeline.py          # Оркестратор: color → generate → postprocess
│       ├── replicate_client.py  # Replicate InstantID, gender-specific промпты
│       ├── color_extractor.py   # K-Means dominant color
│       └── postprocessor.py     # rembg + Pillow resize
│
├── game/
│   ├── template.html            # index.html → плейсхолдеры, window.GAME_CONFIG
│   └── src/
│       ├── main.js              # Читает GAME_CONFIG, передаёт в сцены
│       ├── data/
│       │   └── texts.js         # Гендерно-адаптированный JSON: рулетка, игровые тексты
│       └── scenes/
│           ├── BootScene.js     # Прелоадер ассетов, «Загружаем игру для {name}...»
│           ├── StartScene.js    # Приветствие + кнопка СТАРТ
│           ├── GameScene.js     # Основной геймплей
│           ├── RouletteScene.js # Рулетка 6 фраз, гендерная адаптация
│           ├── FinalScene.js    # Финал по сценарию + char_count
│           └── EndScene.js      # Экран «Поделиться» / «Сыграть снова»
│
├── tests/
│   ├── test_dialog.py           # FSM: 10 состояний, conditional flow
│   ├── test_payment.py          # Invoice + SuccessfulPayment + regen Invoice
│   ├── test_generation.py       # Превью спрайтов, кнопки запуска/реген
│   ├── test_refund.py           # ЮKassa refund на timeout/error
│   ├── test_color_extractor.py
│   ├── test_replicate.py        # Mock Replicate, проверка gender-промптов
│   ├── test_postprocessor.py
│   ├── test_game_builder.py     # Проверка всех 6 плейсхолдеров
│   └── test_session.py          # Redis TTL + CRUD
│
├── docker-compose.yml
├── Dockerfile.bot
├── Dockerfile.backend
├── requirements.txt
└── .env.example
```

---

## 1. Draft Code Graph

```xml
<DraftCodeGraph>

  <!-- ════════════════ BOT LAYER ════════════════ -->

  <bot_main_py FILE="bot/main.py" TYPE="CLI_MODULE">
    <annotation>Точка входа. Bot + Dispatcher + Redis storage + регистрация роутеров. Asyncio long-polling.</annotation>
    <CrossLinks>
      <Link TARGET="bot_handlers_start_py" TYPE="CALLS_METHOD" />
      <Link TARGET="bot_handlers_dialog_py" TYPE="CALLS_METHOD" />
      <Link TARGET="bot_handlers_payment_py" TYPE="CALLS_METHOD" />
    </CrossLinks>
  </bot_main_py>

  <bot_config_py FILE="bot/config.py" TYPE="DATA_PROCESSING_MODULE">
    <annotation>Pydantic Settings: BOT_TOKEN, BACKEND_URL, PAYMENT_PROVIDER_TOKEN, YOOKASSA_SHOP_ID, YOOKASSA_SECRET.</annotation>
  </bot_config_py>

  <bot_states_py FILE="bot/states.py" TYPE="DATA_PROCESSING_MODULE">
    <annotation>FSMContext OrderState (10 состояний): WAITING_SCENARIO → WAITING_CHAR_COUNT → WAITING_HERO_GENDER → [WAITING_COMPANION_GENDER] → WAITING_NAME → WAITING_HERO_PHOTO → [WAITING_COMPANION_PHOTO] → CONFIRM → PAYING → [WAITING_REGEN_PAYMENT]. Состояния в скобках — условные. WAITING_REGEN_PAYMENT: активируется при regen_count ≥ 1, выставляет новый Invoice 1000 руб.</annotation>
  </bot_states_py>

  <bot_keyboards_py FILE="bot/keyboards.py" TYPE="UI_MODULE">
    <annotation>InlineKeyboard builders: сценарий (3 кнопки), char_count (2), пол (2), подтверждение, оплата, перегенерация.</annotation>
  </bot_keyboards_py>

  <bot_handlers_start_py FILE="bot/handlers/start.py" TYPE="CLI_MODULE">
    <annotation>/start — создаёт сессию, показывает кнопки выбора сценария. /new — сброс FSM + сессии. /help — справка.</annotation>
    <CrossLinks>
      <Link TARGET="bot_services_backend_client_py" TYPE="CALLS_METHOD" />
    </CrossLinks>
  </bot_handlers_start_py>

  <bot_handlers_dialog_py FILE="bot/handlers/dialog.py" TYPE="CLI_MODULE">
    <annotation>FSM-обработчики полного диалога v2.1: шаги 1-5б. Conditional branching по char_count: если 1 — пропускает companion_gender и WAITING_COMPANION_PHOTO. Валидация имени (1-30, кириллица/латиница) и фото (JPEG/PNG ≥300px).</annotation>
    <CrossLinks>
      <Link TARGET="bot_services_backend_client_py" TYPE="CALLS_METHOD" />
      <Link TARGET="bot_keyboards_py" TYPE="CALLS_METHOD" />
    </CrossLinks>
  </bot_handlers_dialog_py>

  <bot_handlers_payment_py FILE="bot/handlers/payment.py" TYPE="CLI_MODULE">
    <annotation>Invoice 1000 руб → PreCheckoutQuery → SuccessfulPayment → trigger_generation. При WAITING_REGEN_PAYMENT выставляет повторный Invoice и ждёт SuccessfulPayment. Уведомления о прогрессе и ошибках.</annotation>
    <CrossLinks>
      <Link TARGET="bot_services_backend_client_py" TYPE="CALLS_METHOD" />
    </CrossLinks>
  </bot_handlers_payment_py>

  <bot_handlers_generation_py FILE="bot/handlers/generation.py" TYPE="CLI_MODULE">
    <annotation>Получает callback от backend после завершения AI-генерации. Скачивает PNG-спрайты с GitHub Pages, отправляет превью пользователю: «Вот ваши герои!». Кнопки: [✅ Запустить игру] → отправляет game_url; [🔄 Перегенерировать] → если regen_count=0 повторяет pipeline бесплатно, если ≥1 → переводит в WAITING_REGEN_PAYMENT.</annotation>
    <CrossLinks>
      <Link TARGET="bot_services_backend_client_py" TYPE="CALLS_METHOD" />
      <Link TARGET="bot_handlers_payment_py" TYPE="CALLS_METHOD" />
    </CrossLinks>
  </bot_handlers_generation_py>

  <bot_services_backend_client_py FILE="bot/services/backend_client.py" TYPE="DATA_PROCESSING_MODULE">
    <annotation>Async HTTP (aiohttp): create_session, patch_session (scenario/char_count/hero_gender/companion_gender/name/photos/paid), trigger_generation, get_game_url.</annotation>
    <CrossLinks>
      <Link TARGET="backend_api_sessions_py" TYPE="CALLS_METHOD" />
      <Link TARGET="backend_api_games_py" TYPE="CALLS_METHOD" />
    </CrossLinks>
  </bot_services_backend_client_py>

  <!-- ════════════════ BACKEND LAYER ════════════════ -->

  <backend_main_py FILE="backend/main.py" TYPE="CLI_MODULE">
    <annotation>FastAPI app. lifespan: Redis init. Роутеры: /sessions, /games. CORS для GitHub Pages.</annotation>
    <CrossLinks>
      <Link TARGET="backend_api_sessions_py" TYPE="CALLS_METHOD" />
      <Link TARGET="backend_api_games_py" TYPE="CALLS_METHOD" />
    </CrossLinks>
  </backend_main_py>

  <backend_config_py FILE="backend/config.py" TYPE="DATA_PROCESSING_MODULE">
    <annotation>Pydantic Settings: REDIS_URL, REPLICATE_API_TOKEN, GITHUB_TOKEN, GITHUB_REPO, GAME_BASE_URL.</annotation>
  </backend_config_py>

  <backend_api_sessions_py FILE="backend/api/sessions.py" TYPE="DATA_PROCESSING_MODULE">
    <annotation>POST /sessions (UUID), GET /sessions/{id}, PATCH /sessions/{id}. Модель сессии содержит: scenario, char_count, hero_gender, companion_gender, name, hero_photo_url, companion_photo_url, paid, sprites, regen_count.</annotation>
    <CrossLinks>
      <Link TARGET="backend_services_redis_client_py" TYPE="CALLS_METHOD" />
    </CrossLinks>
  </backend_api_sessions_py>

  <backend_api_games_py FILE="backend/api/games.py" TYPE="DATA_PROCESSING_MODULE">
    <annotation>POST /games/build: session_id → AI pipeline → game_builder → github_publisher → {game_url}. Async + timeout 120 сек. При timeout/error — 500 + логирование для возврата средств.</annotation>
    <CrossLinks>
      <Link TARGET="backend_services_redis_client_py" TYPE="CALLS_METHOD" />
      <Link TARGET="backend_ai_pipeline_py" TYPE="CALLS_METHOD" />
      <Link TARGET="backend_services_game_builder_py" TYPE="CALLS_METHOD" />
      <Link TARGET="backend_services_github_publisher_py" TYPE="CALLS_METHOD" />
    </CrossLinks>
  </backend_api_games_py>

  <backend_services_redis_client_py FILE="backend/services/redis_client.py" TYPE="DATA_PROCESSING_MODULE">
    <annotation>Async Redis wrapper: get/set/delete. JSON-сериализация сессий. TTL дифференцирован: до оплаты — 86400 сек (24ч), после SuccessfulPayment (paid=true) — 259200 сек (72ч). При PATCH session(paid=true) — вызывает expire(session_id, 259200).</annotation>
  </backend_services_redis_client_py>

  <backend_services_refund_service_py FILE="backend/services/refund_service.py" TYPE="DATA_PROCESSING_MODULE">
    <annotation>ЮKassa Refund API: POST /refunds с payment_id и amount. Вызывается из games.py при timeout (>120 сек) или неперехваченной ошибке AI pipeline. Логирует refund_id. При сбое самого возврата — логирует CRITICAL для ручного разбора.</annotation>
    <CrossLinks>
      <Link TARGET="backend_api_games_py" TYPE="READS_DATA_FROM" />
    </CrossLinks>
  </backend_services_refund_service_py>

  <backend_services_game_builder_py FILE="backend/services/game_builder.py" TYPE="DATA_PROCESSING_MODULE">
    <annotation>Читает game/template.html. Заменяет 6 плейсхолдеров: {{PLAYER_NAME}}, {{HERO_SPRITE_URL}}, {{COMPANION_SPRITE_URL}}, {{HAS_COMPANION}}, {{SCENARIO}}, {{HERO_GENDER}}. Инжектирует window.GAME_CONFIG с полными данными сессии.</annotation>
    <CrossLinks>
      <Link TARGET="game_template_html" TYPE="READS_DATA_FROM" />
    </CrossLinks>
  </backend_services_game_builder_py>

  <backend_services_github_publisher_py FILE="backend/services/github_publisher.py" TYPE="DATA_PROCESSING_MODULE">
    <annotation>GitHub Contents API: PUT games/{session_id}/sprites/hero.png, companion.png (если char_count=2), index.html. Возвращает game_url.</annotation>
  </backend_services_github_publisher_py>

  <!-- ════════════════ AI LAYER ════════════════ -->

  <backend_ai_pipeline_py FILE="backend/ai/pipeline.py" TYPE="DATA_PROCESSING_MODULE">
    <annotation>Оркестратор: 1) color_extractor → accent_color, 2) replicate_client.generate(hero_photo, hero_prompt), 3) postprocessor → hero.png. Если char_count=2: повторяет шаги 1-3 для companion_photo с companion_prompt[companion_gender]. Timeout 120 сек.</annotation>
    <CrossLinks>
      <Link TARGET="backend_ai_color_extractor_py" TYPE="CALLS_METHOD" />
      <Link TARGET="backend_ai_replicate_client_py" TYPE="CALLS_METHOD" />
      <Link TARGET="backend_ai_postprocessor_py" TYPE="CALLS_METHOD" />
    </CrossLinks>
  </backend_ai_pipeline_py>

  <backend_ai_color_extractor_py FILE="backend/ai/color_extractor.py" TYPE="DATA_PROCESSING_MODULE">
    <annotation>K-Means (sklearn, k=5) на нижней половине фото. Исключает: кожный (#e8c4a0 ±30), белый (RGB>220), чёрный (RGB<30). Возвращает hex акцентного цвета.</annotation>
  </backend_ai_color_extractor_py>

  <backend_ai_replicate_client_py FILE="backend/ai/replicate_client.py" TYPE="DATA_PROCESSING_MODULE">
    <annotation>Replicate InstantID client. Содержит PROMPTS dict: hero (одинаков для м/ж), companion_m (masculine silhouette), companion_f (feminine silhouette). Подставляет accent_color. Polling каждые 3 сек. Возвращает PNG bytes.</annotation>
  </backend_ai_replicate_client_py>

  <backend_ai_postprocessor_py FILE="backend/ai/postprocessor.py" TYPE="DATA_PROCESSING_MODULE">
    <annotation>rembg.remove → PNG с прозрачностью. Pillow: resize height=512 с сохранением AR. Возвращает bytes.</annotation>
  </backend_ai_postprocessor_py>

  <!-- ════════════════ GAME LAYER ════════════════ -->

  <game_template_html FILE="game/template.html" TYPE="UI_MODULE">
    <annotation>Адаптированный index.html. Инжектирует window.GAME_CONFIG: {PLAYER_NAME, HERO_SPRITE_URL, COMPANION_SPRITE_URL, HAS_COMPANION, SCENARIO, HERO_GENDER}. Подключает src/data/texts.js.</annotation>
    <CrossLinks>
      <Link TARGET="game_src_main_js" TYPE="READS_DATA_FROM" />
      <Link TARGET="game_src_data_texts_js" TYPE="READS_DATA_FROM" />
    </CrossLinks>
  </game_template_html>

  <game_src_data_texts_js FILE="game/src/data/texts.js" TYPE="DATA_PROCESSING_MODULE">
    <annotation>Гендерно-адаптированный JSON: TEXTS.roulette[1-6][m/f], TEXTS.start[m/f], TEXTS.finish[m/f], TEXTS.final[scenario][title/subtitle]. Экспортируется как window.GAME_TEXTS.</annotation>
  </game_src_data_texts_js>

  <game_src_main_js FILE="game/src/main.js" TYPE="UI_MODULE">
    <annotation>Точка входа Phaser.js. Читает window.GAME_CONFIG + window.GAME_TEXTS. Передаёт через Phaser.Registry во все сцены. Порядок сцен: Boot → Start → Game → Roulette → Final → End.</annotation>
    <CrossLinks>
      <Link TARGET="game_src_scenes_BootScene_js" TYPE="CALLS_METHOD" />
      <Link TARGET="game_src_scenes_StartScene_js" TYPE="CALLS_METHOD" />
      <Link TARGET="game_src_scenes_GameScene_js" TYPE="CALLS_METHOD" />
      <Link TARGET="game_src_scenes_RouletteScene_js" TYPE="CALLS_METHOD" />
      <Link TARGET="game_src_scenes_FinalScene_js" TYPE="CALLS_METHOD" />
      <Link TARGET="game_src_scenes_EndScene_js" TYPE="CALLS_METHOD" />
    </CrossLinks>
  </game_src_main_js>

  <game_src_scenes_BootScene_js FILE="game/src/scenes/BootScene.js" TYPE="UI_MODULE">
    <annotation>Phaser preload-сцена: загрузка всех ассетов (спрайты из GAME_CONFIG URLs, атлас тайлов, аудио). Прогресс-бар «Загружаем игру для {name}...». По завершении загрузки → StartScene.</annotation>
  </game_src_scenes_BootScene_js>

  <game_src_scenes_StartScene_js FILE="game/src/scenes/StartScene.js" TYPE="UI_MODULE">
    <annotation>Прелоадер «Загружаем игру для {name}...» → приветствие «{name}, приветствуем тебя! 🎉» → инструкция → кнопка СТАРТ → анимация подъезда багги → GameScene.</annotation>
  </game_src_scenes_StartScene_js>

  <game_src_scenes_GameScene_js FILE="game/src/scenes/GameScene.js" TYPE="UI_MODULE">
    <annotation>Автодвижение Can-Am, прыжок по tap/pointerdown, препятствия, монетки/клубнички/сердечки. Текст финала из TEXTS.finish[HERO_GENDER]. По финишу → RouletteScene.</annotation>
  </game_src_scenes_GameScene_js>

  <game_src_scenes_RouletteScene_js FILE="game/src/scenes/RouletteScene.js" TYPE="UI_MODULE">
    <annotation>3 вращения. 6 фраз из TEXTS.roulette[HERO_GENDER]. Анимация: подсветка + zoom + конфетти. → FinalScene.</annotation>
  </game_src_scenes_RouletteScene_js>

  <game_src_scenes_FinalScene_js FILE="game/src/scenes/FinalScene.js" TYPE="UI_MODULE">
    <annotation>HAS_COMPANION=true: оба персонажа, сердечки, glow, slow-motion. false: только герой, конфетти + фейерверки. Заголовок/подзаголовок из TEXTS.final[SCENARIO]. Мобайл: fullscreen, safe-area. По окончании анимации → EndScene.</annotation>
  </game_src_scenes_FinalScene_js>

  <game_src_scenes_EndScene_js FILE="game/src/scenes/EndScene.js" TYPE="UI_MODULE">
    <annotation>Финальный экран после FinalScene. Кнопки: «Поделиться ссылкой» (Web Share API или копирование URL) и «Сыграть снова» (restart → BootScene). Отображает имя героя и финальный текст по сценарию.</annotation>
  </game_src_scenes_EndScene_js>

  <!-- ════════════════ MODULE INTERACTIONS ════════════════ -->

  <ProjectCrossLinks TYPE="MODULE_INTERACTIONS_OVERVIEW">
    <Link SOURCE="bot_handlers_dialog_py"            TARGET="bot_services_backend_client_py"        TYPE="CALLS_METHOD" />
    <Link SOURCE="bot_handlers_payment_py"           TARGET="bot_services_backend_client_py"        TYPE="CALLS_METHOD" />
    <Link SOURCE="bot_handlers_generation_py"        TARGET="bot_services_backend_client_py"        TYPE="CALLS_METHOD" />
    <Link SOURCE="bot_handlers_generation_py"        TARGET="bot_handlers_payment_py"               TYPE="CALLS_METHOD" />
    <Link SOURCE="bot_services_backend_client_py"    TARGET="backend_api_sessions_py"               TYPE="CALLS_METHOD" />
    <Link SOURCE="bot_services_backend_client_py"    TARGET="backend_api_games_py"                  TYPE="CALLS_METHOD" />
    <Link SOURCE="backend_api_games_py"              TARGET="backend_ai_pipeline_py"                TYPE="CALLS_METHOD" />
    <Link SOURCE="backend_api_games_py"              TARGET="backend_services_game_builder_py"      TYPE="CALLS_METHOD" />
    <Link SOURCE="backend_api_games_py"              TARGET="backend_services_github_publisher_py"  TYPE="CALLS_METHOD" />
    <Link SOURCE="backend_api_games_py"              TARGET="backend_services_refund_service_py"    TYPE="CALLS_METHOD" />
    <Link SOURCE="backend_ai_pipeline_py"            TARGET="backend_ai_color_extractor_py"         TYPE="CALLS_METHOD" />
    <Link SOURCE="backend_ai_pipeline_py"            TARGET="backend_ai_replicate_client_py"        TYPE="CALLS_METHOD" />
    <Link SOURCE="backend_ai_pipeline_py"            TARGET="backend_ai_postprocessor_py"           TYPE="CALLS_METHOD" />
    <Link SOURCE="backend_services_game_builder_py"  TARGET="game_template_html"                    TYPE="READS_DATA_FROM" />
    <Link SOURCE="game_src_main_js"                  TARGET="game_src_data_texts_js"                TYPE="READS_DATA_FROM" />
  </ProjectCrossLinks>

</DraftCodeGraph>
```

---

## 2. Step-by-step Data Flow

### 2.1 Диалог сбора данных (Bot FSM, 9 состояний)

1. `/start` → `start.py` → `backend_client.create_session()` → Redis получает UUID → FSM → `WAITING_SCENARIO`
2. **Сценарий**: кнопка [ДР / Любовь / Комплимент] → `PATCH session(scenario)` → FSM → `WAITING_CHAR_COUNT`
3. **Кол-во персонажей**: кнопка [👥 / 🧑] → `PATCH session(char_count)` → FSM → `WAITING_HERO_GENDER`
4. **Пол героя**: [👨/👩] → `PATCH session(hero_gender)` → если `char_count=2` → FSM → `WAITING_COMPANION_GENDER`, иначе → `WAITING_NAME`
5. **Пол компаньона** (только char_count=2): [👨/👩] → `PATCH session(companion_gender)` → FSM → `WAITING_NAME`
6. **Имя**: текст → валидация (1-30, кириллица/латиница) → `PATCH session(name)` → FSM → `WAITING_HERO_PHOTO`
7. **Фото героя**: фото → скачать с Telegram → валидация JPEG/PNG ≥300px → `PATCH session(hero_photo)` → если `char_count=2` → FSM → `WAITING_COMPANION_PHOTO`, иначе → `CONFIRM`
8. **Фото компаньона** (только char_count=2): фото → `PATCH session(companion_photo)` → FSM → `CONFIRM`
9. **Превью**: сводка (сценарий + кол-во + пол(а) + имя + эскизы) → кнопки [💳 Оплатить] / [✏️ Изменить]

### 2.2 Оплата

10. [💳 Оплатить] → `payment.py` → `send_invoice(amount=100000)` → FSM → `PAYING`
11. `PreCheckoutQuery` → `answer_pre_checkout_query(ok=True)` в течение 10 сек
12. `SuccessfulPayment` → `PATCH session(paid=true)` → Redis TTL обновляется с 24ч → 72ч → `backend_client.trigger_generation(session_id)` → бот: «Оплата получена! Генерирую... ~60 сек»

### 2.3 AI Pipeline

13. `POST /games/build` → читает сессию из Redis → `ai_pipeline.run(session_data)` с timeout 120 сек
14. **Цвет героя**: `color_extractor.extract(hero_photo_bytes)` → K-Means k=5 → `hero_accent_color`
15. **Спрайт героя**: `replicate_client.generate(hero_photo, PROMPTS["hero"], hero_accent_color)` → polling → PNG bytes
16. **Постобработка героя**: `postprocessor.process(png)` → rembg → resize h=512 → `hero.png`
17. **Компаньон** (если char_count=2): повторить шаги 14-16 для companion_photo с `PROMPTS["companion_m" | "companion_f"]` по `companion_gender`
18. Timeout (>120 сек) / Exception → `refund_service.create_refund(payment_id, amount=100000)` → ЮKassa POST /refunds → бот уведомляет пользователя: «Произошла ошибка. Средства возвращены.»

### 2.4 Сборка и публикация

19. **Спрайты**: `github_publisher.upload(session_id, "hero.png", bytes)` → `https://user.github.io/repo/games/{id}/sprites/hero.png`
20. **HTML**: `game_builder.build(session_data)` → читает `game/template.html` → подставляет 6 плейсхолдеров + инжектирует `window.GAME_CONFIG`:
    ```json
    {
      "PLAYER_NAME": "Александр",
      "HERO_SPRITE_URL": "https://.../hero.png",
      "COMPANION_SPRITE_URL": "https://.../companion.png",
      "HAS_COMPANION": true,
      "SCENARIO": "birthday",
      "HERO_GENDER": "m"
    }
    ```
21. **Публикация**: `github_publisher.upload(session_id, "index.html", html)` → `game_url`

### 2.5 Ответ пользователю и регенерация

22. Backend уведомляет бот о готовности → `generation.py` скачивает PNG-спрайты с GitHub Pages → отправляет превью: «Вот ваши герои!»
23. Кнопки: [✅ Запустить игру] → отправляет `game_url` | [🔄 Перегенерировать]
24. **[🔄 Перегенерировать], regen_count=0:** `PATCH session(regen_count=1)` → повторный `trigger_generation` бесплатно → переход к шагу 22
25. **[🔄 Перегенерировать], regen_count≥1:** FSM → `WAITING_REGEN_PAYMENT` → `send_invoice(amount=100000)` → SuccessfulPayment → повторный `trigger_generation` → шаг 22

### 2.6 Игровой flow (Frontend)

25. Browser загружает `index.html` → Phaser.js читает `window.GAME_CONFIG` и `window.GAME_TEXTS`
26. **StartScene**: «{name}, приветствуем тебя!» → СТАРТ → анимация багги
27. **GameScene**: геймплей 1-2 мин → текст финала из `TEXTS.finish[HERO_GENDER]`
28. **RouletteScene**: 3 вращения, фраза из `TEXTS.roulette[1-6][HERO_GENDER]` с именем
29. **FinalScene**: если `HAS_COMPANION=true` → оба у флага + сердечки; если false → герой + конфетти. Заголовок + подзаголовок из `TEXTS.final[SCENARIO]`

---

## 3. Модель данных

### 3.1 Сессия (Redis JSON)

```json
{
  "session_id": "uuid4",
  "user_id": 123456789,
  "scenario": "birthday | love | compliment",
  "char_count": 1,
  "hero_gender": "m | f",
  "companion_gender": "m | f | null",
  "name": "Александр",
  "hero_photo_file_id": "telegram_file_id",
  "companion_photo_file_id": "telegram_file_id | null",
  "paid": false,
  "payment_id": "yookassa_payment_id | null",
  "regen_count": 0,
  "hero_sprite_url": null,
  "companion_sprite_url": null,
  "game_url": null,
  "created_at": "iso8601",
  "ttl_seconds": 86400
}
```

> TTL: 86400 сек (24ч) до оплаты; при `paid=true` Redis `expire` обновляет до 259200 сек (72ч).  
> `payment_id` — сохраняется из `SuccessfulPayment.provider_payment_charge_id` для вызова ЮKassa Refund API.

```json
```

### 3.2 AI Промпты (replicate_client.py PROMPTS dict)

```python
PROMPTS = {
    "hero": (
        "Cartoon caricature bobblehead style. Head occupies 50% of body height. "
        "Face: precise cartoon stylization of reference photo. Preserve all features. "
        "Character MUST be recognizable. Seated in Can-Am Commander UTV. "
        "Suit color: {accent_color}. Pixar quality, blue gradient bg (#1a6fd4 to #0a3a8a). "
        "NEGATIVE: photorealism, dark bg, anime, blurry/distorted face."
    ),
    "companion_f": (
        "Cartoon caricature bobblehead style. Head occupies 50% of body height. "
        "Face: precise cartoon stylization of reference photo. Preserve all features. "
        "Standing celebratory pose: waving, big smile. Rally suit, feminine silhouette. "
        "Suit color: {accent_color}. Pixar quality, blue gradient bg. "
        "NEGATIVE: photorealism, dark bg, anime, blurry/distorted face."
    ),
    "companion_m": (
        "Cartoon caricature bobblehead style. Head occupies 50% of body height. "
        "Face: precise cartoon stylization of reference photo. Preserve all features. "
        "Standing celebratory pose: waving, big smile. Rally suit, masculine silhouette, "
        "broad shoulders. Suit color: {accent_color}. Pixar quality, blue gradient bg. "
        "NEGATIVE: photorealism, dark bg, anime, blurry/distorted face."
    )
}
```

### 3.3 Гендерно-адаптированные тексты (game/src/data/texts.js)

```js
window.GAME_TEXTS = {
  start:  { m: "{name}, ты готов? 🚀",       f: "{name}, ты готова? 🚀" },
  finish: { m: "{name} добрался до финиша!", f: "{name} добралась до финиша!" },
  roulette: {
    1: { m: "{name}, ты КРУТОЙ 😎",         f: "{name}, ты КРУТАЯ 😎" },
    2: { m: "{name} — ты офигенный 🔥",     f: "{name} — ты офигенная 🔥" },
    3: { m: "{name}, ты секси 😏",           f: "{name}, ты секси 😏" },
    4: { m: "{name} — лучший на свете 🌟",  f: "{name} — лучшая на свете 🌟" },
    5: { m: "{name}, ты просто огонь 🎯",   f: "{name}, ты просто огонь 🎯" },
    6: { m: "{name} — мощь и харизма 💪",   f: "{name} — мощь и харизма 💪" }
  },
  final: {
    birthday:  { title: "🎉 С ДНЁМ РОЖДЕНИЯ, {NAME}! 🎉", subtitle: "С днём рождения, душа моя" },
    love:      { title: "❤️ {NAME}, ЛЮБЛЮ ТЕБЯ ❤️",       subtitle: "Люблю тебя, душа моя" },
    compliment:{ title: "💫 {NAME}, ТЫ ЛУЧШЕ ВСЕХ 💫",    subtitle: "Ты лучше всех на свете, душа моя" }
  }
};
```

---

## 4. Feature Slices (для оркестрации)

| ID | Название | Зависит от | Файлы |
|---|---|---|---|
| **FS-1** | Bot Core + FSM Dialog (10 шагов) | — | `bot/` (без payment.py, generation.py) |
| **FS-2** | Payment + Regeneration flow | FS-1 | `bot/handlers/payment.py`, `bot/handlers/generation.py` |
| **FS-3** | AI Pipeline (gender-aware промпты) | — | `backend/ai/` |
| **FS-4** | Backend API + Redis (дифф. TTL) + Game Builder + Refund | FS-3 | `backend/` |
| **FS-5** | Game Template: GAME_CONFIG + GAME_TEXTS + все 6 сцен | — | `game/` |
| **FS-6** | Deployment | FS-1, FS-4 | `docker-compose.yml`, `Dockerfile.*` |

**Параллельный старт:** FS-1, FS-3, FS-5 независимы.
**Последовательно:** FS-2 → после FS-1; FS-4 → после FS-3 + FS-5; FS-6 → последний.

---

## 5. Acceptance Criteria

### Bot & Dialog
- [ ] `/start` показывает кнопки выбора сценария (3 шт)
- [ ] Полный happy path: сценарий → char_count → hero_gender → [companion_gender] → имя → фото_героя → [фото_компаньона] → сводка
- [ ] При char_count=1 шаги companion_gender и фото_компаньона пропускаются
- [ ] Валидация имени: отклоняет пустую строку, >30 символов, только цифры
- [ ] Валидация фото: принимает JPEG/PNG ≥300×300px, отклоняет документы
- [ ] `/new` сбрасывает FSM и создаёт новую сессию

### Оплата и регенерация
- [ ] Invoice на 1000 руб через Telegram Payments (тестовый провайдер)
- [ ] Генерация НЕ запускается без SuccessfulPayment
- [ ] `payment_id` сохраняется в сессии после SuccessfulPayment
- [ ] Redis TTL обновляется с 24ч → 72ч при `paid=true`
- [ ] Первая перегенерация ([🔄]) бесплатна (regen_count 0→1), pipeline запускается без Invoice
- [ ] Вторая+ перегенерация требует нового Invoice 1000 руб (WAITING_REGEN_PAYMENT)
- [ ] При ошибке/timeout AI → `refund_service` вызывает ЮKassa Refund API с `payment_id`
- [ ] Бот уведомляет пользователя об ошибке и возврате средств

### AI Pipeline
- [ ] Replicate вызывается с промптом, содержащим accent_color_hex
- [ ] Компаньон-мужчина использует промпт "companion_m" (masculine silhouette)
- [ ] Компаньон-женщина использует промпт "companion_f" (feminine silhouette)
- [ ] Спрайт возвращается как PNG с прозрачным alpha-каналом
- [ ] color_extractor исключает кожный, белый, чёрный

### Game Builder
- [ ] Все 6 плейсхолдеров заменены в template.html
- [ ] window.GAME_CONFIG содержит: PLAYER_NAME, HERO_SPRITE_URL, COMPANION_SPRITE_URL, HAS_COMPANION, SCENARIO, HERO_GENDER

### Frontend / Game
- [ ] Рулетка: все 6 фраз содержат имя, адаптированы по HERO_GENDER
- [ ] Финальная сцена: заголовок и подзаголовок соответствуют SCENARIO
- [ ] При char_count=1 компаньон отсутствует на финише, только герой + конфетти
- [ ] При char_count=2 компаньон присутствует на финише
- [ ] Fullscreen на мобильных (Phaser Scale FIT/ENVELOP)
- [ ] Safe area iOS: `env(safe-area-inset-bottom)`
- [ ] Прыжок по pointerdown (без 300ms задержки)
- [ ] FPS ≥ 30 на устройствах 2019+
- [ ] Загрузка в браузере < 5 сек

### Инфраструктура
- [ ] Redis TTL: неоплаченная сессия — 24ч, оплаченная — 72ч
- [ ] После истечения TTL — 404 на game_url
- [ ] Docker Compose поднимает bot + backend + Redis без ошибок

$END_DEV_PLAN
